from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()
_sqlite = settings.database_url.startswith("sqlite")
_args = {"check_same_thread": False} if _sqlite else {}
engine = create_engine(settings.database_url, connect_args=_args, pool_pre_ping=True)


def configure_sqlite(eng) -> None:
    """SQLite ignores foreign keys and mishandles SAVEPOINTs by default. PostgreSQL needs none of this."""
    @event.listens_for(eng, "connect")
    def _connect(dbapi_conn, _):
        dbapi_conn.isolation_level = None  # we emit BEGIN ourselves (see below)
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    @event.listens_for(eng, "begin")
    def _begin(conn):
        conn.exec_driver_sql("BEGIN")


if _sqlite:
    configure_sqlite(engine)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
