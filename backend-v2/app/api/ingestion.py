"""Ingestion endpoints (Phase 8). Device-authenticated; never publicly
writable (fixes V1 problems #10/#11 — open ingest and open citizen chat).
Each endpoint returns 202 immediately; the agent chain runs out-of-request
via the queue (Phase 16 worker).

The /poll/* routes below are admin-only operational controls for the
background data pollers (app/ingestion/pollers/), not device-authenticated
ingestion -- they trigger/inspect polling, they don't submit events."""

import dataclasses

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.queue import QueueService, get_queue_service
from app.ingestion.pollers.runner import SOURCES, get_default_runner
from app.ingestion.schemas import CitizenReport, IngestAccepted, IoTEvent, SatelliteEvent, WeatherEvent
from app.ingestion.service import IngestionService
from app.models.security import Device, RoleEnum, User
from app.orchestration.state import BlackboardService, get_blackboard_service
from app.security.devices import require_device
from app.security.permissions import require_role

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


def _service(db: Session, queue: QueueService, blackboard: BlackboardService) -> IngestionService:
    return IngestionService(db, queue, blackboard)


@router.post("/iot", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_iot(
    body: IoTEvent,
    device: Device = Depends(require_device("iot")),
    db: Session = Depends(get_db),
    queue: QueueService = Depends(get_queue_service),
    blackboard: BlackboardService = Depends(get_blackboard_service),
) -> IngestAccepted:
    event = _service(db, queue, blackboard).ingest("iot", body)
    return IngestAccepted(event_id=str(event.id), incident_id=str(event.incident_id))


@router.post("/weather", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_weather(
    body: WeatherEvent,
    device: Device = Depends(require_device("weather")),
    db: Session = Depends(get_db),
    queue: QueueService = Depends(get_queue_service),
    blackboard: BlackboardService = Depends(get_blackboard_service),
) -> IngestAccepted:
    event = _service(db, queue, blackboard).ingest("weather", body)
    return IngestAccepted(event_id=str(event.id), incident_id=str(event.incident_id))


@router.post("/satellite", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_satellite(
    body: SatelliteEvent,
    device: Device = Depends(require_device("satellite")),
    db: Session = Depends(get_db),
    queue: QueueService = Depends(get_queue_service),
    blackboard: BlackboardService = Depends(get_blackboard_service),
) -> IngestAccepted:
    event = _service(db, queue, blackboard).ingest("satellite", body)
    return IngestAccepted(event_id=str(event.id), incident_id=str(event.incident_id))


@router.post("/citizen", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_citizen(
    body: CitizenReport,
    device: Device = Depends(require_device("citizen")),
    db: Session = Depends(get_db),
    queue: QueueService = Depends(get_queue_service),
    blackboard: BlackboardService = Depends(get_blackboard_service),
) -> IngestAccepted:
    event = _service(db, queue, blackboard).ingest("citizen", body)
    return IngestAccepted(event_id=str(event.id), incident_id=str(event.incident_id))


@router.post("/poll/{source}")
def trigger_poll(source: str, admin: User = Depends(require_role(RoleEnum.ADMIN))) -> dict:
    if source not in SOURCES:
        raise HTTPException(status_code=400, detail=f"Unknown poll source '{source}'; valid: {SOURCES}")
    result = get_default_runner().run_once(source)
    return dataclasses.asdict(result)


@router.get("/poll/status")
def poll_status(admin: User = Depends(require_role(RoleEnum.ADMIN))) -> dict:
    status_store = get_default_runner().status
    return {
        source: {
            "last_run": entry.last_run.isoformat() if entry.last_run else None,
            "last_count": entry.last_count,
            "last_error": entry.last_error,
        }
        for source, entry in status_store.all().items()
    }
