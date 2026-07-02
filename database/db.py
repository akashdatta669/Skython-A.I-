"""
database/db.py — SQLAlchemy engine, session factory, and DB initialization
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from config import DB_PATH
from database.models import Base

log = logging.getLogger(__name__)

# ─────────────────────────── Engine ───────────────────────────────────────────
_DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    _DB_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,  # Allow multi-threaded access
        "timeout": 30,
    },
)

# Enable WAL mode and foreign-key enforcement for every new connection
@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _connection_record) -> None:  # type: ignore[type-arg]
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Global write lock — prevents concurrent writes from different threads
_write_lock = threading.Lock()


# ─────────────────────────── Context managers ─────────────────────────────────

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Yield a DB session; auto-commit on success, rollback on exception."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_write() -> Generator[Session, None, None]:
    """Yield a DB session guarded by the global write lock."""
    with _write_lock:
        with get_db() as db:
            yield db


# ─────────────────────────── Initialization ───────────────────────────────────

def init_db() -> None:
    """Create all tables (idempotent). Called once at startup."""
    log.info("Initializing database at %s", DB_PATH)
    Base.metadata.create_all(bind=engine)

    # Verify tables exist
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        )
        tables = [row[0] for row in result]

    log.info("✅ Database initialized. Tables: %s", tables)


def health_check() -> bool:
    """Return True if the database is reachable and tables exist."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.error("Database health check failed: %s", exc)
        return False
