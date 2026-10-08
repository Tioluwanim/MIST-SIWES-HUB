import io

import pytest
from openpyxl import Workbook

from app.config import get_settings
from app.importer import import_sheets
from app.models import Department, Project, SiwesBatch, Student, Unit, User

from .conftest import auth

ADMIN = auth("u-admin", "admin@mist.example.com")
STUD = auth("u-s", "s@mist.example.com")


@pytest.fixture()
def env(client, db_session):
    db_session.add(User(email="admin@mist.example.com", full_name="Admin", role="admin"))
    db_session.add(User(email="admin2@mist.example.com", full_name="Admin Two", role="admin", firebase_uid="u-admin2"))
    db_session.commit()
    assert client.post("/api/auth/sync", json={}, headers=ADMIN).status_code == 200
    assert client.post("/api/auth/sync", json={"full_name": "Stu Dent"}, headers=STUD).status_code == 200
    return client


def xlsx(sheets: dict) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def upload(c, data, name="x.xlsx", **params):
    return c.post("/api/admin/import", params=params, files={"file": (name, data, "application/octet-stream")}, headers=ADMIN)


def destructive(monkeypatch, on=True):
    monkeypatch.setattr(get_settings(), "allow_destructive_admin", on)


# ---------- access control ----------
def test_non_admin_forbidden_everywhere(env):
    for method, url, kw in [("get", "/api/admin/audit", {}), ("get", "/api/admin/status", {}),
                            ("post", "/api/admin/seed", {"json": {}}), ("delete", "/api/admin/demo-data", {}),
                            ("post", "/api/admin/reset", {"json": {"scope": "attendance", "confirm": "RESET"}}),
                            ("get", "/api/admin/import/template", {}), ("delete", "/api/admin/batches/1", {})]:
        assert getattr(env, method)(url, headers=STUD, **kw).status_code == 403, url
    assert env.get("/api/admin/import/template").status_code == 401  # and anonymous users get nothing


# ---------- destructive guard rails ----------
def test_destructive_blocked_by_default_and_reset_needs_confirm(env, monkeypatch):
    assert env.post("/api/admin/reset", json={"scope": "attendance", "confirm": "RESET"}, headers=ADMIN).status_code == 403
    destructive(monkeypatch)
    assert env.post("/api/admin/reset", json={"scope": "attendance", "confirm": "reset"}, headers=ADMIN).status_code == 422
    assert env.post("/api/admin/reset", json={"scope": "nope", "confirm": "RESET"}, headers=ADMIN).status_code == 422
    assert env.post("/api/admin/reset", json={"scope": "attendance", "confirm": "RESET"}, headers=ADMIN).status_code == 200


def test_reset_students_removes_users_too(env, db_session, monkeypatch):
    destructive(monkeypatch)
    assert env.post("/api/admin/reset", json={"scope": "students", "confirm": "RESET"}, headers=ADMIN).status_code == 200
    assert db_session.query(User).filter_by(role="student").count() == 0
    assert db_session.query(Student).count() == 0
    assert db_session.query(User).filter_by(role="admin").count() == 2


def test_last_admin_and_self_delete(env, db_session):
    me = db_session.query(User).filter_by(email="admin@mist.example.com").one()
    assert env.delete(f"/api/users/{me.id}", headers=ADMIN).status_code == 400


def test_delete_conflict_lists_counts_and_force_cascades(env, db_session, monkeypatch):
    destructive(monkeypatch)
    dep = env.post("/api/departments", json={"name": "Dept K"}, headers=ADMIN).json()
    env.post("/api/units", json={"department_id": dep["id"], "name": "Unit K"}, headers=ADMIN)
    r = env.delete(f"/api/admin/departments/{dep['id']}", headers=ADMIN)
    assert r.status_code == 409 and "1 units" in r.json()["detail"]
    assert env.delete(f"/api/admin/departments/{dep['id']}?force=true", headers=ADMIN).status_code == 200
    assert db_session.query(Unit).count() == 0


