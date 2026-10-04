from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (Project, ProjectMember, ProjectMilestone, ProjectSubmission, ProjectSupervisor, SiwesBatch,
                      Student, User)
from ..schemas import (AssignIn, MilestoneIn, MilestoneUpdate, ProjectIn, ProjectUpdate, ReviewIn, SubmissionIn)
from ..services import (milestone_out, project_out, recompute_project, set_milestone_status, submission_out)
from ..storage import validate_url
from ..timeutil import utcnow

router = APIRouter(prefix="/api/projects", tags=["projects"])
milestones_router = APIRouter(prefix="/api/milestones", tags=["milestones"])
submissions_router = APIRouter(prefix="/api/submissions", tags=["submissions"])
admin = require_roles("admin")
_opts = (joinedload(Project.members).joinedload(ProjectMember.student).joinedload(Student.user),
         joinedload(Project.supervisors).joinedload(ProjectSupervisor.user), joinedload(Project.milestones))


def _student_of(db: Session, user: User) -> Student | None:
    return db.scalar(select(Student).where(Student.user_id == user.id))


def _load(db: Session, pid: int) -> Project:
    p = db.scalars(select(Project).where(Project.id == pid).options(*_opts)).unique().first()
    if not p:
        raise HTTPException(404, "Project not found")
    return p


def _can_view(db: Session, user: User, p: Project) -> bool:
    if user.role == "admin":
        return True
    if user.role == "supervisor":
        return any(s.user_id == user.id for s in p.supervisors)
    st = _student_of(db, user)
    return bool(st and any(m.student_id == st.id for m in p.members))


def _can_manage(user: User, p: Project) -> bool:
    return user.role == "admin" or (user.role == "supervisor" and any(s.user_id == user.id for s in p.supervisors))


def _add_people(db: Session, p: Project, student_ids: list[int], supervisor_ids: list[int]):
    have_s = {m.student_id for m in p.members}
    have_u = {s.user_id for s in p.supervisors}
    for sid in set(student_ids) - have_s:
        if not db.get(Student, sid):
            raise HTTPException(404, f"Student {sid} not found")
        p.members.append(ProjectMember(student_id=sid))
    for uid in set(supervisor_ids) - have_u:
        u = db.get(User, uid)
        if not u or u.role != "supervisor":
            raise HTTPException(422, f"User {uid} is not a supervisor")
        p.supervisors.append(ProjectSupervisor(user_id=uid))


@router.get("")
def list_projects(status: str | None = None, db: Session = Depends(get_db),
                  me: User = Depends(require_roles("student", "supervisor", "admin"))):
    q = select(Project).options(*_opts).order_by(Project.created_at.desc())
    if status:
        q = q.where(Project.status == status)
    if me.role == "supervisor":
        q = q.where(Project.id.in_(select(ProjectSupervisor.project_id).where(ProjectSupervisor.user_id == me.id)))
    elif me.role == "student":
        st = _student_of(db, me)
        q = q.where(Project.id.in_(select(ProjectMember.project_id).where(ProjectMember.student_id == (st.id if st else 0))))
    return [project_out(p, detail=False) for p in db.scalars(q).unique()]


@router.post("", status_code=201)
def create_project(body: ProjectIn, db: Session = Depends(get_db), _: User = Depends(admin)):
    if body.batch_id and not db.get(SiwesBatch, body.batch_id):
        raise HTTPException(404, "Batch not found")
    if body.start_date and body.deadline and body.deadline < body.start_date:
        raise HTTPException(422, "Deadline cannot be before the start date")
    p = Project(title=body.title, description=body.description, batch_id=body.batch_id,
                start_date=body.start_date, deadline=body.deadline)
    for i, m in enumerate(body.milestones):
        p.milestones.append(ProjectMilestone(position=i, **m.model_dump()))
    _add_people(db, p, body.member_ids, body.supervisor_ids)
    db.add(p)
    recompute_project(p)
    db.commit()
    return project_out(_load(db, p.id))


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    p = _load(db, project_id)
    if not _can_view(db, me, p):
        raise HTTPException(403, "You are not part of this project")
    return project_out(p)


@router.patch("/{project_id}")
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db),
                   me: User = Depends(require_roles("admin", "supervisor"))):
    p = _load(db, project_id)
    if not _can_manage(me, p):
        raise HTTPException(403, "You are not a supervisor of this project")
    data = body.model_dump(exclude_unset=True)
    if me.role != "admin":  # supervisors may only move the status
        data = {k: v for k, v in data.items() if k == "status"}
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    return project_out(p)


@router.post("/{project_id}/assign")
def assign(project_id: int, body: AssignIn, db: Session = Depends(get_db), _: User = Depends(admin)):
    p = _load(db, project_id)
    _add_people(db, p, body.student_ids, body.supervisor_ids)
    db.commit()
    return project_out(_load(db, project_id))


