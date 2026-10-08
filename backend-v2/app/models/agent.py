"""agent_runs / agent_health (Phases 2, 14, 23)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin, enum_column


class AgentStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    DEGRADED = "DEGRADED"
    SKIPPED = "SKIPPED"
    FALLBACK = "FALLBACK"


class AgentRun(Base, UUIDPkMixin):
    __tablename__ = "agent_runs"

    agent_id: Mapped[str] = mapped_column(String(50), index=True)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id"), nullable=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=True)
    status: Mapped[AgentStatusEnum] = mapped_column(enum_column(AgentStatusEnum))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(Float)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentHealth(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "agent_health"

    agent_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[AgentStatusEnum] = mapped_column(enum_column(AgentStatusEnum), default=AgentStatusEnum.PENDING)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    average_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    degraded_mode: Mapped[bool] = mapped_column(Boolean, default=False)
