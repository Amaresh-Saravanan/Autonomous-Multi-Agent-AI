from app import seed
from app.models.security import Agency, Device, RoleEnum, User


def test_seed_is_idempotent_and_creates_admin_and_devices(db, monkeypatch, capsys):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "root@eoc.gov")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "a-long-password")
    seed.run()
    seed.run()
    assert db.query(User).filter(User.email == "root@eoc.gov", User.role == RoleEnum.ADMIN).count() == 1
    assert db.query(Agency).count() == 2
    assert {d.source_type for d in db.query(Device)} == {"citizen", "iot"}
    out = capsys.readouterr().out
    assert "already exists" in out  # second run changed nothing


def test_dev_seed_includes_ambulances_in_snapshot(db):
    from app.models.security import Agency
    from app.services.resource_service import load_resource_snapshot, seed_dev_resources

    ag = Agency(name="A", code="A1")
    db.add(ag)
    db.commit()
    seed_dev_resources(db, ag.id)
    snap = load_resource_snapshot(db)
    assert len(snap["ambulances"]) == 4
    assert {a["status"] for a in snap["ambulances"]} == {"available"}
    hosp_ids = {h["id"] for h in snap["hospitals"]}
    assert {a["hospital_id"] for a in snap["ambulances"]} == hosp_ids
