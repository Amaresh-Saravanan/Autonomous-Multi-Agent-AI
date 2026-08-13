"""Citizen report trust/verification heuristic (tracker 3.3, SEC-4).

Scores a citizen-claimed severity against the incident's current AG-1
severity. Pure function: caller fetches blackboard state, this module has
no dependency on app.blackboard (avoids circular import with normalizers.py).
"""
from __future__ import annotations

CORROBORATING_THRESHOLD = 0.2
DIVERGENT_THRESHOLD = 0.4
NEUTRAL_CONFIDENCE = 0.5
CORROBORATING_CONFIDENCE = 0.8
DIVERGENT_CONFIDENCE = 0.2


def score_confidence(
    incident_id: str, claimed_severity: float, blackboard_state: dict
) -> tuple[float, bool]:
    """Returns (confidence, flagged_for_review)."""
    ag1_severity = blackboard_state.get("AG-1", {}).get("severity")
    if ag1_severity is None:
        # First-ever report for this incident: nothing to corroborate against yet.
        return NEUTRAL_CONFIDENCE, False

    diff = abs(claimed_severity - ag1_severity)
    if diff <= CORROBORATING_THRESHOLD:
        return CORROBORATING_CONFIDENCE, False
    if diff > DIVERGENT_THRESHOLD:
        return DIVERGENT_CONFIDENCE, True
    # ponytail: simple threshold comparison on a structured severity field,
    # not real NLP claim-extraction from free text; upgrade when citizen
    # reports need free-text severity parsing.
    return NEUTRAL_CONFIDENCE, False
