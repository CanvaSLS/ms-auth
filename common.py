"""Validación HTTP y contexto de confianza para ms-auth."""
import base64
import binascii
import functools
import json
import os
import re
from datetime import datetime, timezone

from auth.config import TENANTS, ROLES


class ApiError(Exception):
    def __init__(self, status, codigo, mensaje):
        super().__init__(codigo)
        self.status, self.codigo, self.mensaje = status, codigo, mensaje


def log(tipo, **datos):
    print(json.dumps({"tipo": tipo, **datos}, ensure_ascii=False))


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def headers():
    return {"Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Access-Control-Allow-Origin": os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"}


def body(event):
    try:
        raw = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        if len(raw.encode("utf-8")) > 16_384:
            raise ApiError(400, "CUERPO_INVALIDO", "El cuerpo supera 16 KiB")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise ApiError(400, "JSON_INVALIDO", "Se esperaba un objeto JSON válido") from None


def requerido(data, field, maximum=200, strip=True):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ApiError(400, "CAMPO_INVALIDO", f"Campo inválido: {field}")
    return value.strip() if strip else value


def identity(data, registration=False):
    tenant = requerido(data, "tenant_id", 40)
    if tenant not in TENANTS:
        raise ApiError(403 if registration else 401,
                       "TENANT_NO_AUTORIZADO" if registration else "CREDENCIALES_INVALIDAS",
                       "Institución no autorizada" if registration else "Email o contraseña incorrectos")
    email = requerido(data, "email", 254).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ApiError(400, "EMAIL_INVALIDO", "Email inválido")
    password = requerido(data, "password", 128, strip=False)
    return tenant, email, password


def validate_password(password):
    if (len(password) < 12 or not any(c.islower() for c in password)
            or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password)):
        raise ApiError(400, "PASSWORD_DEBIL", "Usa 12 a 128 caracteres, mayúscula, minúscula y número")


def public_user(user):
    return {key: user[key] for key in ("tenant_id", "user_id", "email", "nombre", "rol")}


def contexto(event):
    ctx = (event.get("requestContext") or {}).get("authorizer") or {}
    if (ctx.get("tenant_id") not in TENANTS or not ctx.get("user_id")
            or ctx.get("rol") not in ROLES):
        raise ApiError(401, "NO_AUTENTICADO", "Falta el contexto autenticado")
    return {key: ctx[key] for key in ("tenant_id", "user_id", "rol")}


def verificar_tenant(ctx, *sources):
    for source in sources:
        if (source or {}).get("tenant_id", ctx["tenant_id"]) != ctx["tenant_id"]:
            raise ApiError(403, "TENANT_MISMATCH", "El recurso no pertenece a tu institución")


def exigir_rol(ctx, *roles):
    if ctx["rol"] not in roles:
        raise ApiError(403, "ROL_NO_AUTORIZADO", "Rol sin permiso para esta operación")


def endpoint(protected=False):
    def decorate(fn):
        @functools.wraps(fn)
        def wrapped(event, context):
            try:
                if protected:
                    ctx = contexto(event)
                    verificar_tenant(ctx, event.get("pathParameters"),
                                      event.get("queryStringParameters"), body(event))
                    result = fn(event, ctx)
                else:
                    result = fn(event)
                status, data = result if isinstance(result, tuple) else (200, result)
            except ApiError as error:
                status, data = error.status, {"error": error.codigo, "mensaje": error.mensaje}
            except Exception as error:
                # Las excepciones SDK pueden contener datos de la petición: no usar repr.
                log("ERROR", accion=fn.__module__, clase=type(error).__name__)
                status, data = 500, {"error": "ERROR_INTERNO", "mensaje": "Error inesperado"}
            log("HTTP", accion=fn.__module__, status=status)
            return {"statusCode": status, "headers": headers(), "body": json.dumps(data, ensure_ascii=False)}
        return wrapped
    return decorate
