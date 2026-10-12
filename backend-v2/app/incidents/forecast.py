"""Predictive impact (PRD DS-2): a deliberately simple, clearly-labelled
linear-trend projection of the incident's water-level readings. It is a
heuristic, not a hydrological model — the response says so, reports its own
fit quality, and returns `insufficient_data` instead of inventing a trend
when there are too few readings."""

from datetime import datetime, timezone

from app.agents.disaster_assessment.rules import threshold_severity

HORIZONS_HOURS = (1, 3, 6)
MIN_POINTS = 3
MIN_SPAN_HOURS = 5 / 60  # readings must span at least 5 minutes
METRIC = "water_level"
METHOD = "linear-trend heuristic (least squares over this incident's sensor readings)"


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _insufficient(n: int, reason: str) -> dict:
    return {"status": "insufficient_data", "metric": METRIC, "method": METHOD, "n_points": n, "reason": reason,
            "horizons": []}


def build_forecast(readings: list[tuple[str, datetime, float, str]]) -> dict:
    """`readings`: (sensor_id, received_at, value, unit) for METRIC. The
    sensor with the most readings is used (mixing sensors would fit noise)."""
    by_sensor: dict[str, list[tuple[datetime, float, str]]] = {}
    for sensor, at, value, unit in readings:
        by_sensor.setdefault(sensor, []).append((_aware(at), float(value), unit))
    if not by_sensor:
        return _insufficient(0, "No water_level readings for this incident.")

    sensor, pts = max(by_sensor.items(), key=lambda kv: len(kv[1]))
    pts.sort(key=lambda p: p[0])
    n = len(pts)
    t0 = pts[0][0]
    xs = [(p[0] - t0).total_seconds() / 3600 for p in pts]
    ys = [p[1] for p in pts]
    if n < MIN_POINTS:
        return _insufficient(n, f"Need at least {MIN_POINTS} readings from one sensor; have {n}.")
    if xs[-1] - xs[0] < MIN_SPAN_HOURS:
        return _insufficient(n, "Readings span under 5 minutes; no meaningful trend.")

    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 if ss_tot == 0 else max(0.0, 1 - ss_res / ss_tot)

    last_x, last_val = xs[-1], ys[-1]
    horizons = []
    for h in HORIZONS_HOURS:
        predicted = max(0.0, intercept + slope * (last_x + h))
        horizons.append({
            "hours": h,
            "predicted_value": round(predicted, 2),
            "predicted_severity": round(threshold_severity(METRIC, predicted) or 0.0, 2),
        })

    trend = "rising" if slope > 0.05 else "falling" if slope < -0.05 else "steady"
    return {
        "status": "ok", "metric": METRIC, "method": METHOD, "sensor_id": sensor, "unit": pts[-1][2],
        "n_points": n, "trend": trend, "slope_per_hour": round(slope, 3), "current_value": round(last_val, 2),
        "current_severity": round(threshold_severity(METRIC, last_val) or 0.0, 2),
        "fit_r2": round(r2, 2), "confidence": "low" if (r2 < 0.5 or n < 5) else "moderate",
        "as_of": pts[-1][0].isoformat(), "horizons": horizons,
        "disclaimer": "Heuristic extrapolation of recent sensor readings; not a hydrological model. "
                      "Verify against official forecasts before acting.",
    }
