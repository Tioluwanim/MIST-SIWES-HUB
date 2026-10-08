import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import security
from .db import get_db
from .models import Student, User

log = logging.getLogger("uvicorn.error")
bearer = HTTPBearer(auto_error=False)


def get_claims(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not creds:
        log.warning("Request without a bearer token")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        # looked up through the module so tests can patch it
        return security.verify_firebase_token(creds.credentials)
    except security.FirebaseConfigError:
        # our fault, not the user's: don't tell them their token is bad, and don't leak details
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Authentication service is misconfigured. Please contact the administrator.")
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})


def get_current_user(claims: dict = Depends(get_claims), db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.firebase_uid == claims["uid"]))
    if not user:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account not registered. Call /api/auth/sync first.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            log.warning("403: user %s (%s) tried an endpoint restricted to %s", user.id, user.role, roles)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to do this")
        return user
    return checker


def current_student(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)) -> Student:
    st = db.scalar(select(Student).where(Student.user_id == user.id))
    if not st:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No student profile")
    return st
