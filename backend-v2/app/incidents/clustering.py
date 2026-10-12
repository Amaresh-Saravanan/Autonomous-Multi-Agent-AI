"""Incident clustering (Phase 10). Pure function over persisted candidates —
no network call on the hot path. V1 problem #5 was a hidden Nominatim
reverse-geocode call blocking ingestion in-request; V2 drops that
dependency from the clustering decision entirely (district enrichment, if
ever added, is a separate background step — DEFERRED, see
docs/BACKEND_V2_MIGRATION.md). Swappable for a PostGIS `ST_DWithin` query
later without changing the call site."""

from datetime import datetime, timedelta, timezone

from app.geo import distance_km
from app.models.incident import Incident

RADIUS_KM = 5.0
WINDOW = timedelta(hours=1)


def _aware(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes even for timezone=True columns
    (PostgreSQL returns aware ones). Everything we store is UTC, so treat a
    naive value as UTC instead of crashing the comparison."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def find_cluster_candidate(
    open_incidents: list[Incident], *, latitude: float, longitude: float, received_at: datetime
) -> Incident | None:
    """Best-matching open incident within RADIUS_KM and WINDOW of its last
    update, or None if the event should start a new incident."""
    best: Incident | None = None
    best_distance = RADIUS_KM
    for incident in open_incidents:
        if incident.latitude is None or incident.longitude is None:
            continue
        if _aware(received_at) - _aware(incident.updated_at) > WINDOW:
            continue
        d = distance_km(longitude, latitude, incident.longitude, incident.latitude)
        if d <= best_distance:
            best, best_distance = incident, d
    return best
