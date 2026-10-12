"""Import every model module so `Base.metadata` is complete for Alembic
autogenerate and for `create_all()` in tests."""

from app.models.base import Base
from app.models import (  # noqa: F401
    access,
    agent,
    alert,
    audit,
    citizen,
    incident,
    recommendation,
    resource,
    route,
    security,
)

__all__ = ["Base"]
