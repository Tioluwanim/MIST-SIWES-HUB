"""Validation and dependency-aware spreadsheet imports for administrators."""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, time
from typing import Any

from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import (Department, Project, SiwesBatch, Student, TrainingClass,
                     TrainingProgram, TrainingSession, Unit, User, ProjectMember,
                     ProjectSupervisor, ProjectMilestone)
from .services import enroll_student_in_batch_classes

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SHEETS = {
    "Batches": ["name", "year", "start_date", "end_date"],
    "Departments": ["name", "description"],
    "Units": ["department", "name"],
    "Students": ["full_name", "email", "matric_no", "institution", "batch", "department", "unit"],
    "Instructors": ["full_name", "email", "department", "unit"],
    "Supervisors": ["full_name", "email", "department"],
    "Admins": ["full_name", "email"],
    "Programs": ["batch", "name", "description"],
    "Classes": ["program", "name", "instructor_email"],
    "Sessions": ["class", "title", "date", "start_time", "end_time", "location", "latitude", "longitude", "radius_meters"],
    "Projects": ["title", "description", "batch", "start_date", "deadline", "student_emails", "supervisor_emails", "milestones"],
}
ORDER = list(SHEETS)
ALIASES = {name.lower(): name for name in SHEETS}


def _text(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        # Workbook values are never evaluated; formula-looking values remain
        # ordinary strings when persisted.
    return value


def _key(value: Any) -> str:
    return str(value).strip().casefold() if value is not None else ""


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())


def _time(value: Any) -> time | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value).strip())


def parse_import(raw: bytes, filename: str, csv_type: str | None = None) -> dict[str, list[dict[str, Any]]]:
    settings = get_settings()
    if len(raw) > settings.max_import_mb * 1024 * 1024:
        raise ValueError(f"file exceeds the {settings.max_import_mb} MB limit")
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        book = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        output = {}
        total = 0
        for sheet in book.worksheets:
            if sheet.title.casefold() == "instructions":
                continue
            rows = list(sheet.values)
            if not rows:
                continue
            headers = [str(_text(x) or "").strip() for x in rows[0]]
            values = [{h: _text(v) for h, v in zip(headers, row)} for row in rows[1:]
                      if any(v not in (None, "") for v in row)]
            total += len(values)
            if total > settings.max_import_rows:
                raise ValueError(f"at most {settings.max_import_rows} rows are allowed")
            output[ALIASES.get(sheet.title.casefold(), sheet.title)] = values
        return output
    if not lower.endswith(".csv"):
        raise ValueError("only .xlsx and .csv files are supported")
    if not csv_type or csv_type.casefold() not in ALIASES:
        raise ValueError("CSV imports require a valid type query parameter")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if len(rows) > settings.max_import_rows:
        raise ValueError(f"at most {settings.max_import_rows} rows are allowed")
    return {ALIASES[csv_type.casefold()]: [{k: _text(v) for k, v in row.items()} for row in rows]}


def template_bytes() -> bytes:
    book = Workbook()
    instructions = book.active
    instructions.title = "Instructions"
    instructions.append(["Sheet", "Use", "Dates", "Times", "Lists"])
    instructions.append(["All", "Fill only the columns you need to update.", "YYYY-MM-DD", "HH:MM", "Separate list values with ;"])
    for sheet, headers in SHEETS.items():
        ws = book.create_sheet(sheet)
        ws.append(headers)
        examples = {
            "Batches": ["2026 SIWES Batch", 2026, "2026-08-03", "2027-01-29"],
            "Departments": ["Software & Digital Services", "Example department"],
            "Units": ["Software & Digital Services", "Software Development"],
            "Students": ["Ada Example", "ada@example.org", "MIST/001", "Example University", "2026 SIWES Batch", "Software & Digital Services", "Software Development"],
            "Instructors": ["Kayode Example", "kayode@example.org", "Software & Digital Services", "Software Development"],
            "Supervisors": ["Ngozi Example", "ngozi@example.org", "Software & Digital Services"],
            "Admins": ["Admin Example", "admin@example.org"],
            "Programs": ["2026 SIWES Batch", "Software Development Training", "Example program"],
            "Classes": ["Software Development Training", "Backend Development", "kayode@example.org"],
            "Sessions": ["Backend Development", "HTTP Fundamentals", "2026-08-04", "10:00", "12:00", "MIST Training Hall", 6.6186, 3.3569, 100],
            "Projects": ["Example Project", "Example project", "2026 SIWES Batch", "2026-08-03", "2026-09-01", "ada@example.org", "ngozi@example.org", "Requirements;Delivery"],
        }
        ws.append(examples[sheet])
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def _lookup(db: Session, model, field: str, value: Any):
    return db.scalar(select(model).where(getattr(model, field).ilike(str(value).strip())))


