import time

from auth import storage
from auth.config import TENANTS, ROLES
from auth.security import bearer, token_hash
from common import log


def handler(event, context):
    token = bearer(event.get("authorizationToken"))
    if not token:
        raise Exception("Unauthorized")
    try:
        session = storage.tokens().get_item(Key={"token_hash": token_hash(token)},
                                            ConsistentRead=True).get("Item")
        if (not session or session["expires_at"] <= int(time.time())
                or session.get("tenant_id") not in TENANTS):
            raise ValueError("InvalidSession")
        user = storage.get_user(session["tenant_id"], session["user_id"])
        if not user or user.get("estado") != "ACTIVO" or user.get("rol") not in ROLES:
            raise ValueError("InactiveAccount")
    except (ValueError, KeyError, TypeError):
        log("SEGURIDAD", accion="sesion_denegada")
        raise Exception("Unauthorized") from None
    except Exception as error:
        log("ERROR", accion="authorizer", clase=type(error).__name__)
        raise Exception("AuthorizationUnavailable") from None
    return {"principalId": f'{user["tenant_id"]}:{user["user_id"]}',
            "policyDocument": {"Version": "2012-10-17", "Statement": [
                {"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": event["methodArn"]}]},
            "context": {key: user[key] for key in ("tenant_id", "user_id", "rol", "nombre")}}
