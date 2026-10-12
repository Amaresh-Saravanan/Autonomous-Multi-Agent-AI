import uuid

import fakeredis

from app.models.alert import AlertStatusEnum
from app.models.incident import Incident
from app.models.security import Agency, RoleEnum
from app.services.alert_service import list_for_user, publish_if_worthy


class _FakeUser:
    def __init__(self, role, agency_id):
        self.role = role
        self.agency_id = agency_id


def _incident_id(db):
    """A real incident row: PostgreSQL enforces the alerts.incident_id FK (SQLite does not)."""
    inc = Incident(severity=0.9)
    db.add(inc)
    db.commit()
    return inc.id


def test_below_threshold_is_not_alert_worthy(db):
    alert = publish_if_worthy(
        db, incident_id=uuid.uuid4(), agent_id="AG-1", action="monitor", severity=0.1,
        target_agency_id=None, redis_client=fakeredis.FakeStrictRedis(),
    )
    assert alert is None


def test_duplicate_alert_is_suppressed_not_silently_dropped(db):
    incident_id = _incident_id(db)
    client = fakeredis.FakeStrictRedis()
    first = publish_if_worthy(
        db, incident_id=incident_id, agent_id="AG-1", action="raise_severity", severity=0.9,
        target_agency_id=None, redis_client=client,
    )
    second = publish_if_worthy(
        db, incident_id=incident_id, agent_id="AG-1", action="raise_severity", severity=0.9,
        target_agency_id=None, redis_client=client,
    )
    assert first.status == AlertStatusEnum.PUBLISHED
    assert second.status == AlertStatusEnum.SUPPRESSED
    assert second.id != first.id  # row still written, never dropped with no trace


def test_list_for_user_filters_by_agency(db):
    agency_a = Agency(name="A", code="A1")
    agency_b = Agency(name="B", code="B1")
    db.add_all([agency_a, agency_b])
    db.commit()

    publish_if_worthy(db, incident_id=_incident_id(db), agent_id="AG-1", action="x", severity=0.9,
                       target_agency_id=agency_a.id, redis_client=fakeredis.FakeStrictRedis())
    publish_if_worthy(db, incident_id=_incident_id(db), agent_id="AG-1", action="y", severity=0.9,
                       target_agency_id=agency_b.id, redis_client=fakeredis.FakeStrictRedis())

    viewer_a = _FakeUser(RoleEnum.VIEWER, agency_a.id)
    visible = list_for_user(db, viewer_a)
    assert len(visible) == 1
    assert visible[0].target_agency_id == agency_a.id
