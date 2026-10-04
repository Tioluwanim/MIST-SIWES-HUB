from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_claims, get_current_user
from ..models import Student, User
from ..schemas import SyncIn
from ..services import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/sync")
def sync(body: SyncIn, claims: dict = Depends(get_claims), db: Session = Depends(get_db)):
    """Link the verified Firebase identity to a PostgreSQL user (creating a student profile if new).

    Role/department/batch are never read from the client. Staff and pre-registered students are
    pre-provisioned by an admin and are linked by *verified* email only.
    """
    uid, email = claims["uid"], claims["email"]
    if not email:
        raise HTTPException(400, "Your account has no email address")
    user = db.scalar(select(User).where(User.firebase_uid == uid))
    if user:
        return user_out(user)
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        if existing.firebase_uid and existing.firebase_uid != uid:
            raise HTTPException(409, "This email is already linked to another sign-in")
        if not claims["email_verified"]:
            raise HTTPException(403, "Verify your email address to activate your account, then sign in again.")
        existing.firebase_uid = uid
        db.commit()
        return user_out(existing)
    name = (body.full_name or claims["name"] or email.split("@")[0]).strip()
    user = User(firebase_uid=uid, email=email, full_name=name, role="student")
    user.student = Student()
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Account already exists")
    return user_out(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)
