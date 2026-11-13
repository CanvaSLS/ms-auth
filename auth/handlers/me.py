from auth import storage
from common import ApiError, endpoint, public_user


@endpoint(protected=True)
def handler(event, ctx):
    user = storage.get_user(ctx["tenant_id"], ctx["user_id"])
    if not user or user.get("estado") != "ACTIVO":
        raise ApiError(401, "NO_AUTENTICADO", "Cuenta sin acceso")
    return {"usuario": public_user(user)}
