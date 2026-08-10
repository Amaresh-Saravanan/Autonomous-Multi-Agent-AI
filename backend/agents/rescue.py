"""AG-3 Rescue Planning — ranks priority, assigns nearest available team."""
from __future__ import annotations
from app.models import Event, Recommendation, Geo
from app.resources import TEAMS
from app.geo_utils import distance_km
from .base import Agent


class RescuePlanningAgent(Agent):
    id = "AG-3"

    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        ag1 = state.get("AG-1", {})
        ag2 = state.get("AG-2", {})
        severity = ag1.get("severity", 0.0)
        coords = (ag1.get("geo") or {}).get("coordinates") or [80.27, 13.08]
        lon, lat = coords[0], coords[1]

        available = [t for t in TEAMS if t["status"] == "available"]
        priority = "critical" if severity >= 0.85 else "high" if severity >= 0.5 else "routine"
        affected = ag2.get("details", {}).get("affected_population", "unknown")

        if not available:
            action = "escalate:no_teams_available"
            rationale = f"[{priority}] No rescue teams available; escalate to mutual aid."
            confidence, details = 0.4, {}
        else:
            nearest = min(available, key=lambda t: distance_km(lon, lat, t["lon"], t["lat"]))
            dist = distance_km(lon, lat, nearest["lon"], nearest["lat"])
            action = f"dispatch:{nearest['id']}"
            rationale = (
                f"[{priority}] severity {severity:.2f}, est. {affected} affected. "
                f"Nearest available team: {nearest['name']} ({dist:.1f}km)."
            )
            confidence, details = 0.8, {"assigned_team": nearest, "priority": priority}

        rec = Recommendation(
            agent_id=self.id, incident_id=incident_id, action=action, severity=severity,
            evidence=(ag1.get("evidence", []) + ag2.get("evidence", [])) or ["no-evidence"],
            rationale=rationale, confidence=confidence,
            geo=Geo(type="Point", coordinates=[lon, lat]), details=details,
        )
        rec.validate_explainable()
        return rec
