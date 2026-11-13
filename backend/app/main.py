from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal, get_db
from app.core.security import hash_password, verify_password, create_token, generate_opaque_token, hash_token
from app.core.dependencies import current_user, roles
from app.core.rate_limit import rate_limit
from app.models import User, Course, Enrollment, AuditLog, RefreshToken, PasswordResetToken
from app.schemas import (
    RegisterIn, UserOut, TokenOut, RefreshIn, LogoutIn, ForgotPasswordIn, ResetPasswordIn,
    AdminUserCreateIn, UserRoleUpdateIn, CourseIn, CourseOut, EnrollmentIn, StatusIn, EnrollmentOut, ChatIn,
    AuditLogOut, DashboardStatsOut,
)
from app.services.ai import ask_gemini

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    if settings.admin_email and settings.admin_password:
        db = SessionLocal()
        try:
            email = settings.admin_email.lower()
            if not db.scalar(select(User).where(User.email == email)):
                db.add(User(name="Administrador", email=email, password_hash=hash_password(settings.admin_password), role="ADMIN"))
                db.commit()
        finally:
            db.close()
    yield

app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
                   allow_methods=["GET","POST","PATCH"], allow_headers=["Authorization","Content-Type"])

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/auth/register", response_model=UserOut, status_code=201, dependencies=[Depends(rate_limit)])
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Não foi possível cadastrar: verifique os dados informados.")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="STUDENT")
    db.add(user); db.commit(); db.refresh(user)
    return user

def _issue_refresh_token(db: Session, user_id: int) -> str:
    raw = generate_opaque_token()
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    ))
    return raw

@app.post("/api/v1/auth/login", response_model=TokenOut, dependencies=[Depends(rate_limit)])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos", headers={"WWW-Authenticate":"Bearer"})
    refresh_token = _issue_refresh_token(db, user.id)
    db.commit()
    return {"access_token": create_token(str(user.id)), "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/api/v1/auth/refresh", response_model=TokenOut, dependencies=[Depends(rate_limit)])
def refresh_session(payload: RefreshIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token)))
    if not record or record.revoked_at is not None or record.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(401, "Refresh token inválido ou expirado")
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Usuário inativo ou inválido")
    record.revoked_at = now
    new_refresh = _issue_refresh_token(db, user.id)
    db.commit()
    return {"access_token": create_token(str(user.id)), "refresh_token": new_refresh, "token_type": "bearer"}

@app.post("/api/v1/auth/logout", status_code=204)
def logout(payload: LogoutIn, db: Session = Depends(get_db)):
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token)))
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return None

@app.post("/api/v1/auth/forgot-password", dependencies=[Depends(rate_limit)])
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    reset_token = None
    if user and user.is_active:
        reset_token = generate_opaque_token()
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(reset_token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ))
        db.commit()
    resp = {"message": "Se o e-mail estiver cadastrado, enviaremos instruções para redefinição de senha."}
    if reset_token and settings.environment != "production":
        resp["reset_token"] = reset_token
    return resp

@app.post("/api/v1/auth/reset-password", dependencies=[Depends(rate_limit)])
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(payload.token)))
    if not record or record.used_at is not None or record.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(400, "Token de recuperação inválido ou expirado")
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Usuário inválido")
    user.password_hash = hash_password(payload.new_password)
    record.used_at = now
    for rt in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))).all():
        rt.revoked_at = now
    db.commit()
    return {"message": "Senha redefinida com sucesso."}

@app.get("/api/v1/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(roles("ADMIN"))):
    return db.scalars(select(User).order_by(User.id)).all()

@app.post("/api/v1/users", response_model=UserOut, status_code=201)
def create_user(payload: AdminUserCreateIn, db: Session = Depends(get_db), admin: User = Depends(roles("ADMIN"))):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "E-mail já cadastrado")
    new_user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role=payload.role)
    db.add(new_user)
    db.flush()
    db.add(AuditLog(actor_user_id=admin.id, action="USER_CREATE", resource_type="user", resource_id=str(new_user.id), details={"role": new_user.role}))
    db.commit()
    db.refresh(new_user)
    return new_user

