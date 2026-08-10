"""DS-1 dynamic severity heat-map (tracker 1.5). In-memory grid, keyed by
incident_id -> cell_id -> severity. Cell = geo_utils.cell_id (geohash-lite).
"""
from __future__ import annotations
from datetime import datetime, timezone
from . import geo_utils

_grid: dict[str, dict[str, dict]] = {}


def update(incident_id: str, lat: float, lon: float, severity: float) -> None:
    cell = geo_utils.cell_id(lat, lon)
    cells = _grid.setdefault(incident_id, {})
    existing = cells.get(cell)
    if existing is None or severity >= existing["severity"]:
        cells[cell] = {
            "severity": severity,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


def as_geojson(incident_id: str) -> dict:
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": geo_utils.cell_polygon(cell)},
            "properties": {"severity": data["severity"], "updated_at": data["updated_at"]},
        }
        for cell, data in _grid.get(incident_id, {}).items()
    ]
    return {"type": "FeatureCollection", "features": features}
