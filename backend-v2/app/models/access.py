"""access_requests: self-service signup / password-reset REQUESTS. Nothing
here grants access by itself — an ADMIN approves each one (SEC-1), which is
when a user is created or a temporary password is issued."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin, enum_column


class AccessRequestKind(str, enum.Enum):
    SIGNUP = "SIGNUP"
    RESET = "RESET"


class AccessRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AccessRequest(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "access_requests"

    kind: Mapped[AccessRequestKind] = mapped_column(enum_column(AccessRequestKind), index=True)
    status: Mapped[AccessRequestStatus] = mapped_column(
        enum_column(AccessRequestStatus), default=AccessRequestStatus.PENDING, index=True
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    agency_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requested_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
