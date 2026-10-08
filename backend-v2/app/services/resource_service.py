"""Resource snapshot + dev seed (Phase 10/15). Agents receive a plain-dict
snapshot built here from persisted tables — they never import the ORM or
query the DB directly (V1 problem #9). `seed_dev_resources` is a clearly
marked development seed, not a production data path (the synthetic V1
numbers survive only as documented fixtures, per the migration analysis'
DISCARD list)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resource import Hospital, RescueTeam, Resource, Shelter


def load_resource_snapshot(db: Session) -> dict:
    hospitals = db.scalars(select(Hospital)).all()
    shelters = db.scalars(select(Shelter)).all()
    teams = db.scalars(select(RescueTeam)).all()
    supplies_rows = db.scalars(select(Resource)).all()

    return {
        "hospitals": [
            {"id": str(h.id), "agency_id": str(h.agency_id), "name": h.name, "lat": h.latitude, "lon": h.longitude,
             "free_beds": h.beds_free, "beds_total": h.beds_total}
            for h in hospitals
        ],
        "shelters": [
            {"id": str(s.id), "agency_id": str(s.agency_id), "name": s.name, "lat": s.latitude, "lon": s.longitude,
             "capacity": s.capacity, "occupied": s.occupied}
            for s in shelters
        ],
        "teams": [
            {"id": str(t.id), "agency_id": str(t.agency_id), "name": t.name, "lat": t.latitude, "lon": t.longitude,
             "status": t.status.value}
            for t in teams
        ],
        "ambulances": [],
        "supplies": {r.category: r.quantity for r in supplies_rows},
    }


def seed_dev_resources(db: Session, agency_id) -> None:
    """ponytail: hardcoded synthetic coordinates, same as V1's resources.py.
    Fine for a dev/demo seed; never called from production startup paths."""
    db.add_all([
        Hospital(name="Coastal General", agency_id=agency_id, latitude=13.05, longitude=80.28, beds_total=120, beds_free=8),
        Hospital(name="City General", agency_id=agency_id, latitude=13.09, longitude=80.25, beds_total=200, beds_free=45),
        Shelter(name="Community Hall A", agency_id=agency_id, latitude=13.07, longitude=80.26, capacity=300, occupied=300),
        Shelter(name="School Ground B", agency_id=agency_id, latitude=13.04, longitude=80.29, capacity=500, occupied=120),
        RescueTeam(name="Rescue Team Alpha", agency_id=agency_id, latitude=13.06, longitude=80.27),
        RescueTeam(name="Rescue Team Bravo", agency_id=agency_id, latitude=13.10, longitude=80.24),
        Resource(name="Food units", category="food_units", agency_id=agency_id, quantity=5000, unit="unit"),
        Resource(name="Water", category="water_liters", agency_id=agency_id, quantity=20000, unit="liters"),
        Resource(name="Blankets", category="blankets", agency_id=agency_id, quantity=1500, unit="unit"),
    ])
    db.commit()