# ---------- seeding ----------
def test_seed_idempotent_uses_supplied_emails_and_flags_only_its_own_rows(env, db_session, monkeypatch):
    real = Department(name="Real Dept")
    db_session.add(real)
    db_session.commit()
    body = {"include_demo": True, "instructor_email": "ins@mist.example.com", "supervisor_email": "sup@mist.example.com"}
    a = env.post("/api/admin/seed", json=body, headers=ADMIN)
    b = env.post("/api/admin/seed", json=body, headers=ADMIN)
    assert a.status_code == 200 and a.json()["created"] > 0, a.text
    assert b.json()["skipped"] == 1 and b.json()["created"] == 0
    assert db_session.query(User).filter_by(email="ins@mist.example.com", role="instructor").count() == 1
    assert db_session.query(User).filter_by(email="admin@mist.example.com").one().is_demo is False
    assert db_session.query(Department).filter_by(name="Real Dept").one().is_demo is False
    assert any(x["action"] == "seed" for x in env.get("/api/admin/audit", headers=ADMIN).json())
    destructive(monkeypatch)
    assert env.delete("/api/admin/demo-data", headers=ADMIN).status_code == 200
    assert db_session.query(Department).filter_by(name="Real Dept").count() == 1
    assert db_session.query(User).filter_by(email="admin@mist.example.com").count() == 1
    assert db_session.query(User).filter_by(email="ins@mist.example.com").count() == 0


def test_seed_without_staff_emails_does_not_crash(env):
    r = env.post("/api/admin/seed", json={"include_demo": True}, headers=ADMIN)
    assert r.status_code == 200, r.text


# ---------- import ----------
def test_import_dry_run_then_real_then_idempotent(env, db_session):
    wb = xlsx({"Batches": [["name", "year"], ["2030 Batch", 2030]], "Departments": [["name"], ["Dept A"]],
               "Units": [["department", "name"], ["dept a", "Unit 1"]],
               "Students": [["full_name", "email", "batch", "department", "unit", "phone"],
                            ["Ada One", "ada@x.example.com", "2030 Batch", "Dept A", "Unit 1", 8135424176]]})
    r = upload(env, wb, dry_run=True)
    assert r.status_code == 200 and r.json()["total_errors"] == 0, r.text
    assert db_session.query(SiwesBatch).filter_by(name="2030 Batch").count() == 0
    assert upload(env, wb).status_code == 200
    assert all(s["created"] == 0 for s in upload(env, wb).json()["sheets"])
    ada = db_session.query(User).filter_by(email="ada@x.example.com").one()
    assert ada.student.phone == "08135424176"  # Excel dropped the leading zero; it is restored
    assert ada.is_demo is False                # imported data is REAL data


def test_import_unknown_reference_reports_row_and_applies_nothing(env, db_session):
    wb = xlsx({"Departments": [["name"], ["Dept Z"]],
               "Students": [["full_name", "email", "batch"], ["Bad Row", "bad@x.example.com", "No Such Batch"]]})
    r = upload(env, wb)
    assert r.status_code == 422
    st = next(s for s in r.json()["detail"]["sheets"] if s["sheet"] == "Students")["errors"][0]
    assert st["row"] == 2
    assert db_session.query(Department).filter_by(name="Dept Z").count() == 0


def test_import_skip_invalid_applies_only_good_rows_without_half_rows(env, db_session):
    wb = xlsx({"Projects": [["title", "student_emails"], ["Half Project", "ghost@x.example.com"], ["Fine Project", ""]]})
    r = upload(env, wb, skip_invalid=True)
    assert r.status_code == 200 and r.json()["total_errors"] == 1
    assert db_session.query(Project).filter_by(title="Half Project").count() == 0
    assert db_session.query(Project).filter_by(title="Fine Project").count() == 1


def test_import_rejects_role_change_bad_phone_and_bad_files(env):
    wb = xlsx({"Instructors": [["full_name", "email"], ["Hijack Him", "admin2@mist.example.com"]]})
    assert upload(env, wb, dry_run=True).json()["total_errors"] == 1
    wb = xlsx({"Students": [["full_name", "email", "phone"], ["Pho Ne", "p@x.example.com", "12345"]]})
    assert upload(env, wb, dry_run=True).json()["total_errors"] == 1
    assert upload(env, b"x", name="a.xls").status_code == 422
    assert upload(env, b"x", name="a.xlsm").status_code == 422


def test_import_formula_cells_are_never_evaluated(env, db_session):
    wb = xlsx({"Departments": [["name", "description"], ["Dept F", "=1+1"]]})
    assert upload(env, wb).status_code == 200
    assert db_session.query(Department).filter_by(name="Dept F").one().description in (None, "=1+1")


def test_template_downloads_and_reimports_cleanly(env):
    t = env.get("/api/admin/import/template", headers=ADMIN)
    assert t.status_code == 200
    r = upload(env, t.content, dry_run=True)
    assert r.status_code == 200 and r.json()["total_errors"] == 0, r.text


