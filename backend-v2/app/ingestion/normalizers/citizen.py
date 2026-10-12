"""Citizen normalizer + trust scoring (Phase 9, ported from V1
`normalize_citizen` + `citizen_verification.score_confidence`). A citizen's
self-reported coordinates are never GPS-verified here, so a provided
lat/lon is APPROXIMATE, not EXACT; no coordinates means UNKNOWN — never
guessed. Per V1's documented design (unchanged in V2): a citizen report
computes a trust score against the incident's current severity but does
NOT itself wake the agent chain — `ingestion/service.py` must not enqueue
an orchestration job for `source_type="citizen"`."""

from app.ingestion.schemas import CitizenReport
from app.models.incident import LocationStateEnum

CORROBORATING_THRESHOLD = 0.2
DIVERGENT_THRESHOLD = 0.4
NEUTRAL_CONFIDENCE = 0.5
CORROBORATING_CONFIDENCE = 0.8
DIVERGENT_CONFIDENCE = 0.2


def normalize_citizen(data: CitizenReport) -> dict:
    location_state = (
        LocationStateEnum.APPROXIMATE if data.lat is not None and data.lon is not None else LocationStateEnum.UNKNOWN
    )
    return {
        "source_type": "citizen",
        "payload": {"message": data.message, "claimed_severity": data.claimed_severity},
        "location_state": location_state,
        "latitude": data.lat,
        "longitude": data.lon,
    }


def score_confidence(claimed_severity: float, blackboard_state: dict) -> tuple[float, bool]:
    """Returns (confidence, flagged_for_review)."""
    ag1_severity = blackboard_state.get("AG-1", {}).get("severity")
    if ag1_severity is None:
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
