"""Ingestion pipeline (Phase 8): validation already happened in FastAPI via
the Pydantic schema; this is normalize → persist Event → associate incident
→ enqueue. Everything here is fast DB work with no LLM/agent call, so the
API layer can return 202 immediately and the queue consumer (Phase 16) does
the slow part."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.incidents.service import IncidentService
from app.infrastructure.queue import QueueService
from app.ingestion.normalizers.citizen import normalize_citizen, score_confidence
from app.ingestion.normalizers.iot import normalize_iot
from app.ingestion.normalizers.satellite import normalize_satellite
from app.ingestion.normalizers.weather import normalize_weather
from app.ingestion.schemas import CitizenReport, IoTEvent, SatelliteEvent, WeatherEvent
from app.models.citizen import CitizenReport as CitizenReportModel
from app.models.incident import Event
from app.orchestration.state import BlackboardService

NORMALIZERS = {
    "iot": normalize_iot,
    "weather": normalize_weather,
    "satellite": normalize_satellite,
}


class IngestionService:
    def __init__(self, db: Session, queue: QueueService, blackboard: BlackboardService):
        self.db = db
        self.queue = queue
        self.blackboard = blackboard
        self.incidents = IncidentService(db)

    def ingest(self, source_type: str, data) -> Event:
        if source_type == "citizen":
            return self._ingest_citizen(data)
        return self._ingest_sensor(source_type, data)

    def _ingest_sensor(self, source_type: str, data: IoTEvent | WeatherEvent | SatelliteEvent) -> Event:
        normalized = NORMALIZERS[source_type](data)
        received_at = datetime.now(timezone.utc)

        incident = self.incidents.associate_event(
            latitude=normalized["latitude"],
            longitude=normalized["longitude"],
            location_state=normalized["location_state"],
            received_at=received_at,
        )

        event = Event(
            incident_id=incident.id,
            source_type=normalized["source_type"],
            payload=normalized["payload"],
            location_state=normalized["location_state"],
            latitude=normalized["latitude"],
            longitude=normalized["longitude"],
            received_at=received_at,
        )
        self.db.add(event)
        self.db.commit()

        self.queue.enqueue({"event_id": str(event.id), "incident_id": str(incident.id), "source_type": source_type})
        return event

    def _ingest_citizen(self, data: CitizenReport) -> Event:
        normalized = normalize_citizen(data)
        received_at = datetime.now(timezone.utc)

        if data.incident_id:
            incident = self.incidents.get(data.incident_id)
        else:
            incident = self.incidents.associate_event(
                latitude=normalized["latitude"],
                longitude=normalized["longitude"],
                location_state=normalized["location_state"],
                received_at=received_at,
            )

        blackboard_state = self.blackboard.get_incident(str(incident.id))
        confidence, flagged = score_confidence(data.claimed_severity, blackboard_state)

        event = Event(
            incident_id=incident.id,
            source_type="citizen",
            payload={**normalized["payload"], "flagged_for_review": flagged},
            location_state=normalized["location_state"],
            latitude=normalized["latitude"],
            longitude=normalized["longitude"],
            received_at=received_at,
        )
        self.db.add(event)
        self.db.flush()

        self.db.add(
            CitizenReportModel(
                incident_id=incident.id,
                reporter_contact=data.reporter_contact,
                message=data.message,
                location_state=normalized["location_state"],
                latitude=normalized["latitude"],
                longitude=normalized["longitude"],
                verification_score=confidence,
                source="app",
            )
        )
        self.db.commit()

        # Does NOT enqueue: a citizen report scores trust against the
        # incident's current state but never itself wakes the agent chain
        # (V1 design, preserved — see normalizers/citizen.py docstring).
        return event
