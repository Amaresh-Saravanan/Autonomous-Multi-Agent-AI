"""AG-4 Medical Coordination (Phase 15)."""

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.geo import distance_km
from app.models.agent import AgentStatusEnum


class MedicalCoordinationAgent(BaseAgent):
    id = "AG-4"
    triggers = frozenset({"iot"})

    def execute(self, context: AgentContext) -> AgentResult:
        ag1 = context.blackboard.get("AG-1", {})
        ag2 = context.blackboard.get("AG-2", {})
        severity = ag1.get("severity", context.severity)
        evidence = (ag1.get("evidence", []) + ag2.get("evidence", [])) or context.evidence_event_ids or ["no-evidence"]

        if not context.location_known:
            return self.location_unavailable_result(context, evidence)

        lat, lon = context.latitude, context.longitude
        affected = ag2.get("details", {}).get("affected_population", 0) or 0
        casualty_estimate = round(affected * 0.02)  # heuristic: 2% of affected need medical care

        candidates = [h for h in context.resources.get("hospitals", []) if h["free_beds"] > 0]
        avail_amb = [a for a in context.resources.get("ambulances", []) if a["status"] == "available"]

        if not candidates:
            action = "escalate:no_hospital_capacity"
            reasoning = f"Est. {casualty_estimate} casualties; no hospital has free beds. Escalate to neighboring region."
            confidence, details = 0.4, {}
        else:
            best = min(
                candidates,
                key=lambda h: (
                    -h["free_beds"] if h["free_beds"] >= casualty_estimate else 0,
                    distance_km(lon, lat, h["lon"], h["lat"]),
                ),
            )
            amb = min(avail_amb, key=lambda a: distance_km(lon, lat, a["lon"], a["lat"])) if avail_amb else None
            action = f"allocate:{best['id']}"
            reasoning = (
                f"Est. {casualty_estimate} casualties. Allocate to {best['name']} ({best['free_beds']} free beds)."
                + (f" Dispatch ambulance {amb['id']}." if amb else " No ambulance available.")
            )
            confidence = 0.75
            details = {"hospital": best, "ambulance": amb, "casualty_estimate": casualty_estimate}

        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.SUCCESS,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            recommendations=[{"action": action, "details": details}],
        )
