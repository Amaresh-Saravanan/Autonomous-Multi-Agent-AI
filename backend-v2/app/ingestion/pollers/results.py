"""Shared result shape for a single poll run, used by every source module
and the runner so `/poll/{source}` and `/poll/status` have one consistent
JSON-able shape to report."""

from dataclasses import dataclass


@dataclass
class PollResult:
    fetched: int
    ingested: int
    skipped_duplicate: int
    error: str | None
