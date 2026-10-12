"""RoutingService (Phase 15/16 AG-6). `StraightLineFallback` is the only
provider actually implemented — it is a straight line plus one hardcoded
blocked-segment radius check, exactly V1's ceiling, clearly labeled as
such. OSRM/Valhalla road-network routing is DEFERRED: `ROUTING_PROVIDER`
and `OSRM_URL` exist in config for when a real OSRM instance is available,
but no network call is made until that provider is implemented."""

from typing import Protocol

from pydantic import BaseModel

from app.geo import distance_km

# ponytail: one hardcoded blocked segment, same as V1. A real implementation
# would come from live hazard-zone data, not a constant.
BLOCKED_SEGMENTS = [{"lat": 13.06, "lon": 80.265, "radius_km": 0.5, "reason": "bridge collapse"}]


class RouteResult(BaseModel):
    provider: str
    distance_km: float
    geometry: list[list[float]]
    blocked: bool
    blocked_reason: str | None = None


class RouteProvider(Protocol):
    def route(self, *, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> RouteResult: ...


class StraightLineFallback:
    """NOT real road-network routing — a straight line between two points
    plus a check against one hardcoded blocked-segment radius."""

    def route(self, *, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> RouteResult:
        dist = distance_km(origin_lon, origin_lat, dest_lon, dest_lat)
        geometry = [[origin_lon, origin_lat], [dest_lon, dest_lat]]

        mid_lon, mid_lat = (origin_lon + dest_lon) / 2, (origin_lat + dest_lat) / 2
        for seg in BLOCKED_SEGMENTS:
            if distance_km(mid_lon, mid_lat, seg["lon"], seg["lat"]) < seg["radius_km"]:
                return RouteResult(
                    provider="straight_line_fallback", distance_km=dist, geometry=geometry,
                    blocked=True, blocked_reason=seg["reason"],
                )
        return RouteResult(provider="straight_line_fallback", distance_km=dist, geometry=geometry, blocked=False)


class RoutingService:
    def __init__(self, provider: RouteProvider | None = None):
        self._provider = provider or StraightLineFallback()

    def route(self, *, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> RouteResult:
        return self._provider.route(origin_lat=origin_lat, origin_lon=origin_lon, dest_lat=dest_lat, dest_lon=dest_lon)
