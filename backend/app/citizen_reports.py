"""In-memory citizen report store (PRD UI-4). Mirrors app/recommendations.py's
pattern -- no DB needed to run. normalize_citizen already computes a
trust/confidence score per report (app/citizen_verification.py); this just
keeps it so it can be listed instead of thrown away after the ingest response.
"""
from __future__ import annotations

_reports: dict[str, dict] = {}


def record(report: dict) -> None:
    _reports[report["event_id"]] = report


def list_reports(incident_id: str | None = None) -> list[dict]:
    reports = list(_reports.values())
    if incident_id:
        reports = [r for r in reports if r["incident_id"] == incident_id]
    return sorted(reports, key=lambda r: r["timestamp"], reverse=True)
