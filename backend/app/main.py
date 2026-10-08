import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import security
from .config import get_settings
from .db import engine
from .routers import (admin_tools, announcements, attendance, auth, dashboard, files, org, projects, reports,
                      training, users)

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    log.info("Starting MIST SIWES Hub API | db=%s | cors=%s | storage=%s | destructive_admin=%s",
             engine.dialect.name, s.cors_list, s.storage_backend, s.allow_destructive_admin)
    if "*" in s.cors_list or not s.cors_list:
        log.warning("CORS_ORIGINS is empty or '*' - set it to your frontend URL (no trailing slash)")
    if any(o.endswith("/") for o in s.cors_list):
        log.warning("CORS_ORIGINS contains a trailing slash - browsers send origins without one, so it will not match")
    security.init_firebase()  # logs a clear error at boot if the credentials are bad
    yield


app = FastAPI(title="MIST SIWES Hub API", version="1.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Always log the traceback server-side; send the client a safe, generic message.
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Something went wrong on the server. Please try again."}, status_code=500)


for r in (auth.router, users.router, users.students_router, org.dep_router, org.unit_router, org.batch_router,
          training.router, training.sessions_router, attendance.router, projects.router, projects.milestones_router,
          projects.submissions_router, announcements.router, reports.router, dashboard.router, files.router,
          admin_tools.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    """Open /api/health in a browser to check the deploy. Contains no secrets."""
    fb = security.firebase_status()
    return {"status": "ok" if fb["ready"] else "degraded", "database": engine.dialect.name, "firebase": fb}
