 """Firebase ID-token verification. The backend never trusts identity data sent by the client."""
 import json
+import logging
 import threading
 
 import firebase_admin
@@
 from .config import get_settings
 
+log = logging.getLogger("uvicorn.error")
 _lock = threading.Lock()
 
 
@@ def _init_app():
         if firebase_admin._apps:
             return
         s = get_settings()
-        opts = {"projectId": s.firebase_project_id} if s.firebase_project_id else None
         if s.firebase_credentials_json:
-            cred = credentials.Certificate(json.loads(s.firebase_credentials_json))
+            info = json.loads(s.firebase_credentials_json)
+            cred = credentials.Certificate(info)
+            project_id = s.firebase_project_id or info.get("project_id")
         else:
             cred = credentials.ApplicationDefault()  # uses GOOGLE_APPLICATION_CREDENTIALS
-        firebase_admin.initialize_app(cred, opts)
+            project_id = s.firebase_project_id or None
+        firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
+        log.info("Firebase Admin initialised for project %s", project_id)
+
+
+class FirebaseConfigError(RuntimeError):
+    """Server-side Firebase misconfiguration (bad credentials). Surfaces as HTTP 500, never as a 401."""
 
 
 def verify_firebase_token(token: str) -> dict:
     """Returns {uid, email, email_verified, name}. Raises ValueError on any invalid token."""
-    _init_app()
     try:
-        d = fb_auth.verify_id_token(token, check_revoked=True)
-    except Exception as exc:  # expired, revoked, malformed, wrong project...
+        _init_app()
+    except Exception as exc:  # NB: json.JSONDecodeError and bad certs are ValueErrors; don't let them look like a bad token
+        log.error("Firebase Admin could not start - check FIREBASE_CREDENTIALS_JSON / FIREBASE_PROJECT_ID: %s: %s",
+                  type(exc).__name__, exc)
+        raise FirebaseConfigError(str(exc)) from exc
+    try:
+        d = fb_auth.verify_id_token(token)
+    except Exception as exc:  # expired, wrong project, malformed, clock skew...
+        log.warning("Firebase token rejected: %s: %s", type(exc).__name__, exc)
         raise ValueError(str(exc)) from exc
     return {
         "uid": d["uid"],
