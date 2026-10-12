"""JSON operational summaries for the console (Agents page). Prometheus text
stays at /api/v1/health/metrics for scrapers; these are the same numbers in
a shape the UI can read directly."""

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models.agent import AgentHealth
from app.models.recommendation import Recommendation, RecommendationStatusEnum
from app.models.security import RoleEnum
from app.observability.metrics import API_REQUEST_LATENCY
from app.security.permissions import require_role

router = APIRouter(prefix="/api/v1", tags=["metrics"])


def _route_latency() -> dict[str, dict]:
    count: dict[str, float] = defaultdict(float)
    total: dict[str, float] = defaultdict(float)
    buckets: dict[str, dict[float, float]] = defaultdict(lambda: defaultdict(float))
    for metric in API_REQUEST_LATENCY.collect():
        for sample in metric.samples:
            path = sample.labels.get("path")
            if path is None:
                continue
            if sample.name.endswith("_count"):
                count[path] += sample.value
            elif sample.name.endswith("_sum"):
                total[path] += sample.value
            elif sample.name.endswith("_bucket"):
                le = float("inf") if sample.labels["le"] == "+Inf" else float(sample.labels["le"])
                buckets[path][le] += sample.value
    out = {}
    for path, n in count.items():
        if not n:
            continue
        p95 = next((le for le, c in sorted(buckets[path].items()) if c >= 0.95 * n), float("inf"))
        out[path] = {
            "count": int(n),
            "avg_latency_ms": total[path] / n * 1000,
            "p95_latency_ms": (p95 * 1000) if p95 != float("inf") else total[path] / n * 1000,
        }
    return out


@router.get("/metrics")
def metrics_summary(db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.OPERATOR))) -> dict:
    decided = db.scalar(
        select(func.count()).select_from(Recommendation).where(
            Recommendation.status.in_([
                RecommendationStatusEnum.APPROVED, RecommendationStatusEnum.REJECTED,
                RecommendationStatusEnum.OVERRIDDEN,
            ])
        )
    ) or 0
    approved = db.scalar(
        select(func.count()).select_from(Recommendation).where(
            Recommendation.status == RecommendationStatusEnum.APPROVED
        )
    ) or 0
    return {
        "routes": _route_latency(),
        "recommendation_acceptance_rate": (approved / decided) if decided else None,
    }


@router.get("/agents/health")
def agents_health(db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.VIEWER))) -> list[dict]:
    """Per-agent run health (PRD resilience: a failing agent is visible)."""
    return [
        {
            "agent_id": h.agent_id,
            "status": h.status.value,
            "last_run": h.last_run.isoformat() if h.last_run else None,
            "execution_count": h.execution_count,
            "failure_count": h.failure_count,
            "average_latency_ms": h.average_latency_ms,
            "degraded_mode": h.degraded_mode,
            "last_error": h.last_error,
        }
        for h in db.scalars(select(AgentHealth).order_by(AgentHealth.agent_id))
    ]