@router.delete("/{project_id}/members/{student_id}", status_code=204)
def remove_member(project_id: int, student_id: int, db: Session = Depends(get_db), _: User = Depends(admin)):
    m = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.student_id == student_id))
    if not m:
        raise HTTPException(404, "Member not found")
    db.delete(m)
    db.commit()


@router.post("/{project_id}/milestones", status_code=201)
def add_milestone(project_id: int, body: MilestoneIn, db: Session = Depends(get_db),
                  me: User = Depends(require_roles("admin", "supervisor"))):
    p = _load(db, project_id)
    if not _can_manage(me, p):
        raise HTTPException(403, "You are not a supervisor of this project")
    m = ProjectMilestone(project_id=p.id, position=len(p.milestones), **body.model_dump())
    set_milestone_status(m, body.status)
    p.milestones.append(m)
    db.flush()
    recompute_project(p)
    db.commit()
    return milestone_out(m)


@milestones_router.patch("/{milestone_id}")
def update_milestone(milestone_id: int, body: MilestoneUpdate, db: Session = Depends(get_db),
                     me: User = Depends(require_roles("admin", "supervisor"))):
    m = db.get(ProjectMilestone, milestone_id)
    if not m:
        raise HTTPException(404, "Milestone not found")
    p = _load(db, m.project_id)
    if not _can_manage(me, p):
        raise HTTPException(403, "You are not a supervisor of this project")
    data = body.model_dump(exclude_unset=True)
    status = data.pop("status", None)
    for k, v in data.items():
        setattr(m, k, v)
    if status:
        set_milestone_status(m, status)
    db.flush()
    recompute_project(p)
    db.commit()
    return {"milestone": milestone_out(m), "project_progress": p.progress, "project_status": p.status}


# ---------------- submissions ----------------
@submissions_router.get("")
def list_submissions(project_id: int | None = None, review_status: str | None = None, db: Session = Depends(get_db),
                     me: User = Depends(require_roles("student", "supervisor", "admin"))):
    q = (select(ProjectSubmission).options(joinedload(ProjectSubmission.student).joinedload(Student.user),
                                           joinedload(ProjectSubmission.project))
         .order_by(ProjectSubmission.created_at.desc(), ProjectSubmission.id.desc()))
    if project_id:
        q = q.where(ProjectSubmission.project_id == project_id)
    if review_status:
        q = q.where(ProjectSubmission.review_status == review_status)
    if me.role == "supervisor":
        q = q.where(ProjectSubmission.project_id.in_(select(ProjectSupervisor.project_id).where(ProjectSupervisor.user_id == me.id)))
    elif me.role == "student":
        st = _student_of(db, me)
        q = q.where(ProjectSubmission.project_id.in_(select(ProjectMember.project_id).where(ProjectMember.student_id == (st.id if st else 0))))
    return [submission_out(s) for s in db.scalars(q).unique()]


@submissions_router.post("", status_code=201)
def create_submission(body: SubmissionIn, db: Session = Depends(get_db), me: User = Depends(require_roles("student"))):
    p = _load(db, body.project_id)
    st = _student_of(db, me)
    if not st or not any(m.student_id == st.id for m in p.members):
        raise HTTPException(403, "You are not a member of this project")
    if body.milestone_id and not any(m.id == body.milestone_id for m in p.milestones):
        raise HTTPException(422, "Milestone does not belong to this project")
    for a in body.attachments:
        if not a.url.startswith("/api/files/"):
            validate_url(a.url)
    sub = ProjectSubmission(project_id=p.id, milestone_id=body.milestone_id, student_id=st.id, title=body.title,
                            worked_on=body.worked_on, challenges=body.challenges, next_steps=body.next_steps,
                            repo_url=validate_url(body.repo_url), project_url=validate_url(body.project_url),
                            attachments=[a.model_dump() for a in body.attachments])
    db.add(sub)
    db.commit()
    return submission_out(sub)


@submissions_router.patch("/{submission_id}/review")
def review_submission(submission_id: int, body: ReviewIn, db: Session = Depends(get_db),
                      me: User = Depends(require_roles("admin", "supervisor"))):
    sub = db.get(ProjectSubmission, submission_id)
    if not sub:
        raise HTTPException(404, "Submission not found")
    p = _load(db, sub.project_id)
    if not _can_manage(me, p):
        raise HTTPException(403, "You are not a supervisor of this project")
    sub.review_status, sub.feedback, sub.reviewed_by, sub.reviewed_at = body.review_status, body.feedback, me.id, utcnow()
    if body.mark_milestone_complete and sub.milestone_id:
        m = next((m for m in p.milestones if m.id == sub.milestone_id), None)
        if m:
            set_milestone_status(m, "Completed")
    elif body.review_status == "Approved" and sub.milestone_id:
        m = next((m for m in p.milestones if m.id == sub.milestone_id), None)
        if m and m.status == "Not Started":
            set_milestone_status(m, "In Progress")
    db.flush()
    recompute_project(p)
    db.commit()
    return {**submission_out(sub), "project_progress": p.progress, "project_status": p.status}
