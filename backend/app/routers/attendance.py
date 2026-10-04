import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..config import get_settings
from ..db import get_db
from ..deps import current_student, get_current_user, require_roles
from ..geo import haversine_meters
from ..models import (AttendanceRecord, AttendanceSession, ClassEnrollment, Student, TrainingClass, TrainingSession, User)
from ..schemas import ManualIn, ScanIn
from ..services import attendance_aggregate, session_out, student_stats
from ..timeutil import local_now, utcnow
from .training import can_manage_session

router = APIRouter(prefix="/api/attendance", tags=["attendance"])
staff = require_roles("admin", "instructor")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _new_token(att: AttendanceSession) -> dict:
    ttl = get_settings().qr_ttl_seconds
    token = secrets.token_urlsafe(24)
    att.token_hash = _hash(token)
    att.token_expires_at = utcnow() + timedelta(seconds=ttl)
    return {"token": token, "expires_at": att.token_expires_at.isoformat() + "Z", "ttl_seconds": ttl}


def _managed_session(db: Session, session_id: int, user: User) -> TrainingSession:
    s = db.get(TrainingSession, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    if not can_manage_session(user, s):
        raise HTTPException(403, "You can only manage attendance for your own sessions")
    return s


@router.post("/sessions/{session_id}/start")
def start_attendance(session_id: int, db: Session = Depends(get_db), me: User = Depends(staff)):
    s = _managed_session(db, session_id, me)
    att = db.scalar(select(AttendanceSession).where(AttendanceSession.session_id == s.id))
    if not att:
        att = AttendanceSession(session_id=s.id)
        db.add(att)
    att.is_active, att.started_by, att.started_at, att.ended_at = True, me.id, utcnow(), None
    s.attendance_status = "Open"
    payload = _new_token(att)
    db.commit()
    return payload


@router.post("/sessions/{session_id}/refresh")
def refresh_token(session_id: int, db: Session = Depends(get_db), me: User = Depends(staff)):
    s = _managed_session(db, session_id, me)
    att = db.scalar(select(AttendanceSession).where(AttendanceSession.session_id == s.id))
    if not att or not att.is_active:
        raise HTTPException(409, "Attendance is not open for this session")
    payload = _new_token(att)
    db.commit()
    return payload


@router.post("/sessions/{session_id}/stop")
def stop_attendance(session_id: int, db: Session = Depends(get_db), me: User = Depends(staff)):
    s = _managed_session(db, session_id, me)
    att = db.scalar(select(AttendanceSession).where(AttendanceSession.session_id == s.id))
    if not att or not att.is_active:
        raise HTTPException(409, "Attendance is not open for this session")
    att.is_active, att.ended_at, att.token_hash, att.token_expires_at = False, utcnow(), None, None
    s.attendance_status = "Closed"
    have = set(db.scalars(select(AttendanceRecord.student_id).where(AttendanceRecord.session_id == s.id)))
    enrolled = db.scalars(select(ClassEnrollment.student_id).where(ClassEnrollment.class_id == s.training_class_id))
    marked = 0
    for sid in enrolled:
        if sid not in have:
            db.add(AttendanceRecord(student_id=sid, session_id=s.id, status="Absent", marked_at=utcnow(), method="Manual",
                                    remarks="Auto-marked absent when attendance closed", marked_by=me.id))
            marked += 1
    db.commit()
    return {"closed": True, "auto_marked_absent": marked}


@router.get("/sessions/{session_id}/live")
def live(session_id: int, db: Session = Depends(get_db), me: User = Depends(staff)):
    s = _managed_session(db, session_id, me)
    att = db.scalar(select(AttendanceSession).where(AttendanceSession.session_id == s.id))
    recs = {r.student_id: r for r in db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id == s.id))}
    studs = db.scalars(select(Student).join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
                       .where(ClassEnrollment.class_id == s.training_class_id)
                       .options(joinedload(Student.user))).unique().all()
    roster, counts = [], {"Present": 0, "Late": 0, "Absent": 0, "Excused": 0, "Pending": 0}
    for st in sorted(studs, key=lambda x: x.user.full_name):
        r = recs.get(st.id)
        status = r.status if r else "Pending"
        counts[status] += 1
        roster.append({"student_id": st.id, "name": st.user.full_name, "email": st.user.email, "status": status,
                       "method": r.method if r else None,
                       "marked_at": r.marked_at.isoformat() + "Z" if r else None,
                       "distance_meters": r.distance_meters if r else None, "remarks": r.remarks if r else None})
    return {"session": session_out(s), "is_active": bool(att and att.is_active), "counts": counts,
            "total": len(roster), "roster": roster}