# ---------- student self-service ----------
def test_student_sets_own_department_and_unit(env, db_session):
    dep = env.post("/api/departments", json={"name": "Software"}, headers=ADMIN).json()
    other = env.post("/api/departments", json={"name": "Hardware"}, headers=ADMIN).json()
    unit = env.post("/api/units", json={"department_id": dep["id"], "name": "Dev"}, headers=ADMIN).json()
    me = lambda: env.get("/api/auth/me", headers=STUD).json()  # noqa: E731
    assert me()["department"] is None
    r = env.patch("/api/students/me/profile", json={"department_id": dep["id"], "unit_id": unit["id"]}, headers=STUD)
    assert r.status_code == 200 and r.json()["unit"]["name"] == "Dev" and me()["department"]["name"] == "Software"
    # a unit from another department is refused; unknown ids are 404; extra fields cannot escalate anything
    assert env.patch("/api/students/me/profile", json={"department_id": other["id"], "unit_id": unit["id"]}, headers=STUD).status_code == 422
    assert env.patch("/api/students/me/profile", json={"department_id": 999, "unit_id": 999}, headers=STUD).status_code == 404
    r = env.patch("/api/students/me/profile", json={"department_id": dep["id"], "unit_id": unit["id"], "role": "admin", "batch_id": 1}, headers=STUD)
    assert r.status_code == 200 and me()["role"] == "student" and me()["batch"] is None
    # staff cannot use the student endpoint, anonymous users cannot either
    assert env.patch("/api/students/me/profile", json={"department_id": dep["id"], "unit_id": unit["id"]}, headers=ADMIN).status_code == 403
    assert env.patch("/api/students/me/profile", json={"department_id": dep["id"], "unit_id": unit["id"]}).status_code == 401


# ---------- auth diagnostics ----------
def test_firebase_misconfig_is_clean_500_and_health_reports_it(env, monkeypatch):
    import firebase_admin
    monkeypatch.undo()
    monkeypatch.setattr(firebase_admin, "_apps", {})
    monkeypatch.setattr(get_settings(), "firebase_credentials_json", "'{bad")
    r = env.get("/api/auth/me", headers={"Authorization": "Bearer a.b.c"})
    assert r.status_code == 500 and "misconfigured" in r.json()["detail"]
    health = env.get("/api/health").json()
    assert health["status"] == "degraded" and health["firebase"]["error"]


def test_peek_explains_project_mismatch():
    import base64
    import json

    from app import security
    payload = base64.urlsafe_b64encode(json.dumps({"aud": "other-project", "exp": 1}).encode()).decode().rstrip("=")
    info = security._peek(f"x.{payload}.y")
    assert info["aud"] == "other-project" and info["expired"] is True


# ---- carried over from the earlier 'Admin panel' commit ----
def test_import_invalid_project_row_uses_savepoint_and_stays_production(db_session):
    batch = SiwesBatch(name="Import batch", year=2026)
    department = Department(name="Imported department")
    db_session.add_all([batch, department])
    db_session.commit()

    result = import_sheets(db_session, {
        "Departments": [{"name": "Imported department"}],
        "Projects": [{
            "title": "Invalid project",
            "batch": "Import batch",
            "student_emails": "missing@example.com",
        }],
    }, dry_run=False, skip_invalid=True)

    assert result[0]["updated"] == 1
    assert result[1]["skipped"] == 1
    assert db_session.query(Project).filter_by(title="Invalid project").one_or_none() is None
    imported = db_session.query(Department).filter_by(name="Imported department").one()
    assert imported.is_demo is False


def test_upstream_template_requires_admin(client, db_session):
    assert client.get("/api/admin/import/template").status_code == 401
    db_session.add(User(email="admin@mist.example.com", full_name="Admin", role="admin"))
    db_session.commit()
    assert client.post("/api/auth/sync", json={}, headers=auth("admin-id", "admin@mist.example.com")).status_code == 200
    assert client.get("/api/admin/import/template", headers=auth("admin-id", "admin@mist.example.com")).status_code == 200


def test_upstream_student_reset_removes_profiles_and_users(client, db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "allow_destructive_admin", True)
    admin = User(email="admin@mist.example.com", full_name="Admin", role="admin")
    student = User(email="student@mist.example.com", full_name="Student", role="student")
    student.student = Student()
    db_session.add_all([admin, student])
    db_session.commit()
    admin_auth = auth("admin-id", "admin@mist.example.com")
    assert client.post("/api/auth/sync", json={}, headers=admin_auth).status_code == 200
    response = client.post("/api/admin/reset", json={"scope": "students", "confirm": "RESET"}, headers=admin_auth)
    assert response.status_code == 200
    assert db_session.query(User).filter_by(email="student@mist.example.com").one_or_none() is None
    assert db_session.query(Student).count() == 0
