"""Alert dedup/threshold engine (tracker 2.8).

Gates the /ws/alerts broadcast only — recording (blackboard, recommendations,
severity grid) stays unconditional. See
docs/superpowers/specs/2026-08-12-alert-engine-design.md.
"""
from __future__ import annotations

THRESHOLD = 0.5  # matches the frontend Alerts panel's severity cutoff

_last_pushed: dict[str, dict] = {}  # f"{incident_id}:{agent_id}" -> {"action", "severity"}


def should_push(incident_id: str, recs: list[dict]) -> bool:
    any_new = False
    for rec in recs:
        # ponytail: below-threshold recs skip state updates entirely, so a rec that
        # dips below THRESHOLD then climbs back to its exact pre-dip value won't
        # re-push. Add per-rec staleness tracking if that gap matters in practice.
        if rec["severity"] < THRESHOLD:
            continue
        key = f"{incident_id}:{rec['agent_id']}"
        prev = _last_pushed.get(key)
        current = {"action": rec["action"], "severity": rec["severity"]}
        if prev != current:
            any_new = True
        _last_pushed[key] = current
    return any_new