@router.post("/scan")
def scan(body: ScanIn, db: Session = Depends(get_db), student: Student = Depends(current_student)):
    cfg = get_settings()
    att = db.scalar(select(AttendanceSession).where(AttendanceSession.token_hash == _hash(body.token)))
    if not att:
        raise HTTPException(400, "Invalid QR code. Scan the code currently shown by your instructor.")
    if not att.is_active:
        raise HTTPException(400, "Attendance for this session is closed.")
    if not att.token_expires_at or att.token_expires_at < utcnow():
        raise HTTPException(410, "This QR code has expired. Scan the new code on the instructor's screen.")
    s = db.get(TrainingSession, att.session_id)
    if not db.scalar(select(ClassEnrollment.id).where(ClassEnrollment.class_id == s.training_class_id,
                                                      ClassEnrollment.student_id == student.id)):
        raise HTTPException(403, "You are not enrolled in this training class.")
    if body.accuracy is not None and body.accuracy > cfg.max_gps_accuracy_meters:
        raise HTTPException(400, f"Your location is too imprecise ({round(body.accuracy)} m). "
                                 "Move outdoors or turn on high-accuracy location, then try again.")
    existing = db.scalar(select(AttendanceRecord).where(AttendanceRecord.student_id == student.id,
                                                        AttendanceRecord.session_id == s.id))
    if existing and existing.status != "Absent":
        raise HTTPException(409, "You have already checked in for this session.")
    dist = haversine_meters(body.latitude, body.longitude, s.latitude, s.longitude)
    if dist > s.allowed_radius_meters:
        raise HTTPException(403, f"You are {round(dist)} m from the venue. You must be within "
                                 f"{s.allowed_radius_meters} m to check in.")
    start = datetime.combine(s.date, s.start_time)
    status = "Late" if local_now() > start + timedelta(minutes=cfg.late_after_minutes) else "Present"
    if existing:  # auto-absent row from an earlier close; session was re-opened
        rec = existing
        rec.status, rec.marked_at, rec.method = status, utcnow(), "QR"
        rec.latitude, rec.longitude, rec.distance_meters, rec.remarks, rec.marked_by = (
            body.latitude, body.longitude, round(dist, 1), None, None)
    else:
        rec = AttendanceRecord(student_id=student.id, session_id=s.id, status=status, marked_at=utcnow(), method="QR",
                               latitude=body.latitude, longitude=body.longitude, distance_meters=round(dist, 1))
        db.add(rec)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already checked in for this session.")
    return {"status": status, "distance_meters": round(dist, 1), "session": session_out(s, status, rec.marked_at)}


@router.post("/manual")
def manual(body: ManualIn, db: Session = Depends(get_db), me: User = Depends(staff)):
    s = _managed_session(db, body.session_id, me)
    if not db.get(Student, body.student_id):
        raise HTTPException(404, "Student not found")
    if not db.scalar(select(ClassEnrollment.id).where(ClassEnrollment.class_id == s.training_class_id,
                                                      ClassEnrollment.student_id == body.student_id)):
        raise HTTPException(422, "Student is not enrolled in this class")
    rec = db.scalar(select(AttendanceRecord).where(AttendanceRecord.student_id == body.student_id,
                                                   AttendanceRecord.session_id == s.id))
    if rec:
        rec.status, rec.method, rec.marked_at, rec.marked_by, rec.remarks = body.status, "Manual", utcnow(), me.id, body.remarks
        rec.latitude = rec.longitude = rec.distance_meters = None
    else:
        rec = AttendanceRecord(student_id=body.student_id, session_id=s.id, status=body.status, marked_at=utcnow(),
                               method="Manual", remarks=body.remarks, marked_by=me.id)
        db.add(rec)
    db.commit()
    return {"id": rec.id, "status": rec.status, "method": rec.method}


@router.get("/me")
def my_attendance(db: Session = Depends(get_db), student: Student = Depends(current_student)):
    stats = student_stats(db, [student.id])[student.id]
    rows = db.execute(
        select(AttendanceRecord, TrainingSession, TrainingClass).join(TrainingSession, TrainingSession.id == AttendanceRecord.session_id)
        .join(TrainingClass, TrainingClass.id == TrainingSession.training_class_id)
        .where(AttendanceRecord.student_id == student.id).order_by(TrainingSession.date.desc(), TrainingSession.start_time.desc()))
    history = [{"id": r.id, "date": s.date.isoformat(), "training": c.name, "session": s.title, "status": r.status,
                "method": r.method, "checked_in_at": r.marked_at.isoformat() + "Z"} for r, s, c in rows]
    return {"summary": stats, "history": history}


@router.get("/summary")
def summary(batch_id: int | None = None, department_id: int | None = None, db: Session = Depends(get_db),
            me: User = Depends(staff)):
    return attendance_aggregate(db, instructor_id=me.id if me.role == "instructor" else None,
                                batch_id=batch_id, department_id=department_id)
