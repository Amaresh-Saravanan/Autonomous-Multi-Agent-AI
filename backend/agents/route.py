"""AG-6 Route Optimization — straight-line route to nearest open shelter,
flagged if it crosses a known blocked segment. Real road-network routing
(OSRM) is Phase 3+; ponytail: straight-line + radius check is the honest ceiling.
"""
from __future__ import annotations
from app.models import Event, Recommendation, Geo
from app.resources import SHELTERS
from app.geo_utils import distance_km
from .base import Agent

BLOCKED_SEGMENTS = [{"lat": 13.06, "lon": 80.265, "radius_km": 0.5, "reason": "bridge collapse"}]


class RouteOptimizationAgent(Agent):
    id = "AG-6"
    # dispatch decisions need confirmed ground-truth signal, not a forecast/imagery alone.
    triggers = frozenset({"iot"})

    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        ag1 = state.get("AG-1", {})
        severity = ag1.get("severity", 0.0)
        coords = (ag1.get("geo") or {}).get("coordinates") or [80.27, 13.08]
        lon, lat = coords[0], coords[1]

        nearest = min(SHELTERS, key=lambda s: distance_km(lon, lat, s["lon"], s["lat"]))
        line = [[lon, lat], [nearest["lon"], nearest["lat"]]]

        blocked_hit = None
        for seg in BLOCKED_SEGMENTS:
            mid_lon, mid_lat = (lon + nearest["lon"]) / 2, (lat + nearest["lat"]) / 2
            if distance_km(mid_lon, mid_lat, seg["lon"], seg["lat"]) < seg["radius_km"]:
                blocked_hit = seg
                break

        if blocked_hit:
            action = "route:detour_required"
            rationale = (
                f"Direct route to {nearest['name']} crosses blocked segment "
                f"({blocked_hit['reason']}). Detour required — manual routing needed."
            )
            confidence = 0.5
        else:
            action = f"route:{nearest['id']}"
            dist = distance_km(lon, lat, nearest['lon'], nearest['lat'])
            rationale = f"Clear route to {nearest['name']}, {dist:.1f}km, no known blockages."
            confidence = 0.75

        rec = Recommendation(
            agent_id=self.id, incident_id=incident_id, action=action, severity=severity,
            evidence=ag1.get("evidence", []) or ["no-evidence"],
            rationale=rationale, confidence=confidence,
            geo=Geo(type="Point", coordinates=[lon, lat]),
            details={"route_line": line, "destination": nearest, "blocked": bool(blocked_hit)},
        )
        rec.validate_explainable()
        return rec
