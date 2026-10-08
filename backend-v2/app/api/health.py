"""Health + metrics endpoints (Phase 24)."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.infrastructure.database import engine

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
def health() -> dict:
    return {"status": "ok"}


@router.get("/live")
def live() -> dict:
    """Process is up and can serve requests at all."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    """Dependencies (DB) are actually reachable. Redis is checked
    separately — a Redis outage degrades agent/alert behavior but
    shouldn't take the whole API out of rotation for read-only routes."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}


@router.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
