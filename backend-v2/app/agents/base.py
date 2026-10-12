"""Uniform agent contract (Phase 14). Every agent is a `BaseAgent` with
`can_handle` / `execute` / `fallback` / `validate_result`; `run()` is the
template method the orchestrator actually calls. One agent raising never
crashes the pipeline — `run()` catches it and returns a DEGRADED
`AgentResult` instead (Phase 23: one agent's failure must not take down
the others)."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.errors import AgentExecutionError
from app.infrastructure.llm import LLMService
from app.models.agent import AgentStatusEnum
from app.models.incident import LocationStateEnum

logger = logging.getLogger("app.agents")


class AgentContext(BaseModel):
    """Everything an agent needs to reason, with location honesty baked in:
    `location_state` must be checked before `latitude`/`longitude` are
    treated as usable — UNKNOWN means exactly that, never a silently
    substituted coordinate (Phase 13)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    incident_id: str
    source_type: str | None = None
    severity: float = 0.0
    location_state: LocationStateEnum = LocationStateEnum.UNKNOWN
    latitude: float | None = None
    longitude: float | None = None
    events: list[dict] = Field(default_factory=list)
    evidence_event_ids: list[str] = Field(default_factory=list)
    blackboard: dict[str, Any] = Field(default_factory=dict)
    resources: dict[str, Any] = Field(default_factory=dict)
    llm: LLMService | None = None

    @property
    def location_known(self) -> bool:
        return self.location_state != LocationStateEnum.UNKNOWN and self.latitude is not None and self.longitude is not None


class AgentResult(BaseModel):
    agent_id: str
    incident_id: str
    status: AgentStatusEnum
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: float = 0.0
    confidence: float
    reasoning: str
    evidence: list[str]
    recommendations: list[dict] = Field(default_factory=list)
    fallback_used: bool = False
    errors: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class BaseAgent(ABC):
    id: str
    triggers: frozenset[str] = frozenset({"iot", "weather", "satellite"})

    def can_handle(self, context: AgentContext) -> bool:
        return context.source_type is None or context.source_type in self.triggers

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Do the agent's actual reasoning. May raise — `run()` catches it."""
        raise NotImplementedError

    def fallback(self, context: AgentContext, error: Exception) -> AgentResult:
        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.FAILED,
            confidence=0.0,
            reasoning=f"{self.id} failed: {error}",
            evidence=["agent-exception"],
            fallback_used=True,
            errors=[str(error)],
        )

    def validate_result(self, result: AgentResult) -> AgentResult:
        if not result.evidence:
            raise AgentExecutionError(f"{self.id} produced a result with no evidence")
        if not result.reasoning:
            raise AgentExecutionError(f"{self.id} produced a result with no reasoning")
        return result

    def location_unavailable_result(self, context: AgentContext, evidence: list[str]) -> AgentResult:
        """Phase 13: never substitute a fabricated coordinate for a
        distance-based recommendation. Report the gap explicitly instead."""
        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.DEGRADED,
            confidence=0.0,
            reasoning="Incident location is unavailable; cannot compute a distance-based recommendation.",
            evidence=evidence or ["location-unavailable"],
            recommendations=[{"action": "escalate:location_unavailable"}],
            fallback_used=True,
            metadata={"fallback_reason": "location_unavailable"},
        )

    def run(self, context: AgentContext) -> AgentResult:
        start = time.monotonic()
        try:
            result = self.execute(context)
            result = self.validate_result(result)
        except Exception as exc:  # noqa: BLE001 - this boundary is intentional
            logger.exception("%s raised during execute()", self.id)
            result = self.fallback(context, exc)
        result.execution_time_ms = (time.monotonic() - start) * 1000
        return result
