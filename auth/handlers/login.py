import secrets
import time
from datetime import datetime, timezone

from auth import storage
from auth.config import ROLES, token_ttl
from auth.security import hash_password, token_hash, verify_password, verify_legacy_password
from common import ApiError, body, endpoint, identity, public_user

_DUMMY_HASH = None


@endpoint()
def handler(event):
    global _DUMMY_HASH
    tenant, email, password = identity(body(event))
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_urlsafe(32))
    user = storage.get_by_email(tenant, email)
    legacy = user and "password_hash" not in user
    valid = (verify_legacy_password(password, user) if legacy else
             verify_password(password, user.get("password_hash", "") if user else _DUMMY_HASH))
    if not valid or not user:
        raise ApiError(401, "CREDENCIALES_INVALIDAS", "Email o contraseña incorrectos")
    if user.get("estado") != "ACTIVO" or user.get("rol") not in ROLES:
        raise ApiError(403, "USUARIO_INACTIVO", "Cuenta sin acceso")
    if legacy:
        # Actualización condicional: no sobrescribir cambios concurrentes del operador.
        try:
            storage.users().update_item(
                Key={"tenant_id": tenant, "user_id": user["user_id"]},
                UpdateExpression="SET password_hash = :new REMOVE salt, pwd_hash",
                ConditionExpression="salt = :salt AND pwd_hash = :old AND attribute_not_exists(password_hash)",
                ExpressionAttributeValues={":new": hash_password(password), ":salt": user["salt"], ":old": user["pwd_hash"]})
        except Exception as error:
            if storage.conditional_failure(error):
                raise ApiError(401, "CREDENCIALES_INVALIDAS", "Reintenta el inicio de sesión") from None
            raise
    token = secrets.token_urlsafe(32)
    issued, ttl = int(time.time()), token_ttl()
    storage.tokens().put_item(Item={"token_hash": token_hash(token), "tenant_id": tenant,
                                    "user_id": user["user_id"], "issued_at": issued,
                                    "expires_at": issued + ttl},
                              ConditionExpression="attribute_not_exists(token_hash)")
    return {"access_token": token, "token_type": "Bearer", "expires_in": ttl,
            "token": token, "expira_epoch": issued + ttl,
            "expira_en": datetime.fromtimestamp(issued + ttl, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "usuario": public_user(user)}
