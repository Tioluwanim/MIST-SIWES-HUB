from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Announcement, ClassEnrollment, Student, TrainingClass, User
from ..schemas import AnnouncementIn

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


def _out(a: Announcement) -> dict:
    return {"id": a.id, "title": a.title, "message": a.message, "audience": a.audience, "batch_id": a.batch_id,
            "department_id": a.department_id, "class_id": a.class_id,
            "created_at": a.created_at.isoformat() if a.created_at else None}


def visible_to_student(db: Session, me: User, limit: int | None = None) -> list[Announcement]:
    st = db.scalar(select(Student).where(Student.user_id == me.id))
    class_ids = list(db.scalars(select(ClassEnrollment.class_id).where(ClassEnrollment.student_id == (st.id if st else 0))))
    cond = [Announcement.audience == "all"]
    if st and st.batch_id:
        cond.append(and_(Announcement.audience == "batch", Announcement.batch_id == st.batch_id))
    if me.department_id:
        cond.append(and_(Announcement.audience == "department", Announcement.department_id == me.department_id))
    if class_ids:
        cond.append(and_(Announcement.audience == "class", Announcement.class_id.in_(class_ids)))
    q = select(Announcement).where(or_(*cond)).order_by(Announcement.created_at.desc(), Announcement.id.desc())
    if limit:
        q = q.limit(limit)
    return list(db.scalars(q))


@router.get("")
def list_announcements(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    if me.role == "student":
        return [_out(a) for a in visible_to_student(db, me)]
    q = select(Announcement).order_by(Announcement.created_at.desc(), Announcement.id.desc())
    return [_out(a) for a in db.scalars(q)]


@router.post("", status_code=201)
def create_announcement(body: AnnouncementIn, db: Session = Depends(get_db),
                        me: User = Depends(require_roles("admin", "instructor"))):
    if body.audience == "batch" and not body.batch_id:
        raise HTTPException(422, "batch_id is required for a batch announcement")
    if body.audience == "department" and not body.department_id:
        raise HTTPException(422, "department_id is required for a department announcement")
    if body.audience == "class":
        c = db.get(TrainingClass, body.class_id) if body.class_id else None
        if not c:
            raise HTTPException(422, "A valid class_id is required for a class announcement")
        if me.role == "instructor" and c.instructor_id != me.id:
            raise HTTPException(403, "You can only announce to your own classes")
    elif me.role == "instructor":
        raise HTTPException(403, "Instructors can only send announcements to their own classes")
    a = Announcement(**body.model_dump(), created_by=me.id)
    db.add(a)
    db.commit()
    return _out(a)


@router.delete("/{announcement_id}", status_code=204)
def delete_announcement(announcement_id: int, db: Session = Depends(get_db),
                        me: User = Depends(require_roles("admin", "instructor"))):
    a = db.get(Announcement, announcement_id)
    if not a:
        raise HTTPException(404, "Announcement not found")
    if me.role != "admin" and a.created_by != me.id:
        raise HTTPException(403, "You can only delete your own announcements")
    db.delete(a)
    db.commit()
