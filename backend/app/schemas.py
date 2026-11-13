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
    token_type: str = "bearer"

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
