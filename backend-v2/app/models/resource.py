"""resources / resource_allocations / shelters / hospitals / rescue_teams
(Phase 2; consumed by AG-3/4/5)."""

import enum
import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin, enum_column


class RescueTeamStatusEnum(str, enum.Enum):
    AVAILABLE = "available"
    DEPLOYED = "deployed"


class Shelter(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "shelters"

    name: Mapped[str] = mapped_column(String(200))
    agency_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agencies.id"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer)
    occupied: Mapped[int] = mapped_column(Integer, default=0)


class Hospital(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "hospitals"

    name: Mapped[str] = mapped_column(String(200))
    agency_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agencies.id"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    beds_total: Mapped[int] = mapped_column(Integer)
    beds_free: Mapped[int] = mapped_column(Integer)
    ambulances_total: Mapped[int] = mapped_column(Integer, default=0)
    ambulances_free: Mapped[int] = mapped_column(Integer, default=0)


class RescueTeam(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "rescue_teams"

    name: Mapped[str] = mapped_column(String(200))
    agency_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agencies.id"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[RescueTeamStatusEnum] = mapped_column(enum_column(RescueTeamStatusEnum), default=RescueTeamStatusEnum.AVAILABLE)


class Resource(Base, UUIDPkMixin, TimestampMixin):
    """Generic countable supply (water, food, medkits, ...)."""

    __tablename__ = "resources"

    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), index=True)
    agency_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agencies.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[str] = mapped_column(String(20), default="unit")


class ResourceAllocation(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "resource_allocations"
    __table_args__ = (Index("ix_resource_allocations_incident_id", "incident_id"),)

    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("resources.id"))
    incident_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    allocated_by: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="allocated")
