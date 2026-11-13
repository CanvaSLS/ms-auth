"""Importar handlers no necesita red ni credenciales AWS."""
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def dynamodb():
    import boto3
    return boto3.resource("dynamodb")


def users():
    return dynamodb().Table(os.environ["T_USUARIOS"])


def tokens():
    return dynamodb().Table(os.environ["T_TOKENS"])


def get_user(tenant_id, user_id):
    return users().get_item(Key={"tenant_id": tenant_id, "user_id": user_id},
                            ConsistentRead=True).get("Item")


def conditional_failure(error):
    response = getattr(error, "response", {})
    code = response.get("Error", {}).get("Code")
    return (code == "ConditionalCheckFailedException" or
            (code == "TransactionCanceledException" and any(
                reason.get("Code") == "ConditionalCheckFailed"
                for reason in response.get("CancellationReasons", []))))


def get_by_email(tenant_id, email):
    # Reservas creadas por el registro: lectura inmediata, sin depender del GSI.
    lookup = get_user(tenant_id, "EMAIL#" + email)
    if lookup:
        return get_user(tenant_id, lookup["account_id"])
    # Las cuentas del seed externo no tienen reserva; mantienen sus IDs originales.
    from boto3.dynamodb.conditions import Key
    rows = users().query(IndexName="gsi_email", Limit=2,
                         KeyConditionExpression=Key("tenant_id").eq(tenant_id) & Key("email").eq(email))["Items"]
    if len(rows) > 1:
        raise RuntimeError("Email duplicado en el seed; requiere corrección administrativa")
    if not rows:
        return None
    # El índice es eventual. Estado, rol y contraseña se leen de la tabla principal.
    user = get_user(tenant_id, rows[0]["user_id"])
    return user if user and user.get("email") == email else None


@lru_cache(maxsize=1)
def transaction_client():
    import boto3
    return boto3.client("dynamodb")


def create_user(user):
    """Usuario y reserva de email atómicos para registros concurrentes."""
    from boto3.dynamodb.types import TypeSerializer
    serializer = TypeSerializer()
    lookup = {"tenant_id": user["tenant_id"], "user_id": "EMAIL#" + user["email"],
              "account_id": user["user_id"]}
    transaction_client().transact_write_items(TransactItems=[
        {"Put": {"TableName": os.environ["T_USUARIOS"],
                 "Item": {key: serializer.serialize(value) for key, value in item.items()},
                 "ConditionExpression": "attribute_not_exists(tenant_id) AND attribute_not_exists(user_id)"}}
        for item in (user, lookup)])
