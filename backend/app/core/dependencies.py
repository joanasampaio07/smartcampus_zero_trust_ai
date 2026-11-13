from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    subject = decode_token(token)
    if not subject:
        raise HTTPException(401, "Credenciais inválidas ou expiradas")
    user = db.get(User, int(subject))
    if not user or not user.is_active:
        raise HTTPException(401, "Usuário indisponível")
    return user

def roles(*allowed):
    def check(user=Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, "Acesso não autorizado")
        return user
    return check
