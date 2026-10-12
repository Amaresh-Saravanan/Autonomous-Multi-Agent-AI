"""users / agencies / roles / permissions / devices (Phases 2, 6, 7)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin, enum_column


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class DeviceStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class Agency(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "agencies"

    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)


class Permission(Base, UUIDPkMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(300), default="")


class RolePermission(Base, UUIDPkMixin):
    __tablename__ = "role_permissions"

    role: Mapped[RoleEnum] = mapped_column(enum_column(RoleEnum), index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("permissions.id"))


class User(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[RoleEnum] = mapped_column(enum_column(RoleEnum), index=True)
    agency_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agencies.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    agency: Mapped["Agency"] = relationship()


class Device(Base, UUIDPkMixin, TimestampMixin):
    """Ingestion device credential (Phase 7). A device may submit only its
    declared `source_type`, and only on behalf of its own `agency_id`."""

    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_secret: Mapped[str] = mapped_column(String(255))
    agency_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agencies.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[DeviceStatusEnum] = mapped_column(enum_column(DeviceStatusEnum), default=DeviceStatusEnum.ACTIVE)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agency: Mapped["Agency"] = relationship()
