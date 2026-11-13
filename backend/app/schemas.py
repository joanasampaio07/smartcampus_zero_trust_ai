from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=256)

class LogoutIn(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=256)

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)

class AdminUserCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(pattern="^(ADMIN|SUPPORT|STUDENT)$")

class UserRoleUpdateIn(BaseModel):
    role: str = Field(pattern="^(ADMIN|SUPPORT|STUDENT)$")

class CourseIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=5000)
    workload_hours: int = Field(default=0, ge=0, le=10000)
    is_published: bool = True

class CourseOut(CourseIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EnrollmentIn(BaseModel):
    course_id: int

class StatusIn(BaseModel):
    status: str = Field(pattern="^(PENDING|APPROVED|REJECTED|CANCELLED)$")

class EnrollmentOut(BaseModel):
    id: int
    student_id: int
    course_id: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=4000)

class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int
    action: str
    resource_type: str
    resource_id: str
    details: dict
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DashboardStatsOut(BaseModel):
    total_courses: int
    total_enrollments: int
    pending_enrollments: int
    approved_enrollments: int
    rejected_enrollments: int
    cancelled_enrollments: int
    total_users: int | None = None
