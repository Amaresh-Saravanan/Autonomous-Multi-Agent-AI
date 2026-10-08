"""incidents / events / event_sources (Phase 2). Location is never
fabricated: `location_state` records whether lat/lon are exact, approximate,
or unknown (Phase 13) — consumers must branch on it, not assume a value."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class LocationStateEnum(str, enum.Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class IncidentStatusEnum(str, enum.Enum):
    DETECTED = "DETECTED"
    ASSESSING = "ASSESSING"
    ACTIVE = "ACTIVE"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Incident(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_status_severity", "status", "severity"),
    )

    status: Mapped[IncidentStatusEnum] = mapped_column(String(20), default=IncidentStatusEnum.DETECTED)
    severity: Mapped[float] = mapped_column(Float, default=0.0)
    location_state: Mapped[LocationStateEnum] = mapped_column(String(20), default=LocationStateEnum.UNKNOWN)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Event(Base, UUIDPkMixin):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_incident_id", "incident_id"),
        Index("ix_events_received_at", "received_at"),
    )

    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    location_state: Mapped[LocationStateEnum] = mapped_column(String(20), default=LocationStateEnum.UNKNOWN)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventSource(Base, UUIDPkMixin):
    """Provenance of an event: which device/channel produced it."""

    __tablename__ = "event_sources"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.id"), index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(50))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
