"""Geo helpers (ported from V1 `geo_utils.py`, consolidated per
docs/archive/BACKEND_V2_MIGRATION_ANALYSIS.md section 16.5: one small module instead
of scattered geo helpers). Straight-line distance only — real road routing
is AG-6's `RoutingService` job."""

import math

EARTH_RADIUS_KM = 6371.0


def distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ponytail: fixed-precision lat/lon binning = a geohash-like grid without
# pulling in an h3/geohash dependency for what's a one-line quantization.
GRID_PRECISION = 2  # 0.01 deg ~ 1.1km cell at the equator


def cell_id(lat: float, lon: float) -> str:
    return f"{round(lat, GRID_PRECISION)},{round(lon, GRID_PRECISION)}"


def cell_polygon(cell: str) -> list:
    lat_s, lon_s = cell.split(",")
    lat, lon = float(lat_s), float(lon_s)
    d = 10 ** -GRID_PRECISION / 2
    return [[
        [lon - d, lat - d], [lon + d, lat - d],
        [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d],
    ]]
