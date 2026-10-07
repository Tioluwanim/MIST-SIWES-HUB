# MIST SIWES Hub

SIWES training, QR + location attendance and project management for the Lagos State Ministry of Innovation, Science and Technology.

- `frontend/` Next.js 14, TypeScript, Tailwind (student PWA + staff dashboards)
- `backend/` FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- Auth: Firebase (email/password + Google). The backend verifies every ID token with the Firebase Admin SDK; roles live only in PostgreSQL.

## 1. Firebase
1. Create a Firebase project; enable **Email/Password** and **Google** sign-in; add `localhost` (and your domain) to authorised domains.
2. Project settings > Service accounts > generate a key. Save it as `backend/firebase-service-account.json` (git-ignored).
3. Copy the web app config into `frontend/.env.local` (see `frontend/.env.example`).

## 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set DATABASE_URL, FIREBASE_PROJECT_ID, SEED_*_EMAIL
createdb mist_siwes         # PostgreSQL
alembic upgrade head
python -m app.seed          # demo data (python -m app.seed --reset to wipe)
uvicorn app.main:app --reload --port 8000
pytest                      # SQLite, Firebase mocked
```
Set `SEED_ADMIN_EMAIL` (etc.) to emails you can sign in with. Sign in with that email (verified) and the seeded role is linked to your Firebase account. Anyone else who signs up becomes a `student`; admins assign batch, department and unit under Interns.

### Backend administration

The Settings > Admin tools dashboard can seed demo data, manage all four user
roles, import workbooks, deactivate users, reset scoped data, and inspect the
audit log. Destructive actions are disabled by default; set
`ALLOW_DESTRUCTIVE_ADMIN=true` only for an administrator who explicitly needs
deletes or resets. Regular user deletion is a safe deactivation.

Imports accept `.xlsx` or `.csv` (CSV requires a `type` query parameter), are
limited to 5 MB and 5,000 rows, and are processed in dependency order with
case-insensitive reference matching. Download the workbook from
`GET /api/admin/import/template`; its Instructions sheet documents all sheets,
`YYYY-MM-DD` dates, `HH:MM` times and semicolon-separated list columns.
Imports are upserts and non-destructive. A dry run writes nothing; invalid
rows can be skipped explicitly with `skip_invalid=true`. Run
`alembic upgrade head` after pulling backend schema changes.

## 3. Frontend
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev                 # http://localhost:3000
```
Camera and geolocation need HTTPS on phones. Use a deployed URL, or `ngrok http 3000` / `next dev --experimental-https` when testing on a device.

## Attendance rules (enforced server-side)
Valid Firebase token, active session, QR token matches and is unexpired (default 45 s, rotates every ~37 s, stored hashed), student enrolled in the class, GPS accuracy under 150 m, Haversine distance within the session radius, no duplicate (also a DB unique constraint). Late after `LATE_AFTER_MINUTES`. Stopping attendance marks everyone not checked in as Absent. Instructors can correct any record manually.

## Deploy notes
- `CORS_ORIGINS` must list the frontend URL. Set `STORAGE_BACKEND=s3` (+ `S3_*`) for uploads in production; `local` is for development.
- Never commit `.env`, `.env.local` or the service-account JSON.
