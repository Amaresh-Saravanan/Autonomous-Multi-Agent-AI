"""Poller runner: wires the three source modules to real infra (DB
session, queue, blackboard, Redis dedup, HTTP client) and runs them on a
background thread, mirroring `orchestration/graph.py`'s
`start_worker_thread`. Every dependency is constructor-injected on
`PollerRunner` -- tests build one with fakes; `get_default_runner()` is
the only place real singletons (`get_queue_service`, `get_redis_client`,
etc.) are wired, same split as the rest of the app's DI."""

import logging
import threading
from datetime import datetime, timezone
from functools import lru_cache

import httpx

from app.config import get_settings
from app.infrastructure.database import session_scope
from app.infrastructure.queue import QueueService, get_queue_service
from app.infrastructure.redis import get_redis_client
from app.ingestion.pollers import gdacs, open_meteo, usgs
from app.ingestion.pollers.dedup import DedupStore
from app.ingestion.pollers.results import PollResult
from app.ingestion.pollers.status import StatusStore
from app.ingestion.service import IngestionService
from app.orchestration.state import BlackboardService, get_blackboard_service

logger = logging.getLogger("app.pollers")

SOURCES = ("open_meteo", "usgs", "gdacs")


class PollerRunner:
    def __init__(
        self,
        *,
        session_factory,
        queue: QueueService,
        blackboard: BlackboardService,
        dedup: DedupStore,
        http_client: httpx.Client,
        points: list[tuple[str, float, float]],
        bbox: tuple[float, float, float, float],
        min_magnitude: float,
        status: StatusStore | None = None,
    ):
        self.session_factory = session_factory
        self.queue = queue
        self.blackboard = blackboard
        self.dedup = dedup
        self.http_client = http_client
        self.points = points
        self.bbox = bbox
        self.min_magnitude = min_magnitude
        self.status = status or StatusStore()

    def run_once(self, source: str) -> PollResult:
        """Runs one source's poll. Never raises: a failure is logged and
        recorded in status instead of propagating to the caller, so the
        background loop and the manual-trigger endpoint both stay up no
        matter what one source does."""
        run_at = datetime.now(timezone.utc)
        try:
            with self.session_factory() as db:
                def ingest(source_type: str, schema_obj):
                    return IngestionService(db, self.queue, self.blackboard).ingest(source_type, schema_obj)

                if source == "open_meteo":
                    result = open_meteo.poll(points=self.points, client=self.http_client, ingest=ingest, dedup=self.dedup)
                elif source == "usgs":
                    result = usgs.poll(
                        bbox=self.bbox,
                        min_magnitude=self.min_magnitude,
                        client=self.http_client,
                        ingest=ingest,
                        dedup=self.dedup,
                    )
                elif source == "gdacs":
                    result = gdacs.poll(client=self.http_client, ingest=ingest, dedup=self.dedup)
                else:
                    raise ValueError(f"Unknown poll source: {source!r}")
        except Exception as exc:  # noqa: BLE001 - this boundary is intentional
            logger.exception("poller %s failed", source)
            self.status.record_failure(source, error=str(exc), run_at=run_at)
            return PollResult(fetched=0, ingested=0, skipped_duplicate=0, error=str(exc))

        if result.error:
            self.status.record_failure(source, error=result.error, run_at=run_at)
        else:
            self.status.record_success(source, count=result.ingested, run_at=run_at)
        return result

    def run_all(self) -> dict[str, PollResult]:
        return {source: self.run_once(source) for source in SOURCES}


@lru_cache
def get_default_runner() -> PollerRunner:
    """Real-infra singleton: used by both the background thread and the
    manual-trigger/status endpoints, so they share one status store."""
    settings = get_settings()
    redis_client = get_redis_client() if settings.queue_backend == "redis" else None
    return PollerRunner(
        session_factory=session_scope,
        queue=get_queue_service(),
        blackboard=get_blackboard_service(),
        dedup=DedupStore(settings.queue_backend, redis_client),
        http_client=httpx.Client(timeout=10.0),
        points=settings.poller_points_list,
        bbox=settings.poller_bbox_tuple,
        min_magnitude=settings.poller_min_magnitude,
    )


def _loop(runner: PollerRunner, interval_seconds: int, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        for source in SOURCES:
            if stop_event.is_set():
                break
            runner.run_once(source)
        stop_event.wait(timeout=interval_seconds)


def start_poller_thread() -> threading.Event:
    """No-op (returns an already-set event) if POLLERS_ENABLED is false --
    callers can unconditionally call `stop_event.set()` at shutdown either
    way."""
    settings = get_settings()
    stop_event = threading.Event()
    if not settings.pollers_enabled:
        stop_event.set()
        return stop_event
    threading.Thread(
        target=_loop, args=(get_default_runner(), settings.poll_interval_seconds, stop_event), daemon=True
    ).start()
    return stop_event
