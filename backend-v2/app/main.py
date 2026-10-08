from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.ingestion import router as ingestion_router
from app.config import get_settings
from app.errors import register_exception_handlers
from app.orchestration.graph import start_worker_thread

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = start_worker_thread()
    yield
    stop_event.set()


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
app.include_router(ingestion_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app_env": settings.app_env}
