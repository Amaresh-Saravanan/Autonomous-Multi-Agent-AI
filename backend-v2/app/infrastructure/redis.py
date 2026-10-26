"""Redis abstraction (Phase 3). Production (`QUEUE_BACKEND=redis`) always
talks to real Redis via `REDIS_URL`; there is no silent in-memory fallback
on connection failure — that was V1 problem #2 (a transient outage at boot
permanently and silently downgraded the whole process).

`QUEUE_BACKEND=memory` is the explicit dev/test opt-in: this factory then
returns a shared `fakeredis` instance instead, so the blackboard and the
pubsub bridge (which otherwise hard-require Redis, by design) work with no
real server running. This only triggers on the explicit memory setting, not
on a connection failure -- `QUEUE_BACKEND=redis` with Redis down still fails
loudly, same as before."""

import logging
from functools import lru_cache
from typing import Protocol

import fakeredis
import redis

from app.config import get_settings

logger = logging.getLogger("app.redis")


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
    """Real Redis client, or a shared fakeredis singleton when
    `QUEUE_BACKEND=memory` -- `@lru_cache` makes this one instance per
    process, so the worker thread, the blackboard, and the pubsub bridge
    all share the same in-memory store. Connection errors on the real-Redis
    path still surface to the caller; memory mode never falls back here."""
    settings = get_settings()
    if settings.queue_backend == "memory":
        logger.warning("Using in-memory (fakeredis) backend - dev only")
        return fakeredis.FakeStrictRedis(decode_responses=True)
    return redis.from_url(settings.redis_url, decode_responses=True)
