from datetime import date, datetime, timedelta

from app.models import AttendanceSession
from app.timeutil import local_now, utcnow

from .conftest import auth

ADMIN = auth("u-admin", "admin@mist.example.com")
INSTR = auth("u-instr", "instr@mist.example.com")
SUP = auth("u-sup", "sup@mist.example.com")
VENUE = (6.6186, 3.3569)


def bootstrap(client, db_session, n_students=2):
    """Admin is created directly (bootstrap), everything else goes through the API."""
    from app.models import User
    db_session.add(User(email="admin@mist.example.com", full_name="Admin", role="admin"))
    db_session.commit()
    assert client.post("/api/auth/sync", json={}, headers=ADMIN).status_code == 200
    batch = client.post("/api/batches", json={"name": "2026 SIWES Batch", "year": 2026}, headers=ADMIN).json()
    dep = client.post("/api/departments", json={"name": "Software"}, headers=ADMIN).json()
    unit = client.post("/api/units", json={"department_id": dep["id"], "name": "Dev"}, headers=ADMIN).json()
    for body in ({"email": "instr@mist.example.com", "full_name": "Instr", "role": "instructor"},
                 {"email": "sup@mist.example.com", "full_name": "Sup", "role": "supervisor"}):
        assert client.post("/api/users", json=body, headers=ADMIN).status_code == 201
    studs = []
    for i in range(n_students):
        r = client.post("/api/users", json={"email": f"s{i}@mist.example.com", "full_name": f"Student {i}", "role": "student",
                                            "department_id": dep["id"], "unit_id": unit["id"], "batch_id": batch["id"]}, headers=ADMIN)
        assert r.status_code == 201, r.text
        studs.append(r.json())
    for h in (INSTR, SUP, *(auth(f"u-s{i}", f"s{i}@mist.example.com") for i in range(n_students))):
        assert client.post("/api/auth/sync", json={}, headers=h).status_code == 200
    instr_id = next(u["id"] for u in client.get("/api/users?role=instructor", headers=ADMIN).json())
    prog = client.post("/api/training/programs", json={"batch_id": batch["id"], "name": "SWE"}, headers=ADMIN).json()
    cls = client.post("/api/training/classes", json={"program_id": prog["id"], "name": "Backend", "instructor_id": instr_id},
                      headers=ADMIN).json()
    assert cls["student_count"] == n_students  # batch auto-enrolled
    now = local_now()
    sess = client.post("/api/sessions", json={
        "training_class_id": cls["id"], "title": "FastAPI", "date": now.date().isoformat(), "start_time": "00:00:00",
        "end_time": "23:59:00", "latitude": VENUE[0], "longitude": VENUE[1], "allowed_radius_meters": 100}, headers=INSTR)
    assert sess.status_code == 201, sess.text
    return {"batch": batch, "cls": cls, "session": sess.json(), "students": studs, "dep": dep}


def test_auth_required_and_role_checks(client, db_session):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
    ctx = bootstrap(client, db_session)
    s0 = auth("u-s0", "s0@mist.example.com")
    assert client.get("/api/auth/me", headers=s0).json()["role"] == "student"
    assert client.post("/api/batches", json={"name": "x batch", "year": 2030}, headers=s0).status_code == 403
    assert client.get("/api/reports/attendance", headers=INSTR).status_code == 403
    assert client.post(f"/api/attendance/sessions/{ctx['session']['id']}/start", headers=s0).status_code == 403


def test_unverified_email_cannot_claim_provisioned_account(client, db_session):
    from app.models import User
    db_session.add(User(email="admin@mist.example.com", full_name="Admin", role="admin"))
    db_session.commit()
    r = client.post("/api/auth/sync", json={}, headers=auth("attacker", "admin@mist.example.com", verified=False))
    assert r.status_code == 403
    r = client.post("/api/auth/sync", json={"full_name": "New"}, headers=auth("fresh", "fresh@mist.example.com", verified=False))
    assert r.status_code == 200 and r.json()["role"] == "student"  # client can never choose a role


def test_attendance_happy_path_and_rejections(client, db_session):
    ctx = bootstrap(client, db_session, n_students=3)
    sid = ctx["session"]["id"]
    s0, s1, s2 = (auth(f"u-s{i}", f"s{i}@mist.example.com") for i in range(3))
    scan = lambda h, tok, lat=VENUE[0], lon=VENUE[1], **kw: client.post(
        "/api/attendance/scan", json={"token": tok, "latitude": lat, "longitude": lon, **kw}, headers=h)

    tok = client.post(f"/api/attendance/sessions/{sid}/start", headers=INSTR).json()["token"]
    assert scan(s0, "x" * 32).status_code == 400                      # invalid token
    r = scan(s0, tok, lat=VENUE[0] + 0.006)                           # ~660 m away
    assert r.status_code == 403 and "within 100 m" in r.json()["detail"]
    r = scan(s0, tok, lat=VENUE[0] + 0.0003)                          # ~33 m away
    assert r.status_code == 200 and r.json()["status"] in ("Present", "Late") and r.json()["distance_meters"] < 100
    assert scan(s0, tok).status_code == 409                           # duplicate
    assert scan(s1, tok, accuracy=900).status_code == 400             # unusable GPS fix

    # token rotation invalidates the old code
    new = client.post(f"/api/attendance/sessions/{sid}/refresh", headers=INSTR).json()["token"]
    assert scan(s1, tok).status_code == 400
    # expiry
    att = db_session.query(AttendanceSession).one()
    att.token_expires_at = utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert scan(s1, new).status_code == 410
    new = client.post(f"/api/attendance/sessions/{sid}/refresh", headers=INSTR).json()["token"]
    assert scan(s1, new).status_code == 200

    live = client.get(f"/api/attendance/sessions/{sid}/live", headers=INSTR).json()
    assert live["total"] == 3 and live["counts"]["Pending"] == 1

    # manual marking (excused) then close -> remaining become Absent, QR no longer works
    assert client.post("/api/attendance/manual", json={"session_id": sid, "student_id": ctx["students"][2]["student_id"],
                                                      "status": "Excused", "remarks": "Medical"}, headers=INSTR).status_code == 200
    stop = client.post(f"/api/attendance/sessions/{sid}/stop", headers=INSTR).json()
    assert stop["auto_marked_absent"] == 0
    assert scan(s2, new).status_code == 400

    me = client.get("/api/attendance/me", headers=s0).json()
    assert me["summary"]["total"] == 1 and me["summary"]["rate"] == 100.0
    summ = client.get("/api/attendance/summary", headers=ADMIN).json()
    assert summ["overall"]["total"] == 3 and summ["overall"]["Excused"] == 1
    assert client.get("/api/dashboard/admin", headers=ADMIN).json()["total_interns"] == 3
    csv = client.get("/api/reports/attendance?format=csv", headers=ADMIN)
    assert csv.status_code == 200 and "Attendance Rate" in csv.text


