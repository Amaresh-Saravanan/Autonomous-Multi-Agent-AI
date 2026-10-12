from datetime import datetime, timedelta, timezone

from app.incidents.service import IncidentService
from app.models.incident import IncidentStatusEnum, LocationStateEnum


def test_first_event_creates_new_incident(db):
    svc = IncidentService(db)
    now = datetime.now(timezone.utc)
    incident = svc.associate_event(
        latitude=13.08, longitude=80.27, location_state=LocationStateEnum.EXACT, received_at=now
    )
    assert incident.status == IncidentStatusEnum.DETECTED
    assert incident.latitude == 13.08


def test_nearby_event_within_window_joins_same_incident(db):
    svc = IncidentService(db)
    t0 = datetime.now(timezone.utc)
    first = svc.associate_event(
        latitude=13.08, longitude=80.27, location_state=LocationStateEnum.EXACT, received_at=t0
    )
    second = svc.associate_event(
        latitude=13.081, longitude=80.271, location_state=LocationStateEnum.EXACT, received_at=t0 + timedelta(minutes=5)
    )
    assert second.id == first.id


def test_far_event_creates_separate_incident(db):
    svc = IncidentService(db)
    t0 = datetime.now(timezone.utc)
    first = svc.associate_event(
        latitude=13.08, longitude=80.27, location_state=LocationStateEnum.EXACT, received_at=t0
    )
    far = svc.associate_event(
        latitude=28.6, longitude=77.2, location_state=LocationStateEnum.EXACT, received_at=t0
    )
    assert far.id != first.id


def test_unknown_location_gets_its_own_incident(db):
    svc = IncidentService(db)
    now = datetime.now(timezone.utc)
    a = svc.associate_event(latitude=None, longitude=None, location_state=LocationStateEnum.UNKNOWN, received_at=now)
    b = svc.associate_event(latitude=None, longitude=None, location_state=LocationStateEnum.UNKNOWN, received_at=now)
    assert a.id != b.id
    assert a.location_state == LocationStateEnum.UNKNOWN


def test_close_and_reopen_lifecycle(db):
    svc = IncidentService(db)
    incident = svc.create(latitude=1.0, longitude=1.0, location_state=LocationStateEnum.EXACT)
    closed = svc.close(incident.id)
    assert closed.status == IncidentStatusEnum.CLOSED
    assert closed.closed_at is not None

    reopened = svc.reopen(incident.id)
    assert reopened.status == IncidentStatusEnum.ACTIVE
    assert reopened.closed_at is None


def test_closed_incident_not_a_cluster_candidate(db):
    svc = IncidentService(db)
    now = datetime.now(timezone.utc)
    incident = svc.associate_event(
        latitude=13.08, longitude=80.27, location_state=LocationStateEnum.EXACT, received_at=now
    )
    svc.close(incident.id)
    new = svc.associate_event(
        latitude=13.08, longitude=80.27, location_state=LocationStateEnum.EXACT, received_at=now
    )
    assert new.id != incident.id
