"""Development seed data: `python -m app.seed` (add --reset to wipe first)."""
import random
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, event, select

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import *  # noqa
from .services import enroll_batch_in_class, recompute_project, set_milestone_status
from .timeutil import local_now

# Approximate coordinates of the Lagos State Secretariat, Alausa, Ikeja (configurable per session in the UI)
VENUE = ("MIST Training Hall, Alausa Secretariat, Ikeja", 6.6186, 3.3569)

STUDENTS = ["Adaeze Okafor", "Tunde Bakare", "Chiamaka Eze", "Ibrahim Lawal", "Folake Adeyemi", "Emeka Nwosu",
            "Zainab Sanni", "Seyi Ogunleye", "Blessing Udoh", "Kunle Adebayo", "Hauwa Musa", "David Olatunji"]

def delete_demo_rows(db, keep_user_ids=()) -> int:
    """Delete ONLY rows flagged is_demo, children first. Admins and `keep_user_ids` are never removed."""
    deleted = 0
    for model in (AttendanceRecord, AttendanceSession, ProjectSubmission, ProjectMilestone, ProjectMember,
                  ProjectSupervisor, Project, TrainingSession, TrainingMaterial, ClassEnrollment, TrainingClass,
                  TrainingProgram, Student, User, Unit, Department, SiwesBatch, Announcement):
        if not hasattr(model, "is_demo"):
            continue  # join/attendance rows have no flag: they go with their demo parents (ON DELETE CASCADE)
        stmt = delete(model).where(model.is_demo.is_(True))
        if model is User:
            stmt = stmt.where(User.role != "admin", User.id.notin_(list(keep_user_ids) or [0]))
        deleted += db.execute(stmt).rowcount or 0
    return deleted


def run_seed(db=None, *, include_demo: bool = True, staff_emails: dict | None = None, reset: bool = False):
    """Create demo data (idempotent). Everything created here, and nothing else, is flagged is_demo."""
    if not include_demo:
        return {"created": 0, "updated": 0, "skipped": 0, "tables": {}, "warnings": []}
    s = get_settings()
    staff_emails = staff_emails or {}
    if reset:
        with SessionLocal.begin() as reset_db:
            delete_demo_rows(reset_db)
    Base.metadata.create_all(engine)  # no-op when Alembic already created the tables
    owns_session = db is None
    db = db or SessionLocal()
    warnings: list[str] = []
    created: list = []

    def _track(session, _ctx, _instances):
        created.extend(session.new)

    event.listen(db, "before_flush", _track)
    try:
        return _seed(db, s, staff_emails, owns_session, created, warnings)
    except Exception:
        if owns_session:
            db.rollback()
        raise
    finally:
        event.remove(db, "before_flush", _track)
        if owns_session:
            db.close()


