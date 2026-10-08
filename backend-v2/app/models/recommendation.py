"""recommendations / recommendation_evidence (Phases 2, 17, 18)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin, enum_column


class RecommendationStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"
    EXPIRED = "EXPIRED"


class Recommendation(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_incident_id", "incident_id"),
        Index("ix_recommendations_target_agency_id", "target_agency_id"),
        Index("ix_recommendations_status", "status"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id"))
    agent_id: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    # Phase 17: NULL target_agency must NOT mean "visible to every agency" —
    # query filters require an explicit agency match, enforced in the service layer.
    target_agency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agencies.id"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[RecommendationStatusEnum] = mapped_column(enum_column(RecommendationStatusEnum), default=RecommendationStatusEnum.PENDING)

    # Human decision loop (Phase 18)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_action: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecommendationEvidence(Base, UUIDPkMixin):
    __tablename__ = "recommendation_evidence"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("recommendations.id"), index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
