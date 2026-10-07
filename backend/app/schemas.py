from datetime import datetime as DateTime
from datetime import date as Date
from datetime import time as Time
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["student", "instructor", "supervisor", "admin"]
AttStatus = Literal["Present", "Late", "Absent", "Excused"]
ProjectStatus = Literal["Not Started", "In Progress", "Under Review", "Completed"]
MilestoneStatus = Literal["Not Started", "In Progress", "Completed"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- org ----
class DepartmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None


class DepartmentOut(ORM):
    id: int
    name: str
    description: str | None = None


class UnitIn(BaseModel):
    department_id: int
    name: str = Field(min_length=2, max_length=120)


class UnitOut(ORM):
    id: int
    department_id: int
    name: str


class BatchIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    year: int = Field(ge=2000, le=2100)
    start_date: Date | None = None
    end_date: Date | None = None
    is_active: bool = True


class BatchOut(ORM):
    id: int
    name: str
    year: int
    start_date: Date | None = None
    end_date: Date | None = None
    is_active: bool


# ---- users ----
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    role: Role = "student"
    department_id: int | None = None
    unit_id: int | None = None
    batch_id: int | None = None
    matric_no: str | None = None
    institution: str | None = None

    @field_validator("email")
    @classmethod
    def lower(cls, v):
        return v.lower()


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    department_id: int | None = None
    unit_id: int | None = None
    is_active: bool | None = None
    batch_id: int | None = None
    matric_no: str | None = None
    institution: str | None = None


class RoleUpdate(BaseModel):
    role: Role


class DestructiveAction(BaseModel):
    confirmation: str = Field(min_length=1, max_length=80)


class AuditLogOut(ORM):
    id: int
    admin_user_id: int | None
    action: str
    target_type: str
    target_id: str | None
    details: dict
    created_at: DateTime


class SyncIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)


# ---- training ----
class ProgramIn(BaseModel):
    batch_id: int
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None


class ClassIn(BaseModel):
    program_id: int
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    instructor_id: int | None = None
    enroll_batch: bool = True


class EnrollIn(BaseModel):
    student_ids: list[int] = []
    all_in_batch: bool = False


class MaterialIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    url: str


class SessionIn(BaseModel):
    training_class_id: int
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    instructor_id: int | None = None
    date: Date
    start_time: Time
    end_time: Time
    location: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    allowed_radius_meters: int | None = Field(default=None, ge=10, le=5000)

    @field_validator("end_time")
    @classmethod
    def after_start(cls, v, info):
        s = info.data.get("start_time")
        if s and v <= s:
            raise ValueError("end_time must be after start_time")
        return v


class SessionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    date: Date | None = None
    start_time: Time | None = None
    end_time: Time | None = None
    location: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    allowed_radius_meters: int | None = Field(default=None, ge=10, le=5000)
    instructor_id: int | None = None


# ---- attendance ----
class ScanIn(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)


class ManualIn(BaseModel):
    session_id: int
    student_id: int
    status: AttStatus
    remarks: str | None = Field(default=None, max_length=300)


# ---- projects ----
class MilestoneIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    due_date: Date | None = None
    status: MilestoneStatus = "Not Started"


class MilestoneUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: Date | None = None
    status: MilestoneStatus | None = None


class ProjectIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    batch_id: int | None = None
    start_date: Date | None = None
    deadline: Date | None = None
    member_ids: list[int] = []        # student ids
    supervisor_ids: list[int] = []    # user ids
    milestones: list[MilestoneIn] = []


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: Date | None = None
    deadline: Date | None = None
    status: ProjectStatus | None = None


class AssignIn(BaseModel):
    student_ids: list[int] = []
    supervisor_ids: list[int] = []


class Attachment(BaseModel):
    name: str
    url: str


class SubmissionIn(BaseModel):
    project_id: int
    milestone_id: int | None = None
    title: str = Field(min_length=2, max_length=200)
    worked_on: str | None = None
    challenges: str | None = None
    next_steps: str | None = None
    repo_url: str | None = None
    project_url: str | None = None
    attachments: list[Attachment] = Field(default_factory=list, max_length=10)


class ReviewIn(BaseModel):
    review_status: Literal["Approved", "Changes Requested"]
    feedback: str | None = Field(default=None, max_length=4000)
    mark_milestone_complete: bool = False


# ---- announcements ----
class AnnouncementIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    message: str = Field(min_length=2)
    audience: Literal["all", "batch", "department", "class"] = "all"
    batch_id: int | None = None
    department_id: int | None = None
    class_id: int | None = None
