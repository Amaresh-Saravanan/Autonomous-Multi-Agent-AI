"""Per-source poll status: last run time, count ingested on that run, and
the last error (if any). In-memory and per-process -- consistent with this
app's existing "run one backend process" constraint (see
docs/archive/DEPLOYMENT.md), same as AgentHealthService's health rows are
per-incident DB state but this is cheap, read-mostly operational data with
no correctness requirement, so it doesn't need a DB table or Redis key."""

import threading
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PollStatus:
    last_run: datetime | None = None
    last_count: int = 0
    last_error: str | None = None


class StatusStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._status: dict[str, PollStatus] = {}

    def record_success(self, source: str, *, count: int, run_at: datetime) -> None:
        with self._lock:
            self._status[source] = PollStatus(last_run=run_at, last_count=count, last_error=None)

    def record_failure(self, source: str, *, error: str, run_at: datetime) -> None:
        with self._lock:
            self._status[source] = PollStatus(last_run=run_at, last_count=0, last_error=error)

    def get(self, source: str) -> PollStatus:
        with self._lock:
            return self._status.get(source, PollStatus())

    def all(self) -> dict[str, PollStatus]:
        with self._lock:
            return dict(self._status)
