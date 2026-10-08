"""AG-6 Route Optimization (Phase 15). Delegates the actual route
calculation to `RoutingService` (`StraightLineFallback` today) — this
agent is just the nearest-shelter pick + evidence/rationale wrapper."""

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.geo import distance_km
from app.models.agent import AgentStatusEnum
from app.services.route_service import RoutingService


class RouteOptimizationAgent(BaseAgent):
    id = "AG-6"
    triggers = frozenset({"iot"})

    def __init__(self, routing_service: RoutingService | None = None):
        self._routing = routing_service or RoutingService()

    def execute(self, context: AgentContext) -> AgentResult:
        ag1 = context.blackboard.get("AG-1", {})
        severity = ag1.get("severity", context.severity)
        evidence = ag1.get("evidence", []) or context.evidence_event_ids or ["no-evidence"]

        if not context.location_known:
            return self.location_unavailable_result(context, evidence)

        lat, lon = context.latitude, context.longitude
        shelters = context.resources.get("shelters", [])
        if not shelters:
            return AgentResult(
                agent_id=self.id,
                incident_id=context.incident_id,
                status=AgentStatusEnum.DEGRADED,
                confidence=0.3,
                reasoning="No shelters registered; cannot compute a route.",
                evidence=evidence,
                recommendations=[{"action": "escalate:no_shelters_registered"}],
                fallback_used=True,
            )

        nearest = min(shelters, key=lambda s: distance_km(lon, lat, s["lon"], s["lat"]))
        route = self._routing.route(origin_lat=lat, origin_lon=lon, dest_lat=nearest["lat"], dest_lon=nearest["lon"])

        if route.blocked:
            action = "route:detour_required"
            reasoning = (
                f"Direct route to {nearest['name']} crosses a blocked segment "
                f"({route.blocked_reason}). Detour required — manual routing needed."
            )
            confidence = 0.5
        else:
            action = f"route:{nearest['id']}"
            reasoning = f"Clear route to {nearest['name']}, {route.distance_km:.1f}km, no known blockages."
            confidence = 0.75

        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.SUCCESS,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            recommendations=[{"action": action, "details": {"destination": nearest, **route.model_dump()}}],
            metadata={"provider": route.provider},
        )
