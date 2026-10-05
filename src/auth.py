"""JWT authentication utilities."""
import os
from datetime import datetime, timedelta
from typing import Optional

try:
    from jose import jwt, JWTError
    from passlib.context import CryptContext
    _HAS_AUTH = True
except Exception as e:
    print(f"[WARN] jose/passlib unavailable ({e.__class__.__name__}). Using mock hashing.")
    _HAS_AUTH = False

    class CryptContext:
        def hash(self, pw): return f"mockhash::{pw}"
        def verify(self, pw, hashed): return hashed == f"mockhash::{pw}"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if _HAS_AUTH else CryptContext()

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))


def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    return pwd_context.verify(pw, hashed)


def create_access_token(username: str, role: str = "member") -> str:
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)
    payload = {"sub": username, "role": role, "exp": expire}
    if _HAS_AUTH:
        return jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    import base64, json
    raw = json.dumps(payload, default=str).encode()
    return "mock." + base64.urlsafe_b64encode(raw).decode()


def decode_token(token: str):
    try:
        if _HAS_AUTH:
            return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        if not token.startswith("mock."):
            return None
        import base64, json
        raw = base64.urlsafe_b64decode(token.split(".", 1)[1]).decode()
        return json.loads(raw)
    except Exception:
        return None
