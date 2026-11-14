import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd = CryptContext(schemes=["argon2"], deprecated="auto")
def hash_password(value: str) -> str:
    return pwd.hash(value)
def verify_password(value: str, hashed: str) -> bool:
    return pwd.verify(value, hashed)
def create_token(subject: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": subject, "exp": exp}, settings.secret_key, algorithm="HS256")
def decode_token(token: str):
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return data.get("sub")
    except JWTError:
        return None
def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)
def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
def sanitize_pii_lgpd(text: str) -> str:
    text = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[CPF_MASKED]", text)
    return re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_MASKED]", text)