def _ref(db: Session, model, value: Any, label: str):
    obj = _lookup(db, model, "name", value)
    if not obj:
        raise ValueError(f"{label} {value!r} was not found")
    return obj


def import_sheets(db: Session, sheets: dict[str, list[dict]], *, dry_run: bool,
                  skip_invalid: bool, actor: User | None = None) -> list[dict]:
    summaries = {name: {"sheet": name, "created": 0, "updated": 0, "skipped": 0, "errors": []} for name in sheets}

    def error(summary, row, column, message):
        summary["errors"].append({"sheet": summary["sheet"], "row": row, "column": column, "message": message})

    for sheet in sorted(sheets, key=lambda n: ORDER.index(n) if n in ORDER else len(ORDER)):
        summary = summaries[sheet]
        for excel_row, raw in enumerate(sheets[sheet], 2):
            row = {str(k).strip().casefold(): v for k, v in raw.items()}
            savepoint = db.begin_nested()
            try:
                if sheet == "Batches":
                    name = str(row.get("name") or "").strip()
                    if not name: raise ValueError("name is required")
                    obj = _lookup(db, SiwesBatch, "name", name)
                    values = {"name": name, "year": int(row["year"])}
                    for k in ("start_date", "end_date"):
                        if row.get(k) not in (None, ""): values[k] = _date(row[k])
                    model = SiwesBatch
                elif sheet == "Departments":
                    name = str(row.get("name") or "").strip()
                    if not name: raise ValueError("name is required")
                    obj = _lookup(db, Department, "name", name)
                    values = {"name": name}
                    if "description" in row and row["description"] not in (None, ""): values["description"] = row["description"]
                    model = Department
                elif sheet == "Units":
                    dep = _ref(db, Department, row.get("department"), "department")
                    name = str(row.get("name") or "").strip()
                    obj = db.scalar(select(Unit).where(Unit.department_id == dep.id, Unit.name.ilike(name)))
                    values = {"department_id": dep.id, "name": name}
                    model = Unit
                elif sheet in ("Students", "Instructors", "Supervisors", "Admins"):
                    email = str(row.get("email") or "").strip().lower()
                    if not EMAIL.match(email): raise ValueError("a valid email is required")
                    role = {"Students": "student", "Instructors": "instructor", "Supervisors": "supervisor", "Admins": "admin"}[sheet]
                    obj = db.scalar(select(User).where(User.email == email))
                    if obj and obj.role != role: raise ValueError(f"email already has role {obj.role}")
                    values = {"email": email, "full_name": str(row.get("full_name") or "").strip(), "role": role}
                    dep = _ref(db, Department, row["department"], "department") if row.get("department") else None
                    unit = _ref(db, Unit, row["unit"], "unit") if row.get("unit") else None
                    if dep: values["department_id"] = dep.id
                    if unit:
                        if dep and unit.department_id != dep.id: raise ValueError("unit does not belong to department")
                        values["unit_id"] = unit.id
                    model = User
                elif sheet == "Programs":
                    batch = _ref(db, SiwesBatch, row.get("batch"), "batch")
                    name = str(row.get("name") or "").strip()
                    obj = db.scalar(select(TrainingProgram).where(TrainingProgram.batch_id == batch.id, TrainingProgram.name.ilike(name)))
                    values = {"batch_id": batch.id, "name": name}
                    if row.get("description") not in (None, ""): values["description"] = row["description"]
                    model = TrainingProgram
                elif sheet == "Classes":
                    program = _ref(db, TrainingProgram, row.get("program"), "program")
                    name = str(row.get("name") or "").strip()
                    obj = db.scalar(select(TrainingClass).where(TrainingClass.program_id == program.id, TrainingClass.name.ilike(name)))
                    values = {"program_id": program.id, "name": name}
                    if row.get("instructor_email"):
                        ins = db.scalar(select(User).where(User.email == str(row["instructor_email"]).strip().lower(), User.role == "instructor"))
                        if not ins: raise ValueError("instructor_email was not found")
                        values["instructor_id"] = ins.id
                    model = TrainingClass
                elif sheet == "Sessions":
                    cls = _ref(db, TrainingClass, row.get("class"), "class")
                    title = str(row.get("title") or "").strip()
                    session_date = _date(row.get("date"))
                    obj = db.scalar(select(TrainingSession).where(TrainingSession.training_class_id == cls.id, TrainingSession.title.ilike(title), TrainingSession.date == session_date))
                    values = {"training_class_id": cls.id, "title": title, "date": session_date,
                              "start_time": _time(row.get("start_time")), "end_time": _time(row.get("end_time")),
                              "location": row.get("location"), "latitude": float(row["latitude"]), "longitude": float(row["longitude"])}
                    if row.get("radius_meters") not in (None, ""): values["allowed_radius_meters"] = int(row["radius_meters"])
                    if not -90 <= values["latitude"] <= 90 or not -180 <= values["longitude"] <= 180: raise ValueError("coordinates are out of range")
                    model = TrainingSession
                elif sheet == "Projects":
                    title = str(row.get("title") or "").strip()
                    if not title: raise ValueError("title is required")
                    obj = _lookup(db, Project, "title", title)
                    batch = _ref(db, SiwesBatch, row["batch"], "batch") if row.get("batch") else None
                    values = {"title": title, "batch_id": batch.id if batch else None}
                    for key in ("description",):
                        if row.get(key) not in (None, ""): values[key] = row[key]
                    for key in ("start_date", "deadline"):
                        if row.get(key) not in (None, ""): values[key] = _date(row[key])
                    model = Project
                else:
                    summary["skipped"] += 1
                    continue
                if obj:
                    for key, value in values.items():
                        if value is not None: setattr(obj, key, value)
                    summary["updated"] += 1
                else:
                    obj = model(**values)
                    db.add(obj); db.flush()
                    summary["created"] += 1
                if sheet == "Students":
                    student = obj.student or Student(user_id=obj.id)
                    batch = _ref(db, SiwesBatch, row.get("batch"), "batch") if row.get("batch") else None
                    student.batch_id = batch.id if batch else student.batch_id
                    for attr in ("matric_no", "institution"):
                        if row.get(attr) not in (None, ""): setattr(student, attr, row[attr])
                    db.add(student); db.flush()
                    enroll_student_in_batch_classes(db, student)
                elif sheet == "Projects":
                    if row.get("student_emails"):
                        for email in str(row["student_emails"]).split(";"):
                            user = db.scalar(select(User).where(User.email == email.strip().lower()))
                            if not user or not user.student: raise ValueError(f"student email {email.strip()!r} was not found")
                            if not any(m.student_id == user.student.id for m in obj.members):
                                obj.members.append(ProjectMember(student_id=user.student.id))
                    if row.get("supervisor_emails"):
                        for email in str(row["supervisor_emails"]).split(";"):
                            user = db.scalar(select(User).where(User.email == email.strip().lower(), User.role == "supervisor"))
                            if not user: raise ValueError(f"supervisor email {email.strip()!r} was not found")
                            if not any(m.user_id == user.id for m in obj.supervisors):
                                obj.supervisors.append(ProjectSupervisor(user_id=user.id))
                    if row.get("milestones"):
                        for index, title in enumerate(str(row["milestones"]).split(";")):
                            title = title.strip()
                            if title and not any(m.title.casefold() == title.casefold() for m in obj.milestones):
                                obj.milestones.append(ProjectMilestone(title=title, position=index))
                savepoint.commit()
            except Exception as exc:
                savepoint.rollback()
                error(summary, excel_row, "", str(exc))
                summary["skipped"] += 1
                if not skip_invalid:
                    continue
    if dry_run:
        db.rollback()
    return list(summaries.values())
