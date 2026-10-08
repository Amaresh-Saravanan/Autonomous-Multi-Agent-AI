"""Persistent IncidentService (Phase 10). Replaces V1's in-memory registry."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.incidents.clustering import find_cluster_candidate
from app.models.incident import Incident, IncidentStatusEnum, LocationStateEnum

OPEN_STATUSES = (
    IncidentStatusEnum.DETECTED,
    IncidentStatusEnum.ASSESSING,
    IncidentStatusEnum.ACTIVE,
    IncidentStatusEnum.CONTAINED,
)


class IncidentService:
    def __init__(self, db: Session):
        self.db = db

    def _open_incidents(self) -> list[Incident]:
        return list(self.db.scalars(select(Incident).where(Incident.status.in_(OPEN_STATUSES))))

    def create(
        self, *, latitude: float | None, longitude: float | None, location_state: LocationStateEnum
    ) -> Incident:
        incident = Incident(
            status=IncidentStatusEnum.DETECTED,
            location_state=location_state,
            latitude=latitude,
            longitude=longitude,
        )
        self.db.add(incident)
        self.db.commit()
        return incident

    def associate_event(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
        location_state: LocationStateEnum,
        received_at: datetime,
    ) -> Incident:
        """Find an open incident this event belongs to, or start a new one.
        An event with unknown/missing location cannot be clustered — it gets
        its own incident rather than silently joining an unrelated one."""
        if location_state == LocationStateEnum.UNKNOWN or latitude is None or longitude is None:
            return self.create(latitude=None, longitude=None, location_state=LocationStateEnum.UNKNOWN)

        candidate = find_cluster_candidate(
            self._open_incidents(), latitude=latitude, longitude=longitude, received_at=received_at
        )
        if candidate is not None:
            candidate.updated_at = received_at
            self.db.commit()
            return candidate
        return self.create(latitude=latitude, longitude=longitude, location_state=location_state)

    def get(self, incident_id: uuid.UUID) -> Incident:
        incident = self.db.get(Incident, incident_id)
        if incident is None:
            raise NotFoundError(f"Incident {incident_id} not found")
        return incident

    def list_all(self) -> list[Incident]:
        return list(self.db.scalars(select(Incident).order_by(Incident.updated_at.desc())))

    def update_severity(self, incident_id: uuid.UUID, severity: float) -> Incident:
        incident = self.get(incident_id)
        incident.severity = severity
        if incident.status == IncidentStatusEnum.DETECTED:
            incident.status = IncidentStatusEnum.ASSESSING
        self.db.commit()
        return incident

    def close(self, incident_id: uuid.UUID) -> Incident:
        incident = self.get(incident_id)
        incident.status = IncidentStatusEnum.CLOSED
        incident.closed_at = datetime.now(timezone.utc)
        self.db.commit()
        return incident

    def reopen(self, incident_id: uuid.UUID) -> Incident:
        incident = self.get(incident_id)
        incident.status = IncidentStatusEnum.ACTIVE
        incident.closed_at = None
        self.db.commit()
        return incident
