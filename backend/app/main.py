from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import admin_tools, announcements, attendance, auth, dashboard, files, org, projects, reports, training, users

app = FastAPI(title="MIST SIWES Hub API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])

for r in (auth.router, users.router, users.students_router, org.dep_router, org.unit_router, org.batch_router,
          training.router, training.sessions_router, attendance.router, projects.router, projects.milestones_router,
          projects.submissions_router, announcements.router, reports.router, dashboard.router, files.router):
    app.include_router(r)
app.include_router(admin_tools.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
