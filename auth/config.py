import json
import os

# Contrato real de los cinco servicios, frontend-kit y datos-seed.
TENANTS = frozenset({"UTEC", "NORTE", "ANDINO"})
ROLES = frozenset({"alumno", "docente", "admin"})


def invitation_codes():
    codes = json.loads(os.environ.get("TENANT_INVITE_CODES", "{}"))
    if not isinstance(codes, dict):
        raise ValueError("Configuración de invitaciones inválida")
    return codes


def token_ttl():
    value = int(os.environ.get("TOKEN_TTL_SECONDS", "3600"))
    if not 60 <= value <= 86400:
        raise ValueError("TTL fuera del rango permitido")
    return value
