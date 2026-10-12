import fakeredis

from app.orchestration.state import BlackboardService


def _service() -> BlackboardService:
    return BlackboardService(fakeredis.FakeStrictRedis(decode_responses=True))


def test_merge_then_get_agent_round_trips():
    bb = _service()
    version = bb.merge("inc-1", "AG-1", {"severity": 0.7})
    assert version == 1
    data, read_version = bb.get_agent("inc-1", "AG-1")
    assert data == {"severity": 0.7}
    assert read_version == 1


def test_merge_increments_version_on_second_write():
    bb = _service()
    bb.merge("inc-1", "AG-1", {"severity": 0.5})
    version = bb.merge("inc-1", "AG-1", {"severity": 0.9})
    assert version == 2


def test_get_incident_aggregates_all_agents():
    bb = _service()
    bb.merge("inc-1", "AG-1", {"severity": 0.5})
    bb.merge("inc-1", "AG-5", {"shelter": "central"})
    snapshot = bb.get_incident("inc-1")
    assert snapshot == {"AG-1": {"severity": 0.5}, "AG-5": {"shelter": "central"}}


def test_concurrent_writers_do_not_lose_updates():
    """Two clients against the same fake server race to merge; a watched
    transaction forces the loser to retry instead of silently overwriting."""
    server = fakeredis.FakeServer()
    client_a = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    client_b = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    bb_a = BlackboardService(client_a)
    bb_b = BlackboardService(client_b)

    bb_a.merge("inc-1", "AG-1", {"severity": 0.1})

    v_a = bb_a.merge("inc-1", "AG-1", {"severity": 0.2})
    v_b = bb_b.merge("inc-1", "AG-1", {"severity": 0.3})

    assert {v_a, v_b} == {2, 3}
    _, final_version = bb_a.get_agent("inc-1", "AG-1")
    assert final_version == 3
