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
