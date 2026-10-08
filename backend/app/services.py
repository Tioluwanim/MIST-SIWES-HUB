from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (AttendanceRecord, ClassEnrollment, Project, ProjectMilestone, Student, TrainingClass,
                     TrainingProgram, TrainingSession, User)
from .timeutil import utcnow


# ---------- serializers ----------
def user_out(u: User) -> dict:
    st = u.student
    return {
        "id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active,
        "is_demo": u.is_demo,
        "department": {"id": u.department.id, "name": u.department.name} if u.department else None,
        "unit": {"id": u.unit.id, "name": u.unit.name} if u.unit else None,
        "student_id": st.id if st else None,
        "batch": {"id": st.batch.id, "name": st.batch.name} if st and st.batch else None,
        "matric_no": st.matric_no if st else None,
        "institution": st.institution if st else None,
        "phone": st.phone if st else None,
    }


def session_out(s: TrainingSession, my_status: str | None = None, my_marked_at=None) -> dict:
    c = s.training_class
    return {
        "id": s.id, "title": s.title, "description": s.description,
        "training_class_id": c.id, "class_name": c.name, "program_name": c.program.name,
        "instructor_id": s.instructor_id, "instructor_name": s.instructor.full_name if s.instructor else None,
        "date": s.date.isoformat(), "start_time": s.start_time.strftime("%H:%M"), "end_time": s.end_time.strftime("%H:%M"),
        "location": s.location, "latitude": s.latitude, "longitude": s.longitude,
        "allowed_radius_meters": s.allowed_radius_meters, "attendance_status": s.attendance_status,
        "my_status": my_status, "my_marked_at": my_marked_at.isoformat() if my_marked_at else None,
    }


def milestone_out(m: ProjectMilestone) -> dict:
    return {"id": m.id, "project_id": m.project_id, "title": m.title, "description": m.description,
            "status": m.status, "due_date": m.due_date.isoformat() if m.due_date else None,
            "completed_at": m.completed_at.isoformat() if m.completed_at else None}


def project_out(p: Project, detail: bool = True) -> dict:
    out = {
        "id": p.id, "title": p.title, "description": p.description, "status": p.status, "progress": p.progress,
        "batch_id": p.batch_id,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "deadline": p.deadline.isoformat() if p.deadline else None,
        "member_count": len(p.members),
        "members": [{"student_id": m.student_id, "name": m.student.user.full_name, "email": m.student.user.email}
                    for m in p.members],
        "supervisors": [{"id": s.user_id, "name": s.user.full_name} for s in p.supervisors],
    }
    if detail:
        out["milestones"] = [milestone_out(m) for m in p.milestones]
    return out


