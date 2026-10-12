"""Shared test fixtures. Forces SQLite before any app module is imported,
so the whole suite runs without PostgreSQL/Docker (NOT VERIFIED there)."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_v2.db")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest

from app.config import get_settings
from app.infrastructure.database import SessionLocal, engine
from app.models import Base


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    get_settings.cache_clear()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()
