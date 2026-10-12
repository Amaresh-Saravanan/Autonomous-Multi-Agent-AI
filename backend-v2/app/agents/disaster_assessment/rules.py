"""Threshold fallback (Phase 15 AG-1, ported from V1 THRESHOLDS). Only
`water_level` has a configured rule — same ceiling as V1, not a new gap."""

THRESHOLDS: dict[str, tuple[float, float]] = {
    "water_level": (3.0, 5.0),
}


def threshold_severity(metric: str, reading: float) -> float | None:
    """None if `metric` has no configured rule (caller should skip it)."""
    bounds = THRESHOLDS.get(metric)
    if bounds is None:
        return None
    warn, crit = bounds
    if reading < warn:
        return 0.0
    if reading < crit:
        return 0.5 + 0.5 * (reading - warn) / (crit - warn)
    return 1.0
