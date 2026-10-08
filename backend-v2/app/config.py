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

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
