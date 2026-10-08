"""alerts (Phase 2, 21)."""

import enum
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class AlertLevelEnum(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatusEnum(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    SUPPRESSED = "SUPPRESSED"


class Alert(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_incident_id", "incident_id"),
        Index("ix_alerts_target_agency_id", "target_agency_id"),
        Index("ix_alerts_dedup_key", "dedup_key"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id"))
    level: Mapped[AlertLevelEnum] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    target_agency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agencies.id"), nullable=True
    )
    dedup_key: Mapped[str] = mapped_column(String(300))
    status: Mapped[AlertStatusEnum] = mapped_column(String(20), default=AlertStatusEnum.PUBLISHED)
