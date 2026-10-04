from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (AttendanceRecord, ClassEnrollment, SiwesBatch, Student, TrainingClass, TrainingMaterial,
                      TrainingProgram, TrainingSession, User)
from ..schemas import (ClassIn, EnrollIn, MaterialIn, ProgramIn, SessionIn, SessionUpdate)
from ..services import enroll_batch_in_class, enroll_students, session_out, student_stats, user_out
from ..storage import validate_url
from ..timeutil import local_now

router = APIRouter(prefix="/api/training", tags=["training"])
sessions_router = APIRouter(prefix="/api/sessions", tags=["sessions"])
admin = require_roles("admin")
staff = require_roles("admin", "instructor")


def _class_out(c: TrainingClass, n: int | None = None) -> dict:
    return {"id": c.id, "name": c.name, "description": c.description, "program_id": c.program_id,
            "program_name": c.program.name, "batch_id": c.program.batch_id, "batch_name": c.program.batch.name,
            "instructor_id": c.instructor_id, "instructor_name": c.instructor.full_name if c.instructor else None,
            "student_count": n}


def _can_manage_class(user: User, c: TrainingClass) -> bool:
    return user.role == "admin" or (user.role == "instructor" and c.instructor_id == user.id)


@router.get("/programs")
def list_programs(batch_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = select(TrainingProgram).options(joinedload(TrainingProgram.batch)).order_by(TrainingProgram.name)
    if batch_id:
        q = q.where(TrainingProgram.batch_id == batch_id)
    return [{"id": p.id, "name": p.name, "description": p.description, "batch_id": p.batch_id,
             "batch_name": p.batch.name} for p in db.scalars(q)]


@router.post("/programs", status_code=201)
def create_program(body: ProgramIn, db: Session = Depends(get_db), _: User = Depends(admin)):
    if not db.get(SiwesBatch, body.batch_id):
        raise HTTPException(404, "Batch not found")
    p = TrainingProgram(**body.model_dump())
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That program already exists in the batch")
    return {"id": p.id, "name": p.name, "batch_id": p.batch_id}


@router.get("/classes")
def list_classes(batch_id: int | None = None, db: Session = Depends(get_db),
                 me: User = Depends(require_roles("student", "instructor", "admin"))):
    q = (select(TrainingClass).join(TrainingProgram, TrainingProgram.id == TrainingClass.program_id)
         .options(joinedload(TrainingClass.program).joinedload(TrainingProgram.batch), joinedload(TrainingClass.instructor))
         .order_by(TrainingClass.name))
    if batch_id:
        q = q.where(TrainingProgram.batch_id == batch_id)
    if me.role == "instructor":
        q = q.where(TrainingClass.instructor_id == me.id)
    elif me.role == "student":
        st = db.scalar(select(Student).where(Student.user_id == me.id))
        q = q.where(TrainingClass.id.in_(select(ClassEnrollment.class_id).where(ClassEnrollment.student_id == (st.id if st else 0))))
    rows = db.scalars(q).unique().all()
    counts = {}
    for cid, in db.execute(select(ClassEnrollment.class_id)):
        counts[cid] = counts.get(cid, 0) + 1
    return [_class_out(c, counts.get(c.id, 0)) for c in rows]


@router.post("/classes", status_code=201)
def create_class(body: ClassIn, db: Session = Depends(get_db), _: User = Depends(admin)):
    if not db.get(TrainingProgram, body.program_id):
        raise HTTPException(404, "Program not found")
    if body.instructor_id:
        ins = db.get(User, body.instructor_id)
        if not ins or ins.role != "instructor":
            raise HTTPException(422, "instructor_id must belong to an instructor")
    c = TrainingClass(program_id=body.program_id, name=body.name, description=body.description,
                      instructor_id=body.instructor_id)
    db.add(c)
    db.flush()
    n = enroll_batch_in_class(db, c.id) if body.enroll_batch else 0
    db.commit()
    return _class_out(c, n)


@router.post("/classes/{class_id}/enroll")
def enroll(class_id: int, body: EnrollIn, db: Session = Depends(get_db), _: User = Depends(admin)):
    if not db.get(TrainingClass, class_id):
        raise HTTPException(404, "Class not found")
    added = enroll_students(db, class_id, body.student_ids)
    if body.all_in_batch:
        added += enroll_batch_in_class(db, class_id)
    db.commit()
    return {"enrolled": added}


@router.get("/classes/{class_id}/students")
def class_students(class_id: int, db: Session = Depends(get_db), me: User = Depends(staff)):
    c = db.get(TrainingClass, class_id)
    if not c:
        raise HTTPException(404, "Class not found")
    if not _can_manage_class(me, c):
        raise HTTPException(403, "Not your class")
    studs = db.scalars(select(Student).join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
                       .where(ClassEnrollment.class_id == class_id)).all()
    stats = student_stats(db, [s.id for s in studs])
    return [{**user_out(s.user), "attendance": stats[s.id]} for s in studs]


@router.get("/classes/{class_id}/materials")
def list_materials(class_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    if me.role == "student":
        st = db.scalar(select(Student).where(Student.user_id == me.id))
        ok = st and db.scalar(select(ClassEnrollment.id).where(ClassEnrollment.class_id == class_id,
                                                              ClassEnrollment.student_id == st.id))
        if not ok:
            raise HTTPException(403, "You are not enrolled in this class")
    rows = db.scalars(select(TrainingMaterial).where(TrainingMaterial.class_id == class_id).order_by(TrainingMaterial.id.desc()))
    return [{"id": m.id, "title": m.title, "url": m.url, "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in rows]


@router.post("/classes/{class_id}/materials", status_code=201)
def add_material(class_id: int, body: MaterialIn, db: Session = Depends(get_db), me: User = Depends(staff)):
    c = db.get(TrainingClass, class_id)
    if not c:
        raise HTTPException(404, "Class not found")
    if not _can_manage_class(me, c):
        raise HTTPException(403, "Not your class")
    if not body.url.startswith("/api/files/"):
        validate_url(body.url)
    m = TrainingMaterial(class_id=class_id, title=body.title, url=body.url, uploaded_by=me.id)
    db.add(m)
    db.commit()
    return {"id": m.id, "title": m.title, "url": m.url}


# ---------------- sessions ----------------
def _load_session(db: Session, sid: int) -> TrainingSession:
    s = db.get(TrainingSession, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


def can_manage_session(user: User, s: TrainingSession) -> bool:
    return user.role == "admin" or (user.role == "instructor" and
                                    user.id in (s.instructor_id, s.training_class.instructor_id))


@sessions_router.get("")
def list_sessions(class_id: int | None = None, today: bool = False, upcoming: bool = False,
                  date_from: date | None = None, date_to: date | None = None, mine: bool = False,
                  db: Session = Depends(get_db), me: User = Depends(require_roles("student", "instructor", "admin"))):
    q = (select(TrainingSession).options(joinedload(TrainingSession.training_class).joinedload(TrainingClass.program),
                                         joinedload(TrainingSession.instructor))
         .order_by(TrainingSession.date.desc(), TrainingSession.start_time))
    if class_id:
        q = q.where(TrainingSession.training_class_id == class_id)
    if today:
        q = q.where(TrainingSession.date == local_now().date())
    if upcoming:
        q = q.where(TrainingSession.date >= local_now().date()).order_by(None).order_by(TrainingSession.date, TrainingSession.start_time)
    if date_from:
        q = q.where(TrainingSession.date >= date_from)
    if date_to:
        q = q.where(TrainingSession.date <= date_to)
    mine_status = {}
    if me.role == "instructor":
        q = q.where(TrainingSession.instructor_id == me.id)
    elif me.role == "student":
        st = db.scalar(select(Student).where(Student.user_id == me.id))
        sid = st.id if st else 0
        q = q.where(TrainingSession.training_class_id.in_(select(ClassEnrollment.class_id).where(ClassEnrollment.student_id == sid)))
        for r in db.scalars(select(AttendanceRecord).where(AttendanceRecord.student_id == sid)):
            mine_status[r.session_id] = r
    rows = db.scalars(q).unique().all()
    return [session_out(s, mine_status[s.id].status if s.id in mine_status else None,
                        mine_status[s.id].marked_at if s.id in mine_status else None) for s in rows]


@sessions_router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    s = _load_session(db, session_id)
    if me.role == "student":
        st = db.scalar(select(Student).where(Student.user_id == me.id))
        if not st or not db.scalar(select(ClassEnrollment.id).where(ClassEnrollment.class_id == s.training_class_id,
                                                                    ClassEnrollment.student_id == st.id)):
            raise HTTPException(403, "You are not enrolled in this class")
    elif me.role == "instructor" and not can_manage_session(me, s):
        raise HTTPException(403, "Not your session")
    return session_out(s)


@sessions_router.post("", status_code=201)
def create_session(body: SessionIn, db: Session = Depends(get_db), me: User = Depends(staff)):
    c = db.get(TrainingClass, body.training_class_id)
    if not c:
        raise HTTPException(404, "Class not found")
    if not _can_manage_class(me, c):
        raise HTTPException(403, "You can only create sessions for your own classes")
    instructor_id = me.id if me.role == "instructor" else (body.instructor_id or c.instructor_id)
    data = body.model_dump(exclude={"instructor_id", "allowed_radius_meters"})
    s = TrainingSession(**data, instructor_id=instructor_id,
                        allowed_radius_meters=body.allowed_radius_meters or get_settings().default_radius_meters)
    db.add(s)
    db.commit()
    return session_out(s)


@sessions_router.patch("/{session_id}")
def update_session(session_id: int, body: SessionUpdate, db: Session = Depends(get_db), me: User = Depends(staff)):
    s = _load_session(db, session_id)
    if not can_manage_session(me, s):
        raise HTTPException(403, "Not your session")
    data = body.model_dump(exclude_unset=True)
    if me.role != "admin":
        data.pop("instructor_id", None)
    for k, v in data.items():
        setattr(s, k, v)
    if s.end_time <= s.start_time:
        raise HTTPException(422, "end_time must be after start_time")
    db.commit()
    return session_out(s)


@sessions_router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db), _: User = Depends(admin)):
    db.delete(_load_session(db, session_id))
    db.commit()