def test_not_enrolled_and_other_instructor_blocked(client, db_session):
    ctx = bootstrap(client, db_session, n_students=1)
    sid = ctx["session"]["id"]
    tok = client.post(f"/api/attendance/sessions/{sid}/start", headers=INSTR).json()["token"]
    outsider = auth("u-out", "outsider@mist.example.com")
    assert client.post("/api/auth/sync", json={"full_name": "Out"}, headers=outsider).status_code == 200
    r = client.post("/api/attendance/scan", json={"token": tok, "latitude": VENUE[0], "longitude": VENUE[1]}, headers=outsider)
    assert r.status_code == 403
    # supervisors cannot run attendance
    assert client.post(f"/api/attendance/sessions/{sid}/start", headers=SUP).status_code == 403


def test_project_workflow(client, db_session):
    ctx = bootstrap(client, db_session, n_students=2)
    sup_id = next(u["id"] for u in client.get("/api/users?role=supervisor", headers=ADMIN).json())
    s0, s1 = auth("u-s0", "s0@mist.example.com"), auth("u-s1", "s1@mist.example.com")
    proj = client.post("/api/projects", json={
        "title": "Attendance Platform", "batch_id": ctx["batch"]["id"], "deadline": (date.today() + timedelta(days=30)).isoformat(),
        "member_ids": [ctx["students"][0]["student_id"]], "supervisor_ids": [sup_id],
        "milestones": [{"title": "Requirements"}, {"title": "Backend"}]}, headers=ADMIN)
    assert proj.status_code == 201, proj.text
    pid, ms = proj.json()["id"], proj.json()["milestones"]
    assert proj.json()["progress"] == 0

    # only members see / submit
    assert client.get(f"/api/projects/{pid}", headers=s1).status_code == 403
    assert client.post("/api/submissions", json={"project_id": pid, "title": "xx"}, headers=s1).status_code == 403
    assert client.post("/api/submissions", json={"project_id": pid, "title": "bad", "repo_url": "javascript:alert(1)"},
                       headers=s0).status_code == 422
    sub = client.post("/api/submissions", json={"project_id": pid, "milestone_id": ms[0]["id"], "title": "Week 1",
                                                "worked_on": "Wrote requirements", "repo_url": "https://github.com/x/y"}, headers=s0)
    assert sub.status_code == 201

    # students cannot review or edit milestones; supervisor can
    assert client.patch(f"/api/milestones/{ms[0]['id']}", json={"status": "Completed"}, headers=s0).status_code == 403
    rev = client.patch(f"/api/submissions/{sub.json()['id']}/review", json={
        "review_status": "Approved", "feedback": "Good start", "mark_milestone_complete": True}, headers=SUP)
    assert rev.status_code == 200 and rev.json()["project_progress"] == 50
    r = client.patch(f"/api/milestones/{ms[1]['id']}", json={"status": "Completed"}, headers=SUP).json()
    assert r["project_progress"] == 100 and r["project_status"] == "Under Review"
    assert client.patch(f"/api/projects/{pid}", json={"status": "Completed"}, headers=SUP).status_code == 200

    got = client.get("/api/projects", headers=ADMIN).json()
    assert got[0]["status"] == "Completed" and got[0]["progress"] == 100
    assert client.get("/api/reports/projects?format=csv", headers=ADMIN).status_code == 200
    sd = client.get("/api/dashboard/student", headers=s0).json()
    assert sd["active_project"] is None  # completed projects drop off the dashboard


def test_announcement_audiences(client, db_session):
    ctx = bootstrap(client, db_session, n_students=1)
    s0 = auth("u-s0", "s0@mist.example.com")
    client.post("/api/announcements", json={"title": "All", "message": "hello all"}, headers=ADMIN)
    other = client.post("/api/batches", json={"name": "2031 SIWES Batch", "year": 2031}, headers=ADMIN).json()
    assert client.post("/api/announcements", json={"title": "Ghost", "message": "no", "audience": "batch", "batch_id": 999}, headers=ADMIN).status_code == 422
    client.post("/api/announcements", json={"title": "Other batch", "message": "no", "audience": "batch", "batch_id": other["id"]}, headers=ADMIN)
    client.post("/api/announcements", json={"title": "My class", "message": "yes", "audience": "class",
                                            "class_id": ctx["cls"]["id"]}, headers=INSTR)
    titles = {a["title"] for a in client.get("/api/announcements", headers=s0).json()}
    assert titles == {"All", "My class"}
    assert client.post("/api/announcements", json={"title": "Nope", "message": "nope"}, headers=INSTR).status_code == 403
