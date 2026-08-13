"""Alert dedup/threshold engine (tracker 2.8) — see docs/superpowers/specs/2026-08-12-alert-engine-design.md"""
from app import alerts


def _rec(agent_id="AG-1", action="evacuate", severity=0.8):
    return {"agent_id": agent_id, "action": action, "severity": severity}


def test_first_high_severity_rec_pushes():
    alerts._last_pushed.clear()
    assert alerts.should_push("inc-1", [_rec()]) is True


def test_identical_repeat_does_not_push():
    alerts._last_pushed.clear()
    alerts.should_push("inc-1", [_rec()])
    assert alerts.should_push("inc-1", [_rec()]) is False


def test_changed_severity_pushes_again():
    alerts._last_pushed.clear()
    alerts.should_push("inc-1", [_rec(severity=0.6)])
    assert alerts.should_push("inc-1", [_rec(severity=0.9)]) is True


def test_all_low_severity_batch_does_not_push():
    alerts._last_pushed.clear()
    assert alerts.should_push("inc-1", [_rec(severity=0.2)]) is False
