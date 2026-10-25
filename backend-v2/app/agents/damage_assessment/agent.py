"""AG-2 Damage Assessment (Phase 15). `DeterministicExposureEstimator` is a
population-density heuristic — NOT imagery-based damage detection. Every
result says so explicitly in `reasoning` and `metadata["method"]`; real
computer-vision damage assessment is DEFERRED (see
docs/archive/BACKEND_V2_MIGRATION.md)."""

import math

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.damage_assessment.schemas import DamageEstimate
from app.models.agent import AgentStatusEnum

POP_DENSITY_PER_KM2 = 4500
AFFECTED_RADIUS_KM = 2.0


class DeterministicExposureEstimator:
    """ponytail: fixed population-density constant, not real census/imagery
    data. Upgrade when real satellite change-detection (DEFERRED) lands."""

    def estimate(self, severity: float) -> DamageEstimate:
        area_km2 = math.pi * AFFECTED_RADIUS_KM**2
        return DamageEstimate(
            affected_population=round(severity * POP_DENSITY_PER_KM2 * area_km2 * 0.3),
            structures_damaged=round(severity * 40),
        )


class DamageAssessmentAgent(BaseAgent):
    id = "AG-2"
    triggers = frozenset({"iot", "satellite"})

    def __init__(self, estimator: DeterministicExposureEstimator | None = None):
        self._estimator = estimator or DeterministicExposureEstimator()

    def execute(self, context: AgentContext) -> AgentResult:
        ag1 = context.blackboard.get("AG-1", {})
        severity = ag1.get("severity", context.severity)
        estimate = self._estimator.estimate(severity)

        reasoning = (
            f"AG-1 severity {severity:.2f} within {AFFECTED_RADIUS_KM}km radius -> "
            f"est. {estimate.affected_population} people, {estimate.structures_damaged} structures affected "
            f"(population-density heuristic, NOT imagery change-detection)."
        )

        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.SUCCESS,
            confidence=0.55,
            reasoning=reasoning,
            evidence=ag1.get("evidence") or context.evidence_event_ids or ["no-evidence"],
            recommendations=[{"action": "estimate_damage", "details": estimate.model_dump()}],
            metadata={"method": estimate.method},
        )
