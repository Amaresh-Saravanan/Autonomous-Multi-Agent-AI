"""audit_logs (Phase 2, 20). Append-only: no update/delete path is exposed
anywhere in the service layer — this table only grows."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPkMixin, enum_column


class ActorTypeEnum(str, enum.Enum):
    SYSTEM = "SYSTEM"
    AGENT = "AGENT"
    USER = "USER"
    DEVICE = "DEVICE"


class AuditLog(Base, UUIDPkMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_incident_id", "incident_id"),
        Index("ix_audit_logs_agency_id", "agency_id"),
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_type: Mapped[ActorTypeEnum] = mapped_column(enum_column(ActorTypeEnum))
    actor_id: Mapped[str] = mapped_column(String(100))
    agency_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("agencies.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    incident_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id"), nullable=True)
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("recommendations.id"), nullable=True
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