def _seed(db, s, staff_emails, owns_session, created, warnings):
    if db.scalar(select(Department.id).where(Department.is_demo.is_(True)).limit(1)):
        return {"created": 0, "updated": 0, "skipped": 1, "tables": {}, "warnings": ["Demo data already exists"]}
    random.seed(7)
    sw = Department(name="Software & Digital Services")
    hw = Department(name="Hardware & Embedded Systems")
    db.add_all([sw, hw])
    db.flush()
    units = {n: Unit(department_id=d.id, name=n) for n, d in
             [("Software Development", sw), ("Data & Analytics", sw), ("Embedded Systems", hw)]}
    db.add_all(units.values())
    batch = SiwesBatch(name="2026 SIWES Batch", year=2026, start_date=date(2026, 8, 3), end_date=date(2027, 1, 29))
    db.add_all([batch, SiwesBatch(name="2027 SIWES Batch", year=2027, is_active=False)])
    db.flush()

    admin_email = staff_emails.get("admin_email") or (s.seed_admin_email if "@" in s.seed_admin_email and not s.seed_admin_email.endswith("@example.com") else None)

    def staff_user(email, role, name, **kw):
        if not email:
            return None
        email = email.strip().lower()
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            if existing.role == role:
                return existing  # reuse the real account; it is not demo data and is never flagged
            warnings.append(f"{email} already exists as {existing.role}; skipped creating the demo {role}")
            return None
        user = User(email=email, full_name=name, role=role, **kw)
        db.add(user)
        return user

    admin = staff_user(admin_email, "admin", "Folasade Williams")
    instr = staff_user(staff_emails.get("instructor_email"), "instructor", "Engr. Kayode Balogun",
                       department_id=sw.id, unit_id=units["Software Development"].id)
    sup = staff_user(staff_emails.get("supervisor_email"), "supervisor", "Dr. Ngozi Adebisi", department_id=sw.id)
    db.flush()

    studs = []
    own_email = (s.seed_real_student_email or "").strip().lower()
    if own_email:
        if db.scalar(select(User.id).where(User.email == own_email)):
            warnings.append(f"{own_email} already exists; it was not added as a demo student")
        else:
            mine = User(email=own_email, full_name=s.seed_real_student_name or "Demo Student", role="student",
                        department_id=sw.id, unit_id=units["Software Development"].id)
            mine.student = Student(batch_id=batch.id)
            studs.append(mine.student)
            db.add(mine)
    for i, name in enumerate(STUDENTS):
        unit = list(units.values())[0 if i < 6 else (1 if i < 9 else 2)]
        u = User(email=f"{name.split()[0].lower()}.{name.split()[1].lower()}@students.example.com", full_name=name,
                 role="student", department_id=unit.department_id, unit_id=unit.id)
        u.student = Student(batch_id=batch.id, matric_no=f"CSC/20/{1000 + i}", institution="University of Lagos")
        studs.append(u.student)
        db.add(u)
    db.flush()

    prog = TrainingProgram(batch_id=batch.id, name="Software Development Training",
                           description="Core engineering practice for software interns.")
    db.add(prog)
    db.flush()
    backend = TrainingClass(program_id=prog.id, instructor_id=instr.id if instr else None, name="Backend Development")
    frontend = TrainingClass(program_id=prog.id, instructor_id=instr.id if instr else None, name="Frontend Engineering")
    db.add_all([backend, frontend])
    db.flush()
    for c in (backend, frontend):
        enroll_batch_in_class(db, c.id)

    today = local_now().date()
    sessions = []
    plan = [(-14, backend, "Python & HTTP Fundamentals"), (-12, frontend, "TypeScript for Teams"),
            (-9, backend, "REST API Design with FastAPI"), (-7, frontend, "React Component Patterns"),
            (-5, backend, "Relational Modelling & Migrations"), (-2, backend, "Authentication & Authorization"),
            (0, backend, "FastAPI Authentication"), (2, frontend, "Next.js App Router"), (5, backend, "Testing & CI")]
    for off, cls, title in plan:
        d = today + timedelta(days=off)
        while d.weekday() >= 5:  # keep sessions on weekdays
            d += timedelta(days=1 if off >= 0 else -1)
        ts = TrainingSession(training_class_id=cls.id, instructor_id=instr.id if instr else None, title=title, date=d,
                             start_time=time(10, 0), end_time=time(12, 0), location=VENUE[0], latitude=VENUE[1],
                             longitude=VENUE[2], allowed_radius_meters=100,
                             attendance_status="Closed" if d < today else "Not Started")
        sessions.append(ts)
    db.add_all(sessions)
    db.flush()
    for ts in sessions:
        if ts.attendance_status != "Closed":
            continue
        db.add(AttendanceSession(session_id=ts.id, is_active=False, started_by=instr.id if instr else None,
                                 started_at=datetime.combine(ts.date, time(9, 0)), ended_at=datetime.combine(ts.date, time(11, 0))))
        for i, st in enumerate(studs):
            r = random.random()
            weak = i in (3, 8)  # two students with low attendance
            status = "Present" if r > (0.45 if weak else 0.12) else ("Late" if r > (0.3 if weak else 0.05) else "Absent")
            qr = status != "Absent"
            db.add(AttendanceRecord(
                student_id=st.id, session_id=ts.id, status=status, method="QR" if qr else "Manual",
                marked_at=datetime.combine(ts.date, time(9, random.randint(0, 5) if status == "Present" else random.randint(20, 40))),
                latitude=VENUE[1] + random.uniform(-0.0003, 0.0003) if qr else None,
                longitude=VENUE[2] + random.uniform(-0.0003, 0.0003) if qr else None,
                distance_meters=round(random.uniform(5, 70), 1) if qr else None,
                remarks=None if qr else "Auto-marked absent when attendance closed", marked_by=None if qr and instr else (instr.id if instr else None)))

    proj = Project(batch_id=batch.id, title="MIST Attendance Platform",
                   description="Internal attendance and project tracking tool for the ministry's SIWES programme.",
                   start_date=today - timedelta(days=21), deadline=today + timedelta(days=45), status="In Progress")
    names = ["Requirements", "Database Design", "Backend", "Frontend", "Testing", "Deployment", "Documentation"]
    for i, n in enumerate(names):
        m = ProjectMilestone(title=n, position=i, due_date=today - timedelta(days=14) + timedelta(days=i * 9))
        set_milestone_status(m, "Completed" if i < 3 else ("In Progress" if i == 3 else "Not Started"))
        proj.milestones.append(m)
    for st in studs[:4]:
        proj.members.append(ProjectMember(student_id=st.id))
    if sup:
        proj.supervisors.append(ProjectSupervisor(user_id=sup.id))
    db.add(proj)
    db.flush()
    recompute_project(proj)
    be = proj.milestones[2]
    db.add(ProjectSubmission(
        project_id=proj.id, milestone_id=be.id, student_id=studs[1].id, title="Week 3 Progress",
        worked_on="Implemented attendance verification API.", challenges="Handled duplicate attendance requests.",
        next_steps="Build attendance dashboard.", repo_url="https://github.com/example/mist-attendance"))
    db.add_all([
        Announcement(title="Welcome to the 2026 SIWES Batch", audience="batch", batch_id=batch.id, created_by=admin.id if admin else None,
                     message="Sessions run weekdays from 10:00 at the MIST Training Hall. Bring your laptop and your ID."),
        Announcement(title="Attendance reminder", audience="all", created_by=admin.id if admin else None,
                     message="Scan the QR code shown by your instructor while you are in the training hall. Location access is required."),
        Announcement(title="Backend class: install PostgreSQL", audience="class", class_id=backend.id, created_by=instr.id if instr else None,
                     message="Please install PostgreSQL 15+ before the next session."),
    ])
    db.flush()  # lets the tracker see everything added since the last flush
    tables = Counter(type(o).__name__ for o in created)
    for obj in created:
        if hasattr(obj, "is_demo"):
            obj.is_demo = True
    if owns_session:
        db.commit()
    return {"created": len(created), "updated": 0, "skipped": 0, "tables": dict(tables), "warnings": warnings}


def run(reset: bool = False, db=None):
    cfg = get_settings()
    return run_seed(db, reset=reset, staff_emails={"instructor_email": cfg.seed_instructor_email,
                                                    "supervisor_email": cfg.seed_supervisor_email,
                                                    "admin_email": cfg.seed_admin_email})


if __name__ == "__main__":
    print(run("--reset" in sys.argv))