@app.patch("/api/v1/users/{user_id}/role", response_model=UserOut)
def update_user_role(user_id: int, payload: UserRoleUpdateIn, db: Session = Depends(get_db), admin: User = Depends(roles("ADMIN"))):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Usuário não encontrado")
    old_role = target.role
    target.role = payload.role
    db.add(AuditLog(actor_user_id=admin.id, action="USER_ROLE_CHANGE", resource_type="user", resource_id=str(target.id), details={"from": old_role, "to": payload.role}))
    db.commit()
    db.refresh(target)
    return target

@app.get("/api/v1/dashboard/stats", response_model=DashboardStatsOut)
def dashboard_stats(db: Session = Depends(get_db), user: User = Depends(roles("ADMIN", "SUPPORT"))):
    total_courses = db.scalar(select(func.count()).select_from(Course)) or 0
    total_enrollments = db.scalar(select(func.count()).select_from(Enrollment)) or 0
    pending = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.status == "PENDING")) or 0
    approved = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.status == "APPROVED")) or 0
    rejected = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.status == "REJECTED")) or 0
    cancelled = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.status == "CANCELLED")) or 0
    total_users = db.scalar(select(func.count()).select_from(User)) if user.role == "ADMIN" else None
    return {
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "pending_enrollments": pending,
        "approved_enrollments": approved,
        "rejected_enrollments": rejected,
        "cancelled_enrollments": cancelled,
        "total_users": total_users,
    }

@app.get("/api/v1/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(roles("ADMIN", "SUPPORT"))):
    safe_limit = min(max(limit, 1), 200)
    return db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(safe_limit)).all()

@app.get("/api/v1/enrollments/{enrollment_id}/history", response_model=list[AuditLogOut])
def enrollment_history(enrollment_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment:
        raise HTTPException(404, "Matrícula não encontrada")
    if user.role == "STUDENT" and enrollment.student_id != user.id:
        raise HTTPException(403, "Acesso negado")
    return db.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "enrollment", AuditLog.resource_id == str(enrollment_id))
        .order_by(AuditLog.id.desc())
    ).all()

@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user

@app.get("/api/v1/courses", response_model=list[CourseOut])
def courses(db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Course)
    if user.role == "STUDENT": stmt = stmt.where(Course.is_published.is_(True))
    return db.scalars(stmt.order_by(Course.title)).all()

@app.post("/api/v1/courses", response_model=CourseOut, status_code=201)
def create_course(payload: CourseIn, db: Session = Depends(get_db), user: User = Depends(roles("ADMIN"))):
    item = Course(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@app.post("/api/v1/enrollments", response_model=EnrollmentOut, status_code=201)
def enroll(payload: EnrollmentIn, db: Session = Depends(get_db), user: User = Depends(roles("STUDENT"))):
    course = db.get(Course, payload.course_id)
    if not course or not course.is_published: raise HTTPException(404, "Curso não encontrado")
    exists = db.scalar(select(Enrollment).where(Enrollment.student_id == user.id, Enrollment.course_id == course.id))
    if exists: raise HTTPException(409, "Já existe solicitação para este curso")
    item = Enrollment(student_id=user.id, course_id=course.id, status="PENDING")
    db.add(item); db.commit(); db.refresh(item); return item

@app.get("/api/v1/enrollments", response_model=list[EnrollmentOut])
def list_enrollments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Enrollment)
    if user.role == "STUDENT": stmt = stmt.where(Enrollment.student_id == user.id)
    return db.scalars(stmt.order_by(Enrollment.id.desc())).all()

@app.patch("/api/v1/enrollments/{enrollment_id}/status", response_model=EnrollmentOut)
def update_enrollment(enrollment_id: int, payload: StatusIn, db: Session = Depends(get_db), user: User = Depends(roles("ADMIN","SUPPORT"))):
    item = db.get(Enrollment, enrollment_id)
    if not item: raise HTTPException(404, "Matrícula não encontrada")
    previous = item.status; item.status = payload.status
    db.add(AuditLog(actor_user_id=user.id, action="ENROLLMENT_STATUS_CHANGED", resource_type="enrollment",
                    resource_id=str(item.id), details={"from":previous,"to":payload.status}))
    db.commit(); db.refresh(item); return item

@app.post("/api/v1/ai/chat")
async def chat(payload: ChatIn, user: User = Depends(current_user)):
    return {"answer": await ask_gemini(payload.question), "provider":"gemini"}
