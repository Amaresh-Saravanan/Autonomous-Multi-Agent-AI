"""Declarative base + shared mixins for all V2 ORM models (Phase 2)."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def enum_column(enum_cls: type[enum.Enum], length: int = 20):
    """VARCHAR-backed enum column (`native_enum=False`) so both SQLite and
    PostgreSQL store the same portable representation and both coerce reads
    back to the Python enum member — a plain `String` column does not."""
    return Enum(enum_cls, native_enum=False, length=length, validate_strings=True)


class UUIDPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
