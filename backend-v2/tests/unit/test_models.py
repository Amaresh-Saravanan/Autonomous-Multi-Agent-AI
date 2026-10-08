import uuid

from app.models.incident import Incident, IncidentStatusEnum, LocationStateEnum
from app.models.security import Agency, RoleEnum, User


def test_schema_creates_and_round_trips(db):
    agency = Agency(name="Test Agency", code="TST")
    db.add(agency)
    db.commit()

    user = User(
        email="ops@example.com",
        hashed_password="x",
        role=RoleEnum.OPERATOR,
        agency_id=agency.id,
    )
    db.add(user)
    db.commit()

    assert isinstance(user.id, uuid.UUID)
    assert user.role == RoleEnum.OPERATOR


def test_incident_defaults_to_unknown_location(db):
    incident = Incident(status=IncidentStatusEnum.DETECTED)
    db.add(incident)
    db.commit()
    assert incident.location_state == LocationStateEnum.UNKNOWN
    assert incident.latitude is None
