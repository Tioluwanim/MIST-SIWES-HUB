from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..deps import current_student, require_roles
from ..models import (AttendanceRecord, ClassEnrollment, Project, ProjectMember, ProjectSubmission, ProjectSupervisor,
                      Student, TrainingClass, TrainingSession, User)
from ..services import attendance_aggregate, project_out, rate, session_out, student_stats, user_out
from ..timeutil import local_now
from .announcements import _out as ann_out
from .announcements import visible_to_student

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _sessions(db: Session, *where):
    q = (select(TrainingSession).options(joinedload(TrainingSession.training_class).joinedload(TrainingClass.program),
                                         joinedload(TrainingSession.instructor))
         .order_by(TrainingSession.date, TrainingSession.start_time))
    for w in where:
        q = q.where(w)
    return db.scalars(q).unique().all()


@router.get("/student")
def student_dashboard(db: Session = Depends(get_db), st: Student = Depends(current_student),
                      me: User = Depends(require_roles("student"))):
    today = local_now().date()
    mine = {r.session_id: r for r in db.scalars(select(AttendanceRecord).where(AttendanceRecord.student_id == st.id))}
    enrolled = select(ClassEnrollment.class_id).where(ClassEnrollment.student_id == st.id)
    todays = _sessions(db, TrainingSession.date == today, TrainingSession.training_class_id.in_(enrolled))
    upcoming = _sessions(db, TrainingSession.date > today, TrainingSession.training_class_id.in_(enrolled))[:3]
    recent = db.execute(select(AttendanceRecord, TrainingSession).join(TrainingSession, TrainingSession.id == AttendanceRecord.session_id)
                        .where(AttendanceRecord.student_id == st.id).order_by(TrainingSession.date.desc()).limit(5))
    proj = db.scalars(select(Project).where(Project.id.in_(select(ProjectMember.project_id).where(ProjectMember.student_id == st.id)),
                                            Project.status != "Completed").order_by(Project.created_at.desc())
                      .options(joinedload(Project.milestones), joinedload(Project.members).joinedload(ProjectMember.student).joinedload(Student.user),
                               joinedload(Project.supervisors))).unique().first()
    nxt = next((m for m in (proj.milestones if proj else []) if m.status != "Completed"), None)
    return {
        "user": user_out(me),
        "today": [session_out(s, mine[s.id].status if s.id in mine else None, mine[s.id].marked_at if s.id in mine else None) for s in todays],
        "upcoming": [session_out(s) for s in upcoming],
        "attendance": student_stats(db, [st.id])[st.id],
        "recent_attendance": [{"date": s.date.isoformat(), "session": s.title, "status": r.status,
                               "checked_in_at": r.marked_at.isoformat() + "Z"} for r, s in recent],
        "active_project": project_out(proj, detail=False) if proj else None,
        "next_milestone": {"title": nxt.title, "due_date": nxt.due_date.isoformat() if nxt.due_date else None} if nxt else None,
        "announcements": [ann_out(a) for a in visible_to_student(db, me, limit=3)],
    }


@router.get("/instructor")
def instructor_dashboard(db: Session = Depends(get_db), me: User = Depends(require_roles("instructor"))):
    today = local_now().date()
    mine = TrainingSession.instructor_id == me.id
    classes = db.scalars(select(TrainingClass).where(TrainingClass.instructor_id == me.id)).all()
    return {
        "today": [session_out(s) for s in _sessions(db, mine, TrainingSession.date == today)],
        "upcoming": [session_out(s) for s in _sessions(db, mine, TrainingSession.date > today)[:5]],
        "class_count": len(classes),
        "attendance": attendance_aggregate(db, instructor_id=me.id),
    }


@router.get("/supervisor")
def supervisor_dashboard(db: Session = Depends(get_db), me: User = Depends(require_roles("supervisor"))):
    pids = select(ProjectSupervisor.project_id).where(ProjectSupervisor.user_id == me.id)
    projects = db.scalars(select(Project).where(Project.id.in_(pids)).options(
        joinedload(Project.members).joinedload(ProjectMember.student).joinedload(Student.user),
        joinedload(Project.supervisors).joinedload(ProjectSupervisor.user))).unique().all()
    pending = db.scalar(select(func.count()).select_from(ProjectSubmission).where(
        ProjectSubmission.project_id.in_(pids), ProjectSubmission.review_status == "Pending"))
    return {"projects": [project_out(p, detail=False) for p in projects], "pending_reviews": pending,
            "student_count": len({m.student_id for p in projects for m in p.members})}


@router.get("/admin")
def admin_dashboard(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    today = local_now().date()
    agg = attendance_aggregate(db)
    todays = _sessions(db, TrainingSession.date == today)
    tc = {"Present": 0, "Late": 0, "Absent": 0, "Excused": 0}
    if todays:
        for st, n in db.execute(select(AttendanceRecord.status, func.count()).where(
                AttendanceRecord.session_id.in_([s.id for s in todays])).group_by(AttendanceRecord.status)):
            tc[st] = n
    recent = db.execute(select(AttendanceRecord, TrainingSession, User.full_name)
                        .join(TrainingSession, TrainingSession.id == AttendanceRecord.session_id)
                        .join(Student, Student.id == AttendanceRecord.student_id).join(User, User.id == Student.user_id)
                        .order_by(AttendanceRecord.marked_at.desc()).limit(8))
    active = db.scalars(select(Project).where(Project.status != "Completed").order_by(Project.deadline).limit(6)
                        .options(joinedload(Project.members).joinedload(ProjectMember.student).joinedload(Student.user),
                                 joinedload(Project.supervisors).joinedload(ProjectSupervisor.user))).unique().all()
    return {
        "total_interns": db.scalar(select(func.count()).select_from(Student)) or 0,
        "today_sessions": [session_out(s) for s in todays],
        "today": {"present": tc["Present"], "late": tc["Late"], "absent": tc["Absent"]},
        "overall_rate": agg["overall"]["rate"],
        "active_projects": db.scalar(select(func.count()).select_from(Project).where(Project.status != "Completed")) or 0,
        "trend": agg["trend"], "by_department": agg["by_department"], "low_attendance": agg["low_attendance"],
        "recent_activity": [{"student": n, "session": s.title, "status": r.status, "method": r.method,
                             "at": r.marked_at.isoformat() + "Z"} for r, s, n in recent],
        "projects": [project_out(p, detail=False) for p in active],
        "upcoming": [session_out(s) for s in _sessions(db, TrainingSession.date > today)[:5]],
    }
