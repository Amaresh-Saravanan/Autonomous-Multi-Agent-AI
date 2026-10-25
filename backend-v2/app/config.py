"""Centralized configuration. All settings come from environment variables
(or `.env`); nothing here is a hardcoded secret, model name, or infra URL."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False

    database_url: str = "sqlite:///./v2_dev.db"
    # No in-process fallback scheme here on purpose (V1 problem #2 was a
    # silent memory downgrade on Redis outage) — `uvicorn app.main:app`
    # genuinely requires a reachable Redis; use QUEUE_BACKEND=memory only
    # in tests, never as a production default.
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str | None = None

    cors_origins: str = "http://localhost:3000"

    queue_backend: Literal["memory", "redis"] = "memory"

    routing_provider: Literal["fallback", "osrm"] = "fallback"
    osrm_url: str | None = None

    log_level: str = "INFO"

    map_provider: str = "leaflet"

    pollers_enabled: bool = False
    poll_interval_seconds: int = 300
    poller_min_magnitude: float = 2.5
    # "name:lat:lon,name:lat:lon,..." -- string, not list, so pydantic-settings
    # doesn't try to JSON-parse a plain CSV env var (see cors_origins above).
    poller_points: str = "Erode:11.341:77.7172,Chennai:13.0827:80.2707,Mumbai:19.0760:72.8777"
    # "min_lon,min_lat,max_lon,max_lat" -- same ordering as SatelliteEvent.area_bounds.
    poller_bbox: str = "68,6,98,38"

    @property
    def poller_points_list(self) -> list[tuple[str, float, float]]:
        points = []
        for entry in self.poller_points.split(","):
            if not entry.strip():
                continue
            name, lat, lon = entry.split(":")
            points.append((name.strip(), float(lat), float(lon)))
        return points

    @property
    def poller_bbox_tuple(self) -> tuple[float, float, float, float]:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in self.poller_bbox.split(","))
        return min_lon, min_lat, max_lon, max_lat

    @model_validator(mode="after")
    def _require_jwt_secret_outside_dev(self) -> "Settings":
        if self.jwt_secret:
            return self
        if self.app_env == "development":
            # ponytail: dev-only fallback so `uvicorn --reload` works with no .env;
            # raise instead of substituting a secret the moment APP_ENV != development.
            self.jwt_secret = "dev-only-insecure-secret-do-not-use-in-production"
            return self
        raise RuntimeError(
            "JWT_SECRET is required when APP_ENV is not 'development'. "
            "Refusing to start with no secret configured."
        )

    @model_validator(mode="after")
    def _require_strong_secret_in_production(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret and (
            len(self.jwt_secret) < 32 or "change-me" in self.jwt_secret.lower()
        ):
            raise RuntimeError(
                "JWT_SECRET must be at least 32 characters and not a placeholder when APP_ENV=production."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
