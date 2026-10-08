"""Ingestion endpoints (Phase 8). Device-authenticated; never publicly
writable (fixes V1 problems #10/#11 — open ingest and open citizen chat).
Each endpoint returns 202 immediately; the agent chain runs out-of-request
via the queue (Phase 16 worker)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.queue import QueueService, get_queue_service
from app.ingestion.schemas import CitizenReport, IngestAccepted, IoTEvent, SatelliteEvent, WeatherEvent
from app.ingestion.service import IngestionService
from app.models.security import Device
from app.orchestration.state import BlackboardService, get_blackboard_service
from app.security.devices import require_device

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
    return IngestAccepted(event_id=str(event.id))


@router.post("/weather", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_weather(
    body: WeatherEvent,
    device: Device = Depends(require_device("weather")),
    db: Session = Depends(get_db),
    queue: QueueService = Depends(get_queue_service),
    blackboard: BlackboardService = Depends(get_blackboard_service),
) -> IngestAccepted:
    event = _service(db, queue, blackboard).ingest("weather", body)
    return IngestAccepted(event_id=str(event.id))


@router.post("/satellite", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_satellite(
    body: SatelliteEvent,
    device: Device = Depends(require_device("satellite")),
    db: Session = Depends(get_db),
    queue: QueueService = Depends(get_queue_service),
    blackboard: BlackboardService = Depends(get_blackboard_service),
) -> IngestAccepted:
    event = _service(db, queue, blackboard).ingest("satellite", body)
    return IngestAccepted(event_id=str(event.id))


@router.post("/citizen", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_citizen(
    body: CitizenReport,
    device: Device = Depends(require_device("citizen")),
    db: Session = Depends(get_db),
    queue: QueueService = Depends(get_queue_service),
    blackboard: BlackboardService = Depends(get_blackboard_service),
) -> IngestAccepted:
    event = _service(db, queue, blackboard).ingest("citizen", body)
    return IngestAccepted(event_id=str(event.id))
