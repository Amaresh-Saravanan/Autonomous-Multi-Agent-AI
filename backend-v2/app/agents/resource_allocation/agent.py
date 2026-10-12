"""AG-5 Resource Allocation (Phase 15). `ResourceAllocator` delegates to a
pluggable `AllocationStrategy`; `GreedyFallback` (nearest-shelter, ported
from V1) is the only strategy actually implemented. An OR-Tools VRP
optimizer is DEFERRED — `ortools` is not an installed/required dependency
here; the strategy slot exists so adding it later doesn't change callers."""

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.resource_allocation.schemas import AllocationPlan
from app.geo import distance_km
from app.models.agent import AgentStatusEnum

SUPPLIES_PER_PERSON = {"food_units": 3, "water_liters": 10, "blankets": 1}


class GreedyFallback:
    """ponytail: nearest-fit greedy, not a jointly-optimized VRP. Upgrade to
    ORToolsOptimizer when allocations must be optimized across multiple
    simultaneous incidents competing for the same shelters/supplies."""

    def allocate(self, *, lat: float, lon: float, affected: int, shelters: list[dict], supplies: dict) -> AllocationPlan:
        open_shelters = [s for s in shelters if s["capacity"] - s["occupied"] > 0]
        needed = {k: affected * v for k, v in SUPPLIES_PER_PERSON.items()}
        shortfalls = {k: max(0, needed[k] - supplies.get(k, 0)) for k in needed}

        if not open_shelters:
            return AllocationPlan(shelter=None, needed=needed, shortfalls=shortfalls)

        best = min(open_shelters, key=lambda s: distance_km(lon, lat, s["lon"], s["lat"]))
        return AllocationPlan(shelter=best, needed=needed, shortfalls=shortfalls)


class ResourceAllocationAgent(BaseAgent):
    id = "AG-5"
    triggers = frozenset({"iot"})

    def __init__(self, strategy=None):
        self._strategy = strategy or GreedyFallback()

    def execute(self, context: AgentContext) -> AgentResult:
        ag1 = context.blackboard.get("AG-1", {})
        ag2 = context.blackboard.get("AG-2", {})
        severity = ag1.get("severity", context.severity)
        evidence = (ag1.get("evidence", []) + ag2.get("evidence", [])) or context.evidence_event_ids or ["no-evidence"]

        if not context.location_known:
            return self.location_unavailable_result(context, evidence)

        lat, lon = context.latitude, context.longitude
        affected = ag2.get("details", {}).get("affected_population", 0) or 0
        plan = self._strategy.allocate(
            lat=lat,
            lon=lon,
            affected=affected,
            shelters=context.resources.get("shelters", []),
            supplies=context.resources.get("supplies", {}),
        )

        if plan.shelter is None:
            action = "escalate:no_shelter_capacity"
            reasoning = f"Est. {affected} affected; no shelter has free capacity."
            confidence = 0.4
        else:
            free = plan.shelter["capacity"] - plan.shelter["occupied"]
            action = f"allocate_shelter:{plan.shelter['id']}"
            reasoning = (
                f"Est. {affected} affected -> route to {plan.shelter['name']} ({free} free capacity). "
                f"Supplies needed: {plan.needed}."
            )
            if any(plan.shortfalls.values()):
                reasoning += f" SHORTFALL vs current stock: {plan.shortfalls} — request resupply."
            confidence = 0.7

        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.SUCCESS,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            recommendations=[{"action": action, "details": plan.model_dump()}],
            metadata={"strategy": type(self._strategy).__name__},
        )
