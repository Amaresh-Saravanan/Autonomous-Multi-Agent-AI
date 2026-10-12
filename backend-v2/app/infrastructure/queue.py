"""Ingestion queue (Phase 8). Decouples the HTTP request (validate →
normalize → persist → associate incident, all fast) from agent
orchestration (slow: LLM calls) so ingestion can return 202 immediately —
V1's problem #3 was running the whole agent chain inside the request.

`QUEUE_BACKEND=redis` is the production path (Redis list, BRPOP). `memory`
is a dev/test convenience (stdlib `queue.Queue`) — never the production
default (see `.env.example`). No backend silently falls back to another:
if `redis` is configured but unreachable, `enqueue`/`dequeue` raise
`QueueError` rather than quietly dropping to in-memory (that silent-
downgrade pattern was V1 blackboard problem #2)."""

import json
import queue as stdlib_queue
from functools import lru_cache

from app.config import get_settings
from app.errors import QueueError
from app.infrastructure.redis import RedisLike, get_redis_client

QUEUE_KEY = "ingestion:queue"


class QueueService:
    def __init__(self, backend: str, redis_client: RedisLike | None = None):
        if backend == "redis" and redis_client is None:
            raise QueueError("backend='redis' requires a redis_client")
        self.backend = backend
        self._redis = redis_client
        self._mem: stdlib_queue.Queue = stdlib_queue.Queue()

    def enqueue(self, payload: dict) -> None:
        if self.backend == "redis":
            try:
                self._redis.lpush(QUEUE_KEY, json.dumps(payload))
            except Exception as exc:
                raise QueueError(f"Failed to enqueue job: {exc}") from exc
        else:
            self._mem.put(payload)

    def dequeue(self, timeout: float = 1.0) -> dict | None:
        if self.backend == "redis":
            try:
                result = self._redis.brpop([QUEUE_KEY], timeout=timeout)
            except Exception as exc:
                raise QueueError(f"Failed to dequeue job: {exc}") from exc
            if result is None:
                return None
            _, raw = result
            return json.loads(raw)
        try:
            return self._mem.get(timeout=timeout)
        except stdlib_queue.Empty:
            return None


@lru_cache
def get_queue_service() -> QueueService:
    settings = get_settings()
    redis_client = get_redis_client() if settings.queue_backend == "redis" else None
    return QueueService(settings.queue_backend, redis_client)
