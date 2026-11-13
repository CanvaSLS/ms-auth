import hashlib
import hmac
import re
import secrets

ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        rounds = int(iterations)
        if algorithm != "pbkdf2_sha256" or not 600_000 <= rounds <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), rounds)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError, AttributeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def verify_legacy_password(password, user):
    """Solo para cuentas creadas por datos-seed/seed.py (10 000 iteraciones)."""
    try:
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(user["salt"]), 10_000)
        return hmac.compare_digest(actual.hex(), user["pwd_hash"])
    except (KeyError, ValueError, TypeError):
        return False


def bearer(value):
    if not isinstance(value, str):
        return None
    parts = value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1] if re.fullmatch(r"[A-Za-z0-9_-]{43}", parts[1]) else None
