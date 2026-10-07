from datetime import date, datetime, time

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer,
                        String, Text, Time, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    # Seeded records are disposable; production records are never marked demo.
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)


class Department(TimestampMixin, Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    units: Mapped[list["Unit"]] = relationship(back_populates="department", cascade="all, delete-orphan")


class Unit(TimestampMixin, Base):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("department_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    department: Mapped[Department] = relationship(back_populates="units")


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(20), default="student", index=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    department: Mapped[Department | None] = relationship()
    unit: Mapped[Unit | None] = relationship()
    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class SiwesBatch(TimestampMixin, Base):
    __tablename__ = "siwes_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    year: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Student(TimestampMixin, Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("siwes_batches.id", ondelete="SET NULL"), index=True)
    matric_no: Mapped[str | None] = mapped_column(String(40))
    institution: Mapped[str | None] = mapped_column(String(160))
    user: Mapped[User] = relationship(back_populates="student")
    batch: Mapped[SiwesBatch | None] = relationship()


class TrainingProgram(TimestampMixin, Base):
    __tablename__ = "training_programs"
    __table_args__ = (UniqueConstraint("batch_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("siwes_batches.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    batch: Mapped[SiwesBatch] = relationship()


class TrainingClass(TimestampMixin, Base):
    __tablename__ = "training_classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("training_programs.id", ondelete="CASCADE"), index=True)
    instructor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    program: Mapped[TrainingProgram] = relationship()
    instructor: Mapped[User | None] = relationship()


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    __table_args__ = (UniqueConstraint("class_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("training_classes.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)


class TrainingMaterial(TimestampMixin, Base):
    __tablename__ = "training_materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("training_classes.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class TrainingSession(TimestampMixin, Base):
    __tablename__ = "training_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    training_class_id: Mapped[int] = mapped_column(ForeignKey("training_classes.id", ondelete="CASCADE"), index=True)
    instructor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    location: Mapped[str | None] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    allowed_radius_meters: Mapped[int] = mapped_column(Integer, default=100)
    attendance_status: Mapped[str] = mapped_column(String(20), default="Not Started")  # Not Started | Open | Closed
    training_class: Mapped[TrainingClass] = relationship()
    instructor: Mapped[User | None] = relationship()


class AttendanceSession(Base):
    """One per training session. Holds the short-lived rotating QR token (stored hashed)."""
    __tablename__ = "attendance_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id", ondelete="CASCADE"), unique=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    started_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("student_id", "session_id", name="uq_attendance_student_session"),
                      Index("ix_attendance_session_status", "session_id", "status"))
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(12))  # Present | Late | Absent | Excused
    marked_at: Mapped[datetime] = mapped_column(DateTime)
    method: Mapped[str] = mapped_column(String(10))  # QR | Manual
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    distance_meters: Mapped[float | None] = mapped_column(Float)
    remarks: Mapped[str | None] = mapped_column(String(300))
    marked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    student: Mapped[Student] = relationship()
    session: Mapped[TrainingSession] = relationship()


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("siwes_batches.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="Not Started", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    supervisors: Mapped[list["ProjectSupervisor"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectMilestone.position")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    project: Mapped[Project] = relationship(back_populates="members")
    student: Mapped[Student] = relationship()


class ProjectSupervisor(Base):
    __tablename__ = "project_supervisors"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project: Mapped[Project] = relationship(back_populates="supervisors")
    user: Mapped[User] = relationship()


class ProjectMilestone(TimestampMixin, Base):
    __tablename__ = "project_milestones"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Not Started")
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    position: Mapped[int] = mapped_column(Integer, default=0)
    project: Mapped[Project] = relationship(back_populates="milestones")


class ProjectSubmission(TimestampMixin, Base):
    __tablename__ = "project_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    milestone_id: Mapped[int | None] = mapped_column(ForeignKey("project_milestones.id", ondelete="SET NULL"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    worked_on: Mapped[str | None] = mapped_column(Text)
    challenges: Mapped[str | None] = mapped_column(Text)
    next_steps: Mapped[str | None] = mapped_column(Text)
    repo_url: Mapped[str | None] = mapped_column(String(500))
    project_url: Mapped[str | None] = mapped_column(String(500))
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending | Approved | Changes Requested
    feedback: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    student: Mapped[Student] = relationship()
    project: Mapped[Project] = relationship()


class Announcement(TimestampMixin, Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(20), default="all")  # all | batch | department | class
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("siwes_batches.id", ondelete="CASCADE"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"))
    class_id: Mapped[int | None] = mapped_column(ForeignKey("training_classes.id", ondelete="CASCADE"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    admin_user: Mapped[User | None] = relationship()
