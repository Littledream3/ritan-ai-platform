import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt


JWT_SECRET = os.environ.get("COLLECTION_JWT_SECRET", "development-only-secret-change-me")
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_text, digest_text = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(doctor_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(doctor_id), "iat": now, "exp": now + timedelta(hours=12), "aud": "dfu-collection"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], audience="dfu-collection")
    return int(payload["sub"])

