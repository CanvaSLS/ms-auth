from auth import storage
from auth.security import bearer, token_hash
from common import ApiError, endpoint


@endpoint(protected=True)
def handler(event, ctx):
    headers = {key.lower(): value for key, value in (event.get("headers") or {}).items()}
    token = bearer(headers.get("authorization"))
    if not token:
        raise ApiError(401, "NO_AUTENTICADO", "Falta el token Bearer")
    try:
        storage.tokens().delete_item(Key={"token_hash": token_hash(token)},
                                     ConditionExpression="tenant_id = :t AND user_id = :u",
                                     ExpressionAttributeValues={":t": ctx["tenant_id"], ":u": ctx["user_id"]})
    except Exception as error:
        if storage.conditional_failure(error):
            raise ApiError(401, "NO_AUTENTICADO", "Sesión no válida") from None
        raise
    return {"mensaje": "Sesión cerrada"}
