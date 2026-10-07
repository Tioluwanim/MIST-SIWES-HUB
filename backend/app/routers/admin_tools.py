"""Admin-only data lifecycle, import and audit endpoints."""
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import require_roles
from ..importer import import_sheets, parse_import, template_bytes
from ..models import (Announcement, AttendanceRecord, AttendanceSession, AuditLog, ClassEnrollment,
                      Department, Project, ProjectMember, ProjectMilestone, ProjectSubmission,
                      ProjectSupervisor, SiwesBatch, Student, TrainingClass, TrainingMaterial,
                      TrainingProgram, TrainingSession, Unit, User)
from ..schemas import AuditLogOut

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin = require_roles("admin")


def record(db, actor, action, target_type, target_id=None, details=None):
    db.add(AuditLog(admin_user_id=actor.id if actor else None, action=action,
                    target_type=target_type, target_id=str(target_id) if target_id is not None else None,
                    details=details or {}))


def _destructive_allowed():
    if not get_settings().allow_destructive_admin:
        raise HTTPException(403, "Destructive admin operations are disabled; set ALLOW_DESTRUCTIVE_ADMIN=true")


@router.get("/audit", response_model=list[AuditLogOut])
def audit(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), _: User = Depends(admin)):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)).all()


@router.post("/seed")
def seed(body: dict | None = None, db: Session = Depends(get_db), me: User = Depends(admin)):
    from ..seed import run_seed
    body = body or {}
    counts = run_seed(db, include_demo=body.get("include_demo", True),
                      staff_emails={k: body[k] for k in ("instructor_email", "supervisor_email") if body.get(k)})
    record(db, me, "seed", "demo", details=counts)
    db.commit()
    return counts


@router.delete("/demo-data")
def delete_demo_data(db: Session = Depends(get_db), me: User = Depends(admin)):
    _destructive_allowed()
    deleted = 0
    for model in (AttendanceRecord, AttendanceSession, ProjectSubmission, ProjectMilestone, ProjectMember,
                  ProjectSupervisor, Project, TrainingSession, TrainingMaterial, ClassEnrollment,
                  TrainingClass, TrainingProgram, Student, User, Unit, Department, SiwesBatch, Announcement):
        if hasattr(model, "is_demo"):
            stmt = delete(model).where(model.is_demo.is_(True))
            if model is User: stmt = stmt.where(User.id != me.id)
            deleted += db.execute(stmt).rowcount or 0
    record(db, me, "delete_demo_data", "demo", details={"deleted": deleted})
    db.commit()
    return {"deleted": deleted}


@router.post("/reset")
def reset(body: dict, db: Session = Depends(get_db), me: User = Depends(admin)):
    _destructive_allowed()
    if body.get("confirm") != "RESET":
        raise HTTPException(422, 'Confirmation must be exactly "RESET"')
    scopes = {
        "attendance": (AttendanceRecord, AttendanceSession),
        "projects": (ProjectSubmission, ProjectMilestone, ProjectMember, ProjectSupervisor, Project),
        "announcements": (Announcement,),
        "training": (AttendanceRecord, AttendanceSession, TrainingSession, TrainingMaterial, ClassEnrollment, TrainingClass, TrainingProgram),
        "students": (Student, User),
        "all_except_admins": (AttendanceRecord, AttendanceSession, ProjectSubmission, ProjectMilestone, ProjectMember, ProjectSupervisor,
                              Project, Announcement, TrainingSession, TrainingMaterial, ClassEnrollment, TrainingClass, TrainingProgram,
                              Student, User, Unit, Department, SiwesBatch),
    }
    if body.get("scope") not in scopes: raise HTTPException(422, "Unknown reset scope")
    deleted = 0
    for model in scopes[body["scope"]]:
        stmt = delete(model)
        if model is User: stmt = stmt.where(User.role != "admin", User.id != me.id)
        deleted += db.execute(stmt).rowcount or 0
    record(db, me, "reset", body["scope"], details={"deleted": deleted})
    db.commit()
    return {"scope": body["scope"], "deleted": deleted}


