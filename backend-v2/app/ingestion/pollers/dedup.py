"""Poll-source dedup. A set per source holding external ids already
ingested, so re-polling the same feed never creates a duplicate Event.

Same backend split as `QueueService` (app/infrastructure/queue.py):
`backend="redis"` uses a real Redis SET (production); `backend="memory"`
uses a plain in-process dict-of-sets, for local dev / tests where
QUEUE_BACKEND=memory and no Redis is running. Never silently falls back
from redis to memory on a connection failure -- that's the same
silent-downgrade pattern this app avoids everywhere else (blackboard,
queue); if backend="redis" is configured, a Redis outage is a visible
error, not a quiet switch to memory.

Client is constructor-injected (not `get_redis_client()` at call time) so
background/worker code -- outside FastAPI's DI graph -- is testable the
same way the API layer is: pass a fake client in, a real one at the
call site (`runner.get_default_runner()`).

# ponytail: the in-memory set has no size cap and the Redis set has no
# TTL; both grow for the process lifetime. Fine at this scale (USGS ids,
# GDACS event+episode ids, Open-Meteo per-point timestamps are a few
# hundred/day at most); add a TTL or periodic trim if a source's id space
# grows unbounded.
"""

from app.errors import QueueError


def _key(source: str) -> str:
    return f"poller:dedup:{source}"


class DedupStore:
    def __init__(self, backend: str, redis_client=None):
        if backend == "redis" and redis_client is None:
            raise QueueError("backend='redis' requires a redis_client")
        self.backend = backend
        self._redis = redis_client
        self._mem: dict[str, set[str]] = {}

    def already_seen(self, source: str, external_id: str) -> bool:
        """Check only -- does not mark. Callers mark via `mark_seen` only
        after a successful ingest, so a mid-ingest failure doesn't
        permanently lose the event (mark-before-success would)."""
        if self.backend == "redis":
            return bool(self._redis.sismember(_key(source), external_id))
        return external_id in self._mem.get(source, set())

    def mark_seen(self, source: str, external_id: str) -> None:
        if self.backend == "redis":
            self._redis.sadd(_key(source), external_id)
        else:
            self._mem.setdefault(source, set()).add(external_id)
