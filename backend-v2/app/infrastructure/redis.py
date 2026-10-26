"""Redis abstraction (Phase 3). Production always talks to real Redis via
`REDIS_URL`; there is no silent in-memory fallback on connection failure —
that was V1 problem #2 (a transient outage at boot permanently and silently
downgraded the whole process). Tests inject `fakeredis` explicitly through
`get_redis` dependency override — fakeredis never appears in the default
code path."""

from functools import lru_cache
from typing import Protocol

import redis

from app.config import get_settings


class RedisLike(Protocol):
    """Subset of the `redis.Redis` interface the app relies on. `fakeredis`
    implements the same interface, so it satisfies this protocol in tests."""

    def get(self, name: str) -> bytes | None: ...
    def set(self, name: str, value: str, ex: int | None = None) -> bool | None: ...
    def delete(self, *names: str) -> int: ...
    def publish(self, channel: str, message: str) -> int: ...
    def pubsub(self, **kwargs): ...


@lru_cache
def get_redis_client() -> RedisLike:
    """Real Redis client. Connection errors surface to the caller — they are
    not swallowed into an in-memory substitute."""
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)
