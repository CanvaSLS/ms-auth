import base64
import binascii
import json

from auth import storage
from common import ApiError, endpoint, exigir_rol, public_user


@endpoint(protected=True)
def handler(event, ctx):
    from boto3.dynamodb.conditions import Key
    exigir_rol(ctx, "docente", "admin")
    params = event.get("queryStringParameters") or {}
    try:
        limit = max(1, min(100, int(params.get("limit", 25))))
    except (ValueError, TypeError):
        raise ApiError(400, "LIMIT_INVALIDO", "limit debe ser entero") from None
    query = {"KeyConditionExpression": Key("tenant_id").eq(ctx["tenant_id"]),
             "Limit": limit, "ConsistentRead": True,
             "FilterExpression": "attribute_exists(email)"}
    if params.get("cursor"):
        try:
            cursor = json.loads(base64.b64decode(params["cursor"], altchars=b"-_", validate=True))
            if not isinstance(cursor, dict) or set(cursor) != {"tenant_id", "user_id"}:
                raise ValueError()
            if not all(isinstance(value, str) and value for value in cursor.values()):
                raise ValueError()
        except (ValueError, TypeError, UnicodeError, binascii.Error):
            raise ApiError(400, "CURSOR_INVALIDO", "Cursor inválido") from None
        if cursor["tenant_id"] != ctx["tenant_id"]:
            raise ApiError(403, "CURSOR_AJENO", "El cursor pertenece a otra institución")
        query["ExclusiveStartKey"] = cursor
    result = storage.users().query(**query)
    last = result.get("LastEvaluatedKey")
    return {"usuarios": [public_user(user) for user in result["Items"]],
            "cursor": base64.urlsafe_b64encode(json.dumps(last).encode()).decode() if last else None}
