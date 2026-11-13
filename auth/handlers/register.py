import hmac
import uuid

from auth import storage
from auth.config import invitation_codes
from auth.security import hash_password
from common import ApiError, body, endpoint, identity, now_iso, public_user, requerido, validate_password


@endpoint()
def handler(event):
    data = body(event)
    tenant, email, password = identity(data, registration=True)
    nombre = requerido(data, "nombre", 100)
    invite = requerido(data, "invite_code", 256, strip=False)
    expected = invitation_codes().get(tenant)
    if not isinstance(expected, str) or not expected or not hmac.compare_digest(invite.encode(), expected.encode()):
        raise ApiError(403, "INVITACION_INVALIDA", "Invitación no autorizada")
    if "rol" in data and data["rol"] not in ("alumno", "estudiante"):
        raise ApiError(400, "ROL_INVALIDO", "El registro público solo permite alumnos")
    validate_password(password)
    if storage.get_by_email(tenant, email):
        raise ApiError(409, "EMAIL_YA_REGISTRADO", "El email ya existe en esta institución")
    # 20 caracteres: compatible con VARCHAR(20) de cursos/evaluaciones.
    user = {"tenant_id": tenant, "user_id": "A" + uuid.uuid4().hex[:19], "email": email, "nombre": nombre,
            "rol": "alumno", "estado": "ACTIVO", "created_at": now_iso(),
            "password_hash": hash_password(password)}
    try:
        storage.create_user(user)
    except Exception as error:
        if storage.conditional_failure(error):
            raise ApiError(409, "EMAIL_YA_REGISTRADO", "El email ya existe en esta institución") from None
        raise
    profile = public_user(user)
    return 201, {**profile, "usuario": profile}
