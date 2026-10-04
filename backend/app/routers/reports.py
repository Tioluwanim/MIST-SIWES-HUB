import csv
import io

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..deps import require_roles
from ..models import Project, ProjectMember, ProjectSupervisor, Student, User
from ..services import student_stats

router = APIRouter(prefix="/api/reports", tags=["reports"])
admin = require_roles("admin")


def _csv(rows: list[dict], filename: str) -> Response:
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            # neutralise spreadsheet formula injection
            w.writerow({k: ("'" + v if isinstance(v, str) and v[:1] in "=+-@" else v) for k, v in r.items()})
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/attendance")
def attendance_report(batch_id: int | None = None, department_id: int | None = None, format: str = "json",
                      db: Session = Depends(get_db), _: User = Depends(admin)):
    q = select(Student).join(User, User.id == Student.user_id).options(
        joinedload(Student.user).joinedload(User.department), joinedload(Student.user).joinedload(User.unit),
        joinedload(Student.batch)).order_by(User.full_name)
    if batch_id:
        q = q.where(Student.batch_id == batch_id)
    if department_id:
        q = q.where(User.department_id == department_id)
    studs = db.scalars(q).unique().all()
    stats = student_stats(db, [s.id for s in studs])
    rows = [{"Student": s.user.full_name, "Email": s.user.email, "Matric No": s.matric_no or "",
             "Batch": s.batch.name if s.batch else "", "Department": s.user.department.name if s.user.department else "",
             "Unit": s.user.unit.name if s.user.unit else "", "Sessions": stats[s.id]["total"],
             "Present": stats[s.id]["present"], "Late": stats[s.id]["late"], "Absent": stats[s.id]["absent"],
             "Excused": stats[s.id]["excused"], "Attendance Rate (%)": stats[s.id]["rate"]} for s in studs]
    return _csv(rows, "attendance-report.csv") if format == "csv" else rows


@router.get("/projects")
def project_report(format: str = "json", db: Session = Depends(get_db), _: User = Depends(admin)):
    q = select(Project).options(joinedload(Project.members).joinedload(ProjectMember.student).joinedload(Student.user),
                                joinedload(Project.supervisors).joinedload(ProjectSupervisor.user)).order_by(Project.title)
    rows = [{"Project": p.title, "Students": "; ".join(m.student.user.full_name for m in p.members),
             "Supervisors": "; ".join(s.user.full_name for s in p.supervisors), "Progress (%)": p.progress,
             "Status": p.status, "Deadline": p.deadline.isoformat() if p.deadline else ""}
            for p in db.scalars(q).unique()]
    return _csv(rows, "project-report.csv") if format == "csv" else rows
