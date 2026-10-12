"""citizen_reports (Phase 2; fed by the citizen normalizer / AG-7)."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin, enum_column
from app.models.incident import LocationStateEnum


class CitizenReport(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "citizen_reports"

    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id"), nullable=True, index=True
    )
    reporter_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    location_state: Mapped[LocationStateEnum] = mapped_column(enum_column(LocationStateEnum), default=LocationStateEnum.UNKNOWN)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_score: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(30), default="app")
    claimed_severity: Mapped[float] = mapped_column(Float, default=0.5, server_default="0.5")
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=True)
