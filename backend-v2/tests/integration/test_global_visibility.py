"""Situation-level agents (AG-1/2/8) are explicitly global; everything else
stays agency-scoped and a NULL agency stays admin-only."""

import fakeredis
from fastapi.testclient import TestClient

from app.agents.base import AgentResult
from app.models.agent import AgentStatusEnum
from app.main import app
from app.models.recommendation import Recommendation
from app.models.security import Agency, RoleEnum, User
from app.recommendations import service as recs
from app.security.auth import hash_password
from app.services import alert_service

from tests.integration.test_console_api import _fake_blackboard, _incident, _login  # noqa: F401


def _result(agent_id):
    return AgentResult(
        agent_id=agent_id, incident_id="x", status=AgentStatusEnum.SUCCESS, confidence=0.9, reasoning="r",
        evidence=["e1"], recommendations=[{"action": "x", "severity": 0.9, "details": {}}],
    )


def test_global_agents_flagged_and_others_not(db):
    inc = _incident(db)
    assert recs.create_from_agent_result(db, inc.id, _result("AG-1")).is_global
    assert recs.create_from_agent_result(db, inc.id, _result("AG-8")).is_global
    assert not recs.create_from_agent_result(db, inc.id, _result("AG-3")).is_global


def test_operator_and_viewer_see_global_but_not_other_agency_or_null(db):
    client = TestClient(app)
    op_h, agency, _ = _login(client, db, RoleEnum.OPERATOR, "op@eoc.gov")
    other = Agency(name="Other", code="OTH")
    db.add(other)
    db.commit()
    inc = _incident(db)
    g = recs.create_from_agent_result(db, inc.id, _result("AG-8"))
    null_rec = recs.create_from_agent_result(db, inc.id, _result("AG-3"))  # NULL agency, not global
    foreign = recs.create_from_agent_result(db, inc.id, _result("AG-3"))
    foreign.target_agency_id = other.id
    db.commit()

    ids = {r["id"] for r in client.get("/api/v1/recommendations", headers=op_h).json()}
    assert str(g.id) in ids
    assert str(null_rec.id) not in ids and str(foreign.id) not in ids

    # Operator may decide a global rec; foreign one is still forbidden.
    assert client.post(f"/api/v1/recommendations/{g.id}/decide", headers=op_h, json={"decision": "approve"}).status_code == 200
    assert client.post(f"/api/v1/recommendations/{foreign.id}/decide", headers=op_h, json={"decision": "approve"}).status_code == 403


def test_viewer_sees_global_but_cannot_decide(db):
    client = TestClient(app)
    h, agency, _ = _login(client, db, RoleEnum.VIEWER, "v@eoc.gov")
    inc = _incident(db)
    g = recs.create_from_agent_result(db, inc.id, _result("AG-1"))
    assert [r["id"] for r in client.get("/api/v1/recommendations", headers=h).json()] == [str(g.id)]
    assert client.post(f"/api/v1/recommendations/{g.id}/decide", headers=h, json={"decision": "approve"}).status_code == 403


def test_global_alert_listed_and_published_on_global_channel(db):
    client = TestClient(app)
    h, agency, _ = _login(client, db, RoleEnum.OPERATOR, "op2@eoc.gov")
    inc = _incident(db)
    r = fakeredis.FakeRedis(decode_responses=True)
    ps = r.pubsub()
    ps.subscribe("alerts:global")
    alert = alert_service.publish_if_worthy(
        db, incident_id=inc.id, agent_id="AG-8", action="sitrep", severity=0.9,
        target_agency_id=None, is_global=True, redis_client=r,
    )
    assert alert.is_global
    ps.get_message()  # subscribe ack
    assert ps.get_message(timeout=1)["channel"] == "alerts:global"
    assert [a["id"] for a in client.get("/api/v1/alerts", headers=h).json()] == [str(alert.id)]
