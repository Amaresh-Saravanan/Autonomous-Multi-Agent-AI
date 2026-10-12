import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.access import router as access_router
from app.api.alerts import router as alerts_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.citizen import router as citizen_router
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.ingestion import router as ingestion_router
from app.api.metrics import router as metrics_router
from app.api.recommendations import router as recommendations_router
from app.api.resources import router as resources_router
from app.api.websocket import router as websocket_router
from app.config import get_settings
from app.errors import register_exception_handlers
from app.infrastructure.redis import get_redis_client
from app.infrastructure.websocket import get_connection_manager, run_pubsub_bridge
from app.observability.logging import configure_logging
from app.observability.metrics import API_REQUEST_LATENCY
from app.orchestration.graph import start_worker_thread

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = start_worker_thread()
    pubsub_stop = asyncio.Event()
    pubsub_task = asyncio.create_task(
        run_pubsub_bridge(get_redis_client(), get_connection_manager(), pubsub_stop)
    )
    yield
    stop_event.set()
    pubsub_stop.set()
    await pubsub_task


app = FastAPI(title="Disaster Response Platform v2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(access_router)
app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(websocket_router)
app.include_router(incidents_router)
app.include_router(recommendations_router)
app.include_router(citizen_router)
app.include_router(alerts_router)
app.include_router(resources_router)
app.include_router(audit_router)
app.include_router(metrics_router)


@app.middleware("http")
async def record_api_latency(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    API_REQUEST_LATENCY.labels(path=request.url.path, method=request.method).observe(time.monotonic() - start)
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app_env": settings.app_env}
