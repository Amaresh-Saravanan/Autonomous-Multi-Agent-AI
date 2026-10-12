"""Sync SQLAlchemy 2.0 engine/session (Phase 2). Production target is
PostgreSQL/PostGIS; SQLite is a test-only fallback via `DATABASE_URL`.
A `geom` PostGIS column is added by the Alembic migration on the
`postgresql` dialect only — the ORM models stay portable (lat/lon floats)
so SQLite tests never touch a PostGIS type."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(_settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency. `def` (sync) endpoints already run in FastAPI's
    threadpool, so this blocking session is never used directly on the
    async WebSocket path (see infrastructure/websocket.py)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """For use outside request scope: queue workers, scripts, agent runs."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
