"""Poll-source dedup. A Redis SET per source holding external ids already
ingested, so re-polling the same feed never creates a duplicate Event.
Client is constructor-injected (not `get_redis_client()` at call time) so
background/worker code -- outside FastAPI's DI graph -- is testable the
same way the API layer is: pass a fake client in, a real one at the
call site (`runner.get_default_runner()`).

# ponytail: the set has no TTL and grows for the process lifetime. Fine at
# this scale (USGS ids, GDACS event+episode ids, Open-Meteo per-point
# timestamps are a few hundred/day at most); add a TTL or periodic trim if
# a source's id space grows unbounded.
"""


def _key(source: str) -> str:
    return f"poller:dedup:{source}"


class DedupStore:
    def __init__(self, redis_client):
        self._redis = redis_client

    def already_seen(self, source: str, external_id: str) -> bool:
        """Check only -- does not mark. Callers mark via `mark_seen` only
        after a successful ingest, so a mid-ingest failure doesn't
        permanently lose the event (mark-before-success would)."""
        return bool(self._redis.sismember(_key(source), external_id))

    def mark_seen(self, source: str, external_id: str) -> None:
        self._redis.sadd(_key(source), external_id)
