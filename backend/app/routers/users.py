from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..deps import require_roles
from ..models import (ClassEnrollment, Department, Project, ProjectMember, ProjectSupervisor, SiwesBatch, Student,
                      TrainingClass, Unit, User)
from ..schemas import UserCreate, UserUpdate
from ..services import enroll_student_in_batch_classes, student_stats, user_out

router = APIRouter(prefix="/api/users", tags=["users"])
students_router = APIRouter(prefix="/api/students", tags=["students"])
admin = require_roles("admin")


def _check_refs(db: Session, department_id, unit_id, batch_id):
    if department_id and not db.get(Department, department_id):
        raise HTTPException(404, "Department not found")
    if unit_id:
        u = db.get(Unit, unit_id)
        if not u:
            raise HTTPException(404, "Unit not found")
        if department_id and u.department_id != department_id:
            raise HTTPException(422, "Unit does not belong to that department")
    if batch_id and not db.get(SiwesBatch, batch_id):
        raise HTTPException(404, "Batch not found")


@router.get("")
def list_users(role: str | None = None, q: str | None = None, db: Session = Depends(get_db),
               _: User = Depends(require_roles("admin", "instructor"))):
    stmt = select(User).options(joinedload(User.student)).order_by(User.full_name)
    if role:
        stmt = stmt.where(User.role == role)
    if q:
        stmt = stmt.where(or_(User.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    return [user_out(u) for u in db.scalars(stmt).unique()]


@router.post("", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), _: User = Depends(admin)):
    """Pre-provision an account. It is linked when that person signs in with the same *verified* email."""
    _check_refs(db, body.department_id, body.unit_id, body.batch_id)
    u = User(email=body.email, full_name=body.full_name, role=body.role,
             department_id=body.department_id, unit_id=body.unit_id)
    if body.role == "student":
        u.student = Student(batch_id=body.batch_id, matric_no=body.matric_no, institution=body.institution)
    db.add(u)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A user with that email already exists")
    if u.student:
        enroll_student_in_batch_classes(db, u.student)
    db.commit()
    return user_out(u)


@router.patch("/{user_id}")
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), me: User = Depends(admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    data = body.model_dump(exclude_unset=True)
    _check_refs(db, data.get("department_id"), data.get("unit_id"), data.get("batch_id"))
    if u.id == me.id and (data.get("role") not in (None, "admin") or data.get("is_active") is False):
        raise HTTPException(400, "You cannot demote or disable your own account")
    for k in ("full_name", "role", "department_id", "unit_id", "is_active"):
        if k in data:
            setattr(u, k, data[k])
    if u.role == "student" and not u.student:
        u.student = Student()
    if u.student:
        for k in ("batch_id", "matric_no", "institution"):
            if k in data:
                setattr(u.student, k, data[k])
        db.flush()
        if "batch_id" in data:
            enroll_student_in_batch_classes(db, u.student)
    db.commit()
    return user_out(u)


@students_router.get("")
def list_students(batch_id: int | None = None, department_id: int | None = None, unit_id: int | None = None,
                  class_id: int | None = None, q: str | None = None, db: Session = Depends(get_db),
                  me: User = Depends(require_roles("admin", "instructor", "supervisor"))):
    stmt = (select(Student).join(User, User.id == Student.user_id)
            .options(joinedload(Student.user).joinedload(User.department), joinedload(Student.user).joinedload(User.unit),
                     joinedload(Student.batch)).order_by(User.full_name))
    if batch_id:
        stmt = stmt.where(Student.batch_id == batch_id)
    if department_id:
        stmt = stmt.where(User.department_id == department_id)
    if unit_id:
        stmt = stmt.where(User.unit_id == unit_id)
    if q:
        stmt = stmt.where(or_(User.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"), Student.matric_no.ilike(f"%{q}%")))
    if class_id:
        stmt = stmt.where(Student.id.in_(select(ClassEnrollment.student_id).where(ClassEnrollment.class_id == class_id)))
    # scope: instructors see only students enrolled in their classes; supervisors only their project members
    if me.role == "instructor":
        mine = select(TrainingClass.id).where(TrainingClass.instructor_id == me.id)
        stmt = stmt.where(Student.id.in_(select(ClassEnrollment.student_id).where(ClassEnrollment.class_id.in_(mine))))
    elif me.role == "supervisor":
        pids = select(ProjectSupervisor.project_id).where(ProjectSupervisor.user_id == me.id)
        stmt = stmt.where(Student.id.in_(select(ProjectMember.student_id).where(ProjectMember.project_id.in_(pids))))
    rows = db.scalars(stmt).unique().all()
    stats = student_stats(db, [s.id for s in rows])
    return [{**user_out(s.user), "student_id": s.id, "attendance": stats[s.id]} for s in rows]
