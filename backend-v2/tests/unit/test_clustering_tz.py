from datetime import datetime, timezone

from app.incidents.clustering import find_cluster_candidate
from app.models.incident import Incident


def test_naive_updated_at_from_sqlite_does_not_crash_and_still_clusters():
    incident = Incident(latitude=13.08, longitude=80.27)
    incident.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)  # what SQLite returns
    match = find_cluster_candidate(
        [incident], latitude=13.081, longitude=80.271, received_at=datetime.now(timezone.utc)
    )
    assert match is incident
