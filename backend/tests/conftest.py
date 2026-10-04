import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import security
from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = S()
    yield s
    s.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    def fake_verify(token: str) -> dict:
        try:
            uid, email, verified = token.split("|")
        except ValueError:
            raise ValueError("bad token")
        return {"uid": uid, "email": email, "email_verified": verified == "1", "name": ""}

    monkeypatch.setattr(security, "verify_firebase_token", fake_verify)
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def auth(uid: str, email: str, verified: bool = True) -> dict:
    return {"Authorization": f"Bearer {uid}|{email}|{1 if verified else 0}"}
