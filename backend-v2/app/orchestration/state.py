"""Blackboard (Phase 11). Redis-backed shared state, replacing V1's
module-global dict. Keyed by incident; one hash field per agent. Updates use
optimistic concurrency (WATCH/MULTI) so two workers racing on the same
incident never silently lose one write — the loser retries against the
latest version, and `ConcurrencyError` is raised only if retries are
exhausted."""

import json
import time

from redis.exceptions import WatchError

from app.errors import ConcurrencyError
from app.infrastructure.redis import RedisLike

MAX_RETRIES = 10


def _key(incident_id: str) -> str:
    return f"blackboard:{incident_id}"


class BlackboardService:
    def __init__(self, redis_client: RedisLike):
        self._redis = redis_client

    def get_incident(self, incident_id: str) -> dict:
        """All agent-scoped entries for one incident."""
        raw = self._redis.hgetall(_key(incident_id))
        return {agent_id: json.loads(value)["data"] for agent_id, value in raw.items()}

    def get_agent(self, incident_id: str, agent_id: str) -> tuple[dict | None, int]:
        """One agent-scoped entry. Returns (data, version); (None, 0) if absent."""
        raw = self._redis.hget(_key(incident_id), agent_id)
        if raw is None:
            return None, 0
        decoded = json.loads(raw)
        return decoded["data"], decoded["version"]

    def merge(self, incident_id: str, agent_id: str, data: dict) -> int:
        """Compare-and-update one agent's state within an incident's
        blackboard. Returns the new version number."""
        key = _key(incident_id)
        for _ in range(MAX_RETRIES):
            with self._redis.pipeline() as pipe:
                pipe.watch(key)
                current_raw = pipe.hget(key, agent_id)
                current_version = json.loads(current_raw)["version"] if current_raw else 0
                new_version = current_version + 1
                payload = json.dumps(
                    {"data": data, "version": new_version, "updated_at": time.time()}
                )
                pipe.multi()
                pipe.hset(key, agent_id, payload)
                try:
                    pipe.execute()
                    return new_version
                except WatchError:
                    continue
        raise ConcurrencyError(
            f"Could not update blackboard for incident={incident_id} agent={agent_id} "
            f"after {MAX_RETRIES} attempts; another writer kept winning the race."
        )
