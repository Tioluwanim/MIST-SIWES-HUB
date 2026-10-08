"""Admin-only data lifecycle, import and audit endpoints."""
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import require_roles
from ..importer import import_sheets, parse_import, template_bytes
from ..models import (Announcement, AttendanceRecord, AttendanceSession, AuditLog, ClassEnrollment, Department,
                      Project, ProjectMember, ProjectMilestone, ProjectSubmission, ProjectSupervisor, SiwesBatch,
                      Student, TrainingClass, TrainingMaterial, TrainingProgram, TrainingSession, Unit, User)
from ..schemas import AuditLogOut
from ..services import recompute_project

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin = require_roles("admin")


def record(db, actor, action, target_type, target_id=None, details=None):
    db.add(AuditLog(admin_user_id=actor.id if actor else None, action=action,
                    target_type=target_type, target_id=str(target_id) if target_id is not None else None,
                    details=details or {}))


def _destructive_allowed():
    if not get_settings().allow_destructive_admin:
        raise HTTPException(403, "Destructive admin operations are disabled. Set ALLOW_DESTRUCTIVE_ADMIN=true on the "
                                 "server to enable deleting and resetting data.")


class SeedIn(BaseModel):
    include_demo: bool = True
    instructor_email: EmailStr | None = None
    supervisor_email: EmailStr | None = None


class ResetIn(BaseModel):
    scope: Literal["attendance", "projects", "announcements", "training", "students", "all_except_admins"]
    confirm: str


@router.get("/status")
def status(db: Session = Depends(get_db), _: User = Depends(admin)):
    """Lets the UI explain what is switched on and what is currently demo data."""
    demo = sum(db.scalar(select(func.count()).select_from(m).where(m.is_demo.is_(True))) or 0
               for m in (User, Department, SiwesBatch, Project, Announcement))
    return {"destructive_enabled": get_settings().allow_destructive_admin, "demo_rows": demo,
            "totals": {"students": db.scalar(select(func.count(Student.id))) or 0,
                       "users": db.scalar(select(func.count(User.id))) or 0}}


@router.get("/audit", response_model=list[AuditLogOut])
def audit(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), _: User = Depends(admin)):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)).all()


@router.post("/seed")
def seed(body: SeedIn | None = None, db: Session = Depends(get_db), me: User = Depends(admin)):
    from ..seed import run_seed
    body = body or SeedIn()
    staff = {k: str(v) for k, v in (("instructor_email", body.instructor_email),
                                    ("supervisor_email", body.supervisor_email)) if v}
    counts = run_seed(db, include_demo=body.include_demo, staff_emails=staff)
    record(db, me, "seed", "demo", details=counts)
    db.commit()
    return counts


@router.delete("/demo-data")
def delete_demo_data(db: Session = Depends(get_db), me: User = Depends(admin)):
    """Removes ONLY rows flagged is_demo (never admins, never you). Imported and hand-made data is untouched."""
    _destructive_allowed()
    from ..seed import delete_demo_rows
    try:
        deleted = delete_demo_rows(db, keep_user_ids={me.id})
        record(db, me, "delete_demo_data", "demo", details={"deleted": deleted})
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(409, f"Could not remove demo data: {exc.__class__.__name__}") from exc
    return {"deleted": deleted}


@router.post("/reset")
def reset(body: ResetIn, db: Session = Depends(get_db), me: User = Depends(admin)):
    _destructive_allowed()
    if body.confirm != "RESET":
        raise HTTPException(422, 'Confirmation must be exactly "RESET"')
    not_admin = (User.role != "admin", User.id != me.id)
    training = [AttendanceRecord, AttendanceSession, TrainingSession, TrainingMaterial, ClassEnrollment,
                TrainingClass, TrainingProgram]
    projects = [ProjectSubmission, ProjectMilestone, ProjectMember, ProjectSupervisor, Project]
    scopes: dict[str, list] = {
        "attendance": [AttendanceRecord, AttendanceSession],
        "projects": projects,
        "announcements": [Announcement],
        "training": training,
        # a student is a User with a Student profile: remove both so nobody is left without a profile
        "students": [Student, (User, (User.role == "student", User.id != me.id))],
        "all_except_admins": training + projects + [Announcement, Student, (User, not_admin), Unit, Department, SiwesBatch],
    }
    deleted = 0
    try:
        for item in scopes[body.scope]:
            model, where = item if isinstance(item, tuple) else (item, ())
            deleted += db.execute(delete(model).where(*where)).rowcount or 0
        record(db, me, "reset", body.scope, details={"deleted": deleted})
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(409, f"Reset failed and nothing was changed: {exc.__class__.__name__}") from exc
    return {"scope": body.scope, "deleted": deleted}


