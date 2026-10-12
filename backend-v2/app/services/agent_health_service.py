"""AgentHealthService (Phase 23). Tracks per-agent run history so one
agent's failures are visible without crashing the pipeline — `execution.py`
calls `record_run` after every agent invocation, success or not."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.base import AgentResult
from app.models.agent import AgentHealth, AgentRun, AgentStatusEnum
from app.observability.metrics import AGENT_FALLBACKS, AGENT_LATENCY

FAILURE_STATUSES = {AgentStatusEnum.FAILED, AgentStatusEnum.TIMEOUT, AgentStatusEnum.DEGRADED}
DEGRADED_STREAK_THRESHOLD = 3


def record_run(db: Session, incident_id, event_id, result: AgentResult) -> AgentHealth:
    AGENT_LATENCY.labels(agent_id=result.agent_id).observe(result.execution_time_ms / 1000)
    if result.fallback_used:
        AGENT_FALLBACKS.labels(agent_id=result.agent_id).inc()

    db.add(
        AgentRun(
            agent_id=result.agent_id,
            incident_id=incident_id,
            event_id=event_id,
            status=result.status,
            confidence=result.confidence,
            execution_time_ms=result.execution_time_ms,
            fallback_used=result.fallback_used,
            error=result.errors[0] if result.errors else None,
            created_at=result.timestamp,
        )
    )

    health = db.query(AgentHealth).filter(AgentHealth.agent_id == result.agent_id).one_or_none()
    if health is None:
        # Explicit zeros: SQLAlchemy `default=` only applies at flush, not at
        # construction, and we mutate these fields before any flush happens.
        health = AgentHealth(
            agent_id=result.agent_id,
            execution_count=0,
            success_count=0,
            failure_count=0,
            average_latency_ms=0.0,
            degraded_mode=False,
        )
        db.add(health)

    is_failure = result.status in FAILURE_STATUSES
    health.execution_count += 1
    health.success_count += 0 if is_failure else 1
    health.failure_count += 1 if is_failure else 0
    total = health.execution_count
    health.average_latency_ms = ((health.average_latency_ms * (total - 1)) + result.execution_time_ms) / total
    health.last_run = datetime.now(timezone.utc)
    health.status = result.status
    if is_failure:
        health.last_error = result.errors[0] if result.errors else result.reasoning
    # ponytail: degraded_mode flips on after a short consecutive-failure
    # streak proxy (recent failure rate), not a separate rolling window —
    # upgrade to real windowed tracking if false positives show up.
    recent_failure_rate = health.failure_count / max(health.execution_count, 1)
    health.degraded_mode = is_failure and recent_failure_rate > 0.5

    db.commit()
    return health
