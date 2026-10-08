"""Firebase ID-token verification. The backend never trusts identity data sent by the client."""
import base64
import json
import logging
import threading
import time

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials

from .config import get_settings

log = logging.getLogger("uvicorn.error")
_lock = threading.Lock()
_state: dict = {"project_id": None, "client_email": None, "source": None, "error": None}


class FirebaseConfigError(RuntimeError):
    """Server-side Firebase misconfiguration (bad credentials). Surfaces as HTTP 500, never as a 401."""


def _init_app() -> None:
    with _lock:
        if firebase_admin._apps:
            return
        s = get_settings()
        if s.firebase_credentials_json:
            raw = s.firebase_credentials_json.strip()
            if raw[:1] in ("'", '"') and raw[-1:] == raw[:1]:
                raise ValueError("FIREBASE_CREDENTIALS_JSON is wrapped in quotes - paste the raw JSON without surrounding quotes")
            info = json.loads(raw)
            for key in ("type", "project_id", "private_key", "client_email"):
                if not info.get(key):
                    raise ValueError(f"service-account JSON is missing '{key}'")
            if "BEGIN PRIVATE KEY" not in info["private_key"]:
                raise ValueError("private_key does not look like a PEM key - was the JSON edited or truncated?")
            cred = credentials.Certificate(info)
            project_id = s.firebase_project_id or info["project_id"]
            _state.update(source="FIREBASE_CREDENTIALS_JSON", client_email=info["client_email"])
            if s.firebase_project_id and s.firebase_project_id != info["project_id"]:
                log.warning("FIREBASE_PROJECT_ID (%s) differs from the project_id inside the service-account JSON (%s)",
                            s.firebase_project_id, info["project_id"])
        else:
            cred = credentials.ApplicationDefault()  # uses GOOGLE_APPLICATION_CREDENTIALS
            project_id = s.firebase_project_id or None
            _state.update(source="GOOGLE_APPLICATION_CREDENTIALS", client_email=None)
        firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
        _state.update(project_id=project_id, error=None)
        log.info("Firebase Admin initialised: project=%s source=%s service_account=%s",
                 project_id, _state["source"], _state["client_email"])


def init_firebase() -> bool:
    """Try to start Firebase Admin; log and remember the reason on failure. Used at startup and for /api/health."""
    try:
        _init_app()
        return True
    except Exception as exc:
        _state["error"] = f"{type(exc).__name__}: {exc}"
        log.error("Firebase Admin could not start - check FIREBASE_CREDENTIALS_JSON / GOOGLE_APPLICATION_CREDENTIALS "
                  "/ FIREBASE_PROJECT_ID: %s", _state["error"])
        return False


def firebase_status() -> dict:
    """Safe to expose: contains no secrets."""
    if not firebase_admin._apps and not _state["error"]:
        init_firebase()
    ok = bool(firebase_admin._apps)
    return {"ready": ok, "project_id": _state["project_id"], "source": _state["source"],
            "error": None if ok else _state["error"]}


def _peek(token: str) -> dict:
    """Decode (WITHOUT verifying) a JWT payload so rejections can be explained in the logs."""
    try:
        payload = token.split(".")[1]
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        exp = data.get("exp")
        return {"aud": data.get("aud"), "iss": data.get("iss"),
                "expired": bool(exp and exp < time.time()), "expires_in_s": int(exp - time.time()) if exp else None}
    except Exception:
        return {"unreadable": True}


def verify_firebase_token(token: str) -> dict:
    """Returns {uid, email, email_verified, name}. Raises ValueError on a bad token, FirebaseConfigError on bad server config."""
    if not init_firebase():
        raise FirebaseConfigError(_state["error"] or "Firebase Admin is not initialised")
    try:
        d = fb_auth.verify_id_token(token)
    except Exception as exc:  # expired, wrong project, malformed, clock skew...
        info = _peek(token)
        hint = ""
        if info.get("aud") and _state["project_id"] and info["aud"] != _state["project_id"]:
            hint = f" | PROJECT MISMATCH: token is for '{info['aud']}' but the backend is configured for '{_state['project_id']}'"
        elif info.get("expired"):
            hint = " | token already expired (clock skew or stale session)"
        log.warning("Firebase token rejected: %s: %s | token=%s%s", type(exc).__name__, exc, info, hint)
        raise ValueError(str(exc)) from exc
    return {
        "uid": d["uid"],
        "email": (d.get("email") or "").lower(),
        "email_verified": bool(d.get("email_verified")),
        "name": d.get("name") or "",
    }


def delete_firebase_user(uid: str) -> bool:
    """Best-effort removal of the Firebase login when a user is hard-deleted. Logs and returns False on failure."""
    try:
        if not init_firebase():
            return False
        fb_auth.delete_user(uid)
        return True
    except Exception as exc:
        log.warning("Could not delete Firebase user %s: %s: %s", uid, type(exc).__name__, exc)
        return False
