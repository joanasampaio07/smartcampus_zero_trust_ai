from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal, get_db
from app.core.security import hash_password, verify_password, create_token
from app.core.dependencies import current_user, roles
from app.core.rate_limit import rate_limit
from app.models import User, Course, Enrollment, AuditLog
from app.schemas import RegisterIn, UserOut, TokenOut, CourseIn, CourseOut, EnrollmentIn, StatusIn, EnrollmentOut, ChatIn
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

@app.post("/api/v1/auth/login", response_model=TokenOut, dependencies=[Depends(rate_limit)])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos", headers={"WWW-Authenticate":"Bearer"})
    return {"access_token": create_token(str(user.id)), "token_type":"bearer"}

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
