"""routes / route_status (Phase 2; consumed by AG-6 RoutingService)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin, enum_column


class RouteStatusEnum(str, enum.Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class Route(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "routes"

    incident_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id"), index=True)
    origin_lat: Mapped[float] = mapped_column(Float)
    origin_lon: Mapped[float] = mapped_column(Float)
    destination_lat: Mapped[float] = mapped_column(Float)
    destination_lon: Mapped[float] = mapped_column(Float)
    # ponytail: "fallback" is the only provider actually implemented today;
    # "osrm" is a valid value once RoutingService.provider is wired to a real OSRM instance.
    provider: Mapped[str] = mapped_column(String(20))
    distance_km: Mapped[float] = mapped_column(Float)
    eta_minutes: Mapped[float] = mapped_column(Float)
    geometry: Mapped[list] = mapped_column(JSON)
    status: Mapped[RouteStatusEnum] = mapped_column(enum_column(RouteStatusEnum), default=RouteStatusEnum.PLANNED)


class RouteStatusEvent(Base, UUIDPkMixin):
    __tablename__ = "route_status"

    route_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("routes.id"), index=True)
    status: Mapped[RouteStatusEnum] = mapped_column(enum_column(RouteStatusEnum))
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