@router.get("/import/template")
def import_template(_: User = Depends(admin)):
    return StreamingResponse(BytesIO(template_bytes()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": 'attachment; filename="siwes-import-template.xlsx"'})


@router.post("/import")
async def import_data(file: UploadFile = File(...), dry_run: bool = False, skip_invalid: bool = False,
                      type: str | None = None, db: Session = Depends(get_db), me: User = Depends(admin)):
    limit = get_settings().max_import_mb * 1024 * 1024
    raw = await file.read(limit + 1)  # never buffer more than the limit
    try:
        if len(raw) > limit:
            raise ValueError(f"file exceeds the {get_settings().max_import_mb} MB limit")
        sheets = parse_import(raw, file.filename or "", type)
        result = import_sheets(db, sheets, dry_run=dry_run, skip_invalid=skip_invalid, actor=me)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    total_errors = sum(len(s["errors"]) for s in result)
    summary = [{"sheet": s["sheet"], "created": s["created"], "updated": s["updated"], "skipped": s["skipped"],
                "error_count": len(s["errors"])} for s in result]
    remaining = 200  # keep responses small
    for s in result:
        s["errors"] = s["errors"][:remaining]
        remaining -= len(s["errors"])
    if total_errors and not dry_run and not skip_invalid:
        db.rollback()
        raise HTTPException(422, detail={"message": "Import contains invalid rows. Nothing was imported.",
                                         "sheets": result, "total_errors": total_errors})
    if not dry_run:
        record(db, me, "import", "workbook", details={"filename": file.filename, "total_errors": total_errors, "sheets": summary})
        db.commit()
    return {"sheets": result, "total_errors": total_errors, "dry_run": dry_run}


_DELETE_MODELS = {
    "batches": SiwesBatch, "departments": Department, "units": Unit, "programs": TrainingProgram,
    "classes": TrainingClass, "sessions": TrainingSession, "projects": Project, "milestones": ProjectMilestone,
    "announcements": Announcement,
}


def _count(db, stmt) -> int:
    return db.scalar(stmt) or 0


def _dependents(db, kind: str, obj) -> dict[str, int]:
    """What would be affected if this record disappeared (only non-zero entries)."""
    c = lambda col, model: _count(db, select(func.count(model.id)).where(col == obj.id))  # noqa: E731
    found = {
        "batches": {"students": c(Student.batch_id, Student), "programs": c(TrainingProgram.batch_id, TrainingProgram),
                    "projects": c(Project.batch_id, Project)},
        "departments": {"people": c(User.department_id, User), "units": c(Unit.department_id, Unit)},
        "units": {"people": c(User.unit_id, User)},
        "programs": {"classes": c(TrainingClass.program_id, TrainingClass)},
        "classes": {"sessions": c(TrainingSession.training_class_id, TrainingSession),
                    "enrolled students": c(ClassEnrollment.class_id, ClassEnrollment)},
        "sessions": {"attendance records": c(AttendanceRecord.session_id, AttendanceRecord)},
        "projects": {"progress updates": c(ProjectSubmission.project_id, ProjectSubmission),
                     "team members": c(ProjectMember.project_id, ProjectMember)},
    }.get(kind, {})
    return {k: v for k, v in found.items() if v}


@router.delete("/{target_type}/{target_id}")
def delete_record(target_type: str, target_id: int, force: bool = False,
                  db: Session = Depends(get_db), me: User = Depends(admin)):
    """People are removed through DELETE /api/users/{id}; everything else lives here."""
    _destructive_allowed()
    model = _DELETE_MODELS.get(target_type)
    if not model:
        raise HTTPException(404, "Unknown target type")
    label = target_type[:-3] + "y" if target_type.endswith("ies") else target_type.rstrip("s")
    obj = db.get(model, target_id)
    if not obj:
        raise HTTPException(404, f"{label.capitalize()} not found")
    deps = _dependents(db, target_type, obj)
    if deps and not force:
        parts = [f"{n} {name}" for name, n in deps.items()]
        raise HTTPException(409, detail=f"This {label} has " + (", ".join(parts[:-1]) + " and " if len(parts) > 1 else "") + parts[-1]
                                        + ". Deleting it removes or detaches them.")
    project_id = obj.project_id if model is ProjectMilestone else None
    try:
        db.delete(obj)
        db.flush()
        if project_id:
            project = db.get(Project, project_id)
            db.refresh(project)
            recompute_project(project)
        record(db, me, "delete", target_type, target_id, {"force": force, "dependents": deps})
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(409, f"Could not delete: {exc.__class__.__name__}") from exc
    return {"ok": True}
