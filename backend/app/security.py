"""Firebase ID-token verification. The backend never trusts identity data sent by the client."""
import json
import logging
import threading

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials

from .config import get_settings

log = logging.getLogger("uvicorn.error")
_lock = threading.Lock()


def _init_app():
    with _lock:
        if firebase_admin._apps:
            return
        s = get_settings()
        if s.firebase_credentials_json:
            info = json.loads(s.firebase_credentials_json)
            cred = credentials.Certificate(info)
            project_id = s.firebase_project_id or info.get("project_id")
        else:
            cred = credentials.ApplicationDefault()  # uses GOOGLE_APPLICATION_CREDENTIALS
            project_id = s.firebase_project_id or None
        firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
        log.info("Firebase Admin initialised for project %s", project_id)


def verify_firebase_token(token: str) -> dict:
    """Returns {uid, email, email_verified, name}. Raises ValueError on any invalid token."""
    _init_app()
    try:
        d = fb_auth.verify_id_token(token)
    except Exception as exc:  # expired, wrong project, malformed, clock skew...
        log.warning("Firebase token rejected: %s: %s", type(exc).__name__, exc)
        raise ValueError(str(exc)) from exc
    return {
        "uid": d["uid"],
        "email": (d.get("email") or "").lower(),
        "email_verified": bool(d.get("email_verified")),
        "name": d.get("name") or "",
    }
