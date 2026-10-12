"""Incident read endpoints, plus the two views the console map/command room
need: per-agent blackboard state (with surfaced conflicts, PRD AC-4) and the
severity grid (PRD DS-1)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.geo import cell_id, cell_polygon
from app.incidents.forecast import METRIC, build_forecast
from app.incidents.schemas import IncidentResponse
from app.incidents.service import IncidentService
from app.infrastructure.database import get_db
from app.models.incident import Event
from app.models.security import RoleEnum
from app.orchestration.state import BlackboardService, get_blackboard_service
from app.recommendations.conflict import ConflictDetector
from app.security.permissions import require_role

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


def _event_counts(db: Session) -> dict[uuid.UUID, int]:
    rows = db.execute(select(Event.incident_id, func.count(Event.id)).group_by(Event.incident_id)).all()
    return {incident_id: count for incident_id, count in rows}


@router.get("", response_model=list[IncidentResponse])
def list_incidents(db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.VIEWER))) -> list[IncidentResponse]:
    counts = _event_counts(db)
    out = []
    for incident in IncidentService(db).list_all():
        item = IncidentResponse.model_validate(incident)
        item.event_count = counts.get(incident.id, 0)
        out.append(item)
    return out


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.VIEWER))
) -> IncidentResponse:
    incident = IncidentService(db).get(incident_id)
    item = IncidentResponse.model_validate(incident)
    item.event_count = _event_counts(db).get(incident.id, 0)
    return item


@router.get("/{incident_id}/state")
def get_incident_state(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    blackboard: BlackboardService = Depends(get_blackboard_service),
    user=Depends(require_role(RoleEnum.VIEWER)),
) -> dict:
    """Per-agent latest output (the shared blackboard, PRD AC-1) plus any
    conflicting agent recommendations (AC-4) — surfaced, never merged."""
    IncidentService(db).get(incident_id)  # 404 if unknown
    state = blackboard.get_incident(str(incident_id))
    conflicts = ConflictDetector().detect(state)
    return {
        **state,
        "conflicts": [
            {
                "agents": c.agents, "target": c.target, "values": c.values,
                "recs": [], "rationale": c.rationale, "category": c.category,
            }
            for c in conflicts
        ],
    }


@router.get("/{incident_id}/severity")
def get_incident_severity(
    incident_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.VIEWER))
) -> dict:
    """Severity heat-map as GeoJSON (PRD DS-1): one cell per distinct
    event location of the incident, at the incident's current severity.
    Events without a known location contribute nothing — no fabricated cell."""
    incident = IncidentService(db).get(incident_id)
    cells: set[str] = set()
    for lat, lon in db.execute(
        select(Event.latitude, Event.longitude).where(Event.incident_id == incident_id)
    ).all():
        if lat is not None and lon is not None:
            cells.add(cell_id(lat, lon))
    if not cells and incident.latitude is not None and incident.longitude is not None:
        cells.add(cell_id(incident.latitude, incident.longitude))
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": cell_polygon(cell)},
                "properties": {"severity": incident.severity, "updated_at": incident.updated_at.isoformat()},
            }
            for cell in sorted(cells)
        ],
    }


@router.get("/{incident_id}/forecast")
def get_incident_forecast(
    incident_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.VIEWER))
) -> dict:
    """Predictive impact (PRD DS-2): +1/+3/+6h water-level projection."""
    IncidentService(db).get(incident_id)
    rows = db.execute(
        select(Event.payload, Event.received_at).where(Event.incident_id == incident_id, Event.source_type == "iot")
    ).all()
    readings = [
        (str(p.get("sensor_id", "unknown")), at, p["reading"], str(p.get("unit") or ""))
        for p, at in rows
        if p.get("metric") == METRIC and isinstance(p.get("reading"), (int, float))
    ]
    return build_forecast(readings)
