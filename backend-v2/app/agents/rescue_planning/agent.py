"""AG-3 Rescue Planning (Phase 15). Nearest-available-team dispatch over
persisted resources passed in via `context.resources["teams"]` — no direct
DB/registry import (V1 problem #9) and no hardcoded fallback coordinate
when the incident's location is unknown (Phase 13)."""

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.geo import distance_km
from app.models.agent import AgentStatusEnum


class RescuePlanningAgent(BaseAgent):
    id = "AG-3"
    triggers = frozenset({"iot"})

    def execute(self, context: AgentContext) -> AgentResult:
        ag1 = context.blackboard.get("AG-1", {})
        ag2 = context.blackboard.get("AG-2", {})
        severity = ag1.get("severity", context.severity)
        evidence = (ag1.get("evidence", []) + ag2.get("evidence", [])) or context.evidence_event_ids or ["no-evidence"]

        if not context.location_known:
            return self.location_unavailable_result(context, evidence)

        lat, lon = context.latitude, context.longitude
        available = [t for t in context.resources.get("teams", []) if t["status"] == "available"]
        priority = "critical" if severity >= 0.85 else "high" if severity >= 0.5 else "routine"
        affected = ag2.get("details", {}).get("affected_population", "unknown")

        if not available:
            action = "escalate:no_teams_available"
            reasoning = f"[{priority}] No rescue teams available; escalate to mutual aid."
            confidence, details = 0.4, {}
        else:
            nearest = min(available, key=lambda t: distance_km(lon, lat, t["lon"], t["lat"]))
            dist = distance_km(lon, lat, nearest["lon"], nearest["lat"])
            action = f"dispatch:{nearest['id']}"
            reasoning = (
                f"[{priority}] severity {severity:.2f}, est. {affected} affected. "
                f"Nearest available team: {nearest['name']} ({dist:.1f}km)."
            )
            confidence, details = 0.8, {"assigned_team": nearest, "priority": priority, "distance_km": dist}

        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.SUCCESS,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            recommendations=[{"action": action, "details": details}],
        )