def submission_out(s) -> dict:
    return {
        "id": s.id, "project_id": s.project_id, "project_title": s.project.title,
        "milestone_id": s.milestone_id, "student_id": s.student_id, "student_name": s.student.user.full_name,
        "title": s.title, "worked_on": s.worked_on, "challenges": s.challenges, "next_steps": s.next_steps,
        "repo_url": s.repo_url, "project_url": s.project_url, "attachments": s.attachments or [],
        "review_status": s.review_status, "feedback": s.feedback,
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ---------- enrolment ----------
def enroll_students(db: Session, class_id: int, student_ids: list[int]) -> int:
    existing = set(db.scalars(select(ClassEnrollment.student_id).where(ClassEnrollment.class_id == class_id)))
    added = 0
    for sid in set(student_ids) - existing:
        db.add(ClassEnrollment(class_id=class_id, student_id=sid))
        added += 1
    return added


def enroll_batch_in_class(db: Session, class_id: int) -> int:
    batch_id = db.scalar(select(TrainingProgram.batch_id).join(TrainingClass, TrainingClass.program_id == TrainingProgram.id)
                         .where(TrainingClass.id == class_id))
    ids = list(db.scalars(select(Student.id).where(Student.batch_id == batch_id)))
    return enroll_students(db, class_id, ids)


def enroll_student_in_batch_classes(db: Session, student: Student) -> None:
    if not student.batch_id:
        return
    class_ids = list(db.scalars(select(TrainingClass.id).join(TrainingProgram, TrainingClass.program_id == TrainingProgram.id)
                                .where(TrainingProgram.batch_id == student.batch_id)))
    for cid in class_ids:
        enroll_students(db, cid, [student.id])


# ---------- attendance stats ----------
def rate(present: int, late: int, excused: int, total: int) -> float:
    denom = total - excused
    return round(100 * (present + late) / denom, 1) if denom > 0 else 0.0


def student_stats(db: Session, student_ids: list[int] | None = None) -> dict[int, dict]:
    q = select(AttendanceRecord.student_id, AttendanceRecord.status, func.count()).group_by(
        AttendanceRecord.student_id, AttendanceRecord.status)
    if student_ids is not None:
        q = q.where(AttendanceRecord.student_id.in_(student_ids or [0]))
    acc: dict[int, dict] = defaultdict(lambda: {"Present": 0, "Late": 0, "Absent": 0, "Excused": 0})
    for sid, st, n in db.execute(q):
        acc[sid][st] = n
    out = {}
    for sid in (student_ids if student_ids is not None else list(acc)):
        a = acc[sid]
        total = sum(a.values())
        out[sid] = {"total": total, "present": a["Present"], "late": a["Late"], "absent": a["Absent"],
                    "excused": a["Excused"], "rate": rate(a["Present"], a["Late"], a["Excused"], total)}
    return out


def attendance_aggregate(db: Session, instructor_id: int | None = None, batch_id: int | None = None,
                         department_id: int | None = None, since: date | None = None) -> dict:
    q = (select(AttendanceRecord.status, AttendanceRecord.student_id, TrainingSession.date,
                User.full_name, Student.id, Student.batch_id, User.department_id, User.unit_id)
         .join(TrainingSession, TrainingSession.id == AttendanceRecord.session_id)
         .join(Student, Student.id == AttendanceRecord.student_id)
         .join(User, User.id == Student.user_id))
    if instructor_id:
        q = q.where(TrainingSession.instructor_id == instructor_id)
    if batch_id:
        q = q.where(Student.batch_id == batch_id)
    if department_id:
        q = q.where(User.department_id == department_id)
    if since:
        q = q.where(TrainingSession.date >= since)
    from .models import Department, Unit
    dept = {d.id: d.name for d in db.scalars(select(Department))}
    unit = {u.id: u.name for u in db.scalars(select(Unit))}

    def blank():
        return {"Present": 0, "Late": 0, "Absent": 0, "Excused": 0}
    overall, by_dept, by_unit, by_day = blank(), defaultdict(blank), defaultdict(blank), defaultdict(blank)
    per_student: dict[int, dict] = {}
    for st, sid, d, name, _, _, dep_id, unit_id in db.execute(q):
        overall[st] += 1
        by_dept[dept.get(dep_id, "Unassigned")][st] += 1
        by_unit[unit.get(unit_id, "Unassigned")][st] += 1
        by_day[d.isoformat()][st] += 1
        ps = per_student.setdefault(sid, {"student_id": sid, "name": name, **blank()})
        ps[st] += 1

    def fin(c):
        t = sum(c.values())
        return {**c, "total": t, "rate": rate(c["Present"], c["Late"], c["Excused"], t)}
    low = []
    for ps in per_student.values():
        f = fin({k: ps[k] for k in ("Present", "Late", "Absent", "Excused")})
        if f["total"] >= 1 and f["rate"] < 75:
            low.append({"student_id": ps["student_id"], "name": ps["name"], **f})
    low.sort(key=lambda r: r["rate"])
    return {
        "overall": fin(overall),
        "by_department": [{"name": k, **fin(v)} for k, v in sorted(by_dept.items())],
        "by_unit": [{"name": k, **fin(v)} for k, v in sorted(by_unit.items())],
        "trend": [{"date": k, **fin(v)} for k, v in sorted(by_day.items())][-14:],
        "low_attendance": low[:10],
    }


# ---------- projects ----------
def recompute_project(p: Project) -> None:
    ms = p.milestones
    done = sum(1 for m in ms if m.status == "Completed")
    p.progress = round(100 * done / len(ms)) if ms else 0
    if ms and done == len(ms) and p.status in ("Not Started", "In Progress"):
        p.status = "Under Review"
    elif p.status == "Not Started" and any(m.status != "Not Started" for m in ms):
        p.status = "In Progress"


def set_milestone_status(m: ProjectMilestone, status: str) -> None:
    m.status = status
    m.completed_at = utcnow() if status == "Completed" else None