@router.get("/import/template")
def import_template(_: User = Depends(admin)):
    return StreamingResponse(BytesIO(template_bytes()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": 'attachment; filename="siwes-import-template.xlsx"'})


@router.post("/import")
async def import_data(file: UploadFile = File(...), dry_run: bool = False, skip_invalid: bool = False,
                      type: str | None = None, db: Session = Depends(get_db), me: User = Depends(admin)):
    try:
        sheets = parse_import(await file.read(), file.filename or "", type)
        result = import_sheets(db, sheets, dry_run=dry_run, skip_invalid=skip_invalid, actor=me)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    total_errors = sum(len(s["errors"]) for s in result)
    if total_errors > 200:
        remaining = 200
        for summary in result:
            summary["errors"] = summary["errors"][:remaining]
            remaining -= len(summary["errors"])
            if remaining <= 0:
                for later in result[result.index(summary) + 1:]:
                    later["errors"] = []
                break
    if total_errors and not dry_run and not skip_invalid:
        db.rollback()
        raise HTTPException(422, detail={"message": "Import contains invalid rows", "sheets": result, "total_errors": total_errors})
    if not dry_run:
        record(db, me, "import", "workbook", details={"filename": file.filename, "total_errors": total_errors, "sheets": result})
        db.commit()
    return {"sheets": result, "total_errors": total_errors, "dry_run": dry_run}


_DELETE_MODELS = {
    "users": User, "batches": SiwesBatch, "departments": Department, "units": Unit,
    "programs": TrainingProgram, "classes": TrainingClass, "sessions": TrainingSession,
    "projects": Project, "milestones": ProjectMilestone, "announcements": Announcement,
}


@router.delete("/{target_type}/{target_id}")
def delete_record(target_type: str, target_id: int, force: bool = False, hard: bool = False,
                  db: Session = Depends(get_db), me: User = Depends(admin)):
    _destructive_allowed()
    model = _DELETE_MODELS.get(target_type)
    if not model: raise HTTPException(404, "Unknown target type")
    obj = db.get(model, target_id)
    if not obj: raise HTTPException(404, f"{target_type.rstrip('s').capitalize()} not found")
    if model is User:
        if obj.id == me.id: raise HTTPException(400, "You cannot delete your own account")
        if obj.role == "admin" and db.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))) <= 1:
            raise HTTPException(409, "You cannot delete or deactivate the last active admin")
        if not hard:
            obj.is_active = False
        else:
            db.delete(obj)
    else:
        if not force and target_type in {"batches", "departments", "units", "programs", "classes"}:
            dependent = _dependent_count(db, target_type, obj)
            if dependent: raise HTTPException(409, detail=f"{target_type.rstrip('s').capitalize()} has {dependent} dependent records")
        db.delete(obj)
    record(db, me, "delete", target_type, target_id, {"hard": hard, "force": force})
    db.commit()
    return {"ok": True, "deactivated": model is User and not hard}


def _dependent_count(db, target_type, obj):
    if target_type == "batches": return db.scalar(select(func.count(Student.id)).where(Student.batch_id == obj.id)) + db.scalar(select(func.count(TrainingProgram.id)).where(TrainingProgram.batch_id == obj.id))
    if target_type == "departments": return db.scalar(select(func.count(User.id)).where(User.department_id == obj.id)) + db.scalar(select(func.count(Unit.id)).where(Unit.department_id == obj.id))
    if target_type == "units": return db.scalar(select(func.count(User.id)).where(User.unit_id == obj.id))
    if target_type == "programs": return db.scalar(select(func.count(TrainingClass.id)).where(TrainingClass.program_id == obj.id))
    if target_type == "classes": return db.scalar(select(func.count(TrainingSession.id)).where(TrainingSession.training_class_id == obj.id))
    return 0
