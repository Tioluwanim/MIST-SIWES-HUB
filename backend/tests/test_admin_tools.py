from app.config import get_settings
from app.importer import import_sheets
from app.models import Department, Project, SiwesBatch, Student, User

from .conftest import auth


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


def test_template_requires_admin(client, db_session):
    assert client.get("/api/admin/import/template").status_code == 401
    db_session.add(User(email="admin@mist.example.com", full_name="Admin", role="admin"))
    db_session.commit()
    assert client.post("/api/auth/sync", json={}, headers=auth("admin-id", "admin@mist.example.com")).status_code == 200
    assert client.get("/api/admin/import/template", headers=auth("admin-id", "admin@mist.example.com")).status_code == 200


def test_student_reset_removes_profiles_and_users(client, db_session, monkeypatch):
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
