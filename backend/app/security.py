"""Firebase ID-token verification. The backend never trusts identity data sent by the client."""
import json
import threading

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials

from .config import get_settings

_lock = threading.Lock()


def _init_app():
    with _lock:
        if firebase_admin._apps:
            return
        s = get_settings()
        opts = {"projectId": s.firebase_project_id} if s.firebase_project_id else None
        if s.firebase_credentials_json:
            cred = credentials.Certificate(json.loads(s.firebase_credentials_json))
        else:
            cred = credentials.ApplicationDefault()  # uses GOOGLE_APPLICATION_CREDENTIALS
        firebase_admin.initialize_app(cred, opts)


def verify_firebase_token(token: str) -> dict:
    """Returns {uid, email, email_verified, name}. Raises ValueError on any invalid token."""
    _init_app()
    try:
        d = fb_auth.verify_id_token(token, check_revoked=True)
    except Exception as exc:  # expired, revoked, malformed, wrong project...
        raise ValueError(str(exc)) from exc
    return {
        "uid": d["uid"],
        "email": (d.get("email") or "").lower(),
        "email_verified": bool(d.get("email_verified")),
        "name": d.get("name") or "",
    }
