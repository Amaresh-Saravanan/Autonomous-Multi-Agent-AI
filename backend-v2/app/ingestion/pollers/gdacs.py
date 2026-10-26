"""GDACS poller: public, no API key. The MAP endpoint requires exactly one
`eventtype` per call (confirmed live: no "all types" option returns a
'Please specify only 1 eventtype' error) -- so this hits it once per known
GDACS hazard category and merges the results. Only Orange/Red alert-level
events are kept; Green is the common case and not actionable here.

# ponytail: EVENT_TYPES is GDACS's own hazard-category set (earthquake,
tropical cyclone, flood, drought, wildfire), hardcoded because the API
has no "list valid eventtypes" endpoint to query it from. VO (volcano) is
deliberately excluded: confirmed live that the endpoint 404s for it every
time (not a transient failure), so it's not worth polling or retrying.
Add it back if GDACS ever starts serving that eventtype.

Mapped to the `weather` normalizer, not `satellite`: GDACS gives a point
location (not an imagery tile), and SatelliteEvent requires real
`area_bounds` -- synthesizing a bounding box around a point would be
fabricated area data, which this codebase deliberately avoids elsewhere
(location_state honesty, no fabricated fallback coordinates). WeatherEvent
fits the actual shape of what GDACS reports: a point plus an alert.
"""

import logging

import httpx
from redis.exceptions import RedisError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed

from app.ingestion.pollers.results import PollResult
from app.ingestion.schemas import WeatherEvent

logger = logging.getLogger("app.pollers")

SOURCE = "gdacs"
EVENT_LIST_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
EVENT_TYPES = ["EQ", "TC", "FL", "DR", "WF"]
ALLOWED_ALERT_LEVELS = {"orange", "red"}


def _is_retryable(exc: BaseException) -> bool:
    """A 404 means this eventtype doesn't exist on the endpoint -- a
    permanent condition, not a transient one. Retrying it three times just
    burns 2 seconds for the same answer; let it fail immediately."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return False
    return True


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception(_is_retryable), reraise=True)
def fetch_event_type(client: httpx.Client, event_type: str) -> dict:
    resp = client.get(EVENT_LIST_URL, params={"eventtype": event_type}, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def build_event(feature: dict) -> tuple[WeatherEvent, str] | None:
    props = feature.get("properties", {})
    alert_level = (props.get("alertlevel") or "").lower()
    if alert_level not in ALLOWED_ALERT_LEVELS:
        return None

    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    # Some GDACS features (e.g. a cyclone's track) are Polygon/LineString,
    # where `coordinates` is nested lists, not a flat [lon, lat] -- skip
    # rather than guess a centroid, consistent with never fabricating a
    # location for an area this codebase doesn't actually have.
    if geometry.get("type") != "Point" or not coords or len(coords) < 2:
        return None
    lon, lat = coords[0], coords[1]
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        return None

    # GDACS mixes units across hazard types (km/h for cyclone wind, m for
    # flood depth, VEI for volcanoes) -- folded into `alert` text, never
    # mapped onto a numeric field like wind_speed_kmh, which would
    # misrepresent what was actually measured for non-wind hazards.
    severity = props.get("severitydata") or {}
    name = props.get("name") or props.get("eventname") or "unknown"
    alert = f"GDACS {props.get('alertlevel')} {props.get('eventtype')}: {name} ({severity.get('severitytext', '')})".strip()

    event = WeatherEvent(location=name, alert=alert, lat=lat, lon=lon)
    dedup_id = f"{props.get('eventtype')}:{props.get('eventid')}:{props.get('episodeid')}"
    return event, dedup_id


def poll(*, client: httpx.Client, ingest, dedup) -> PollResult:
    fetched = ingested = skipped = 0
    any_success = False
    errors = []

    for event_type in EVENT_TYPES:
        try:
            data = fetch_event_type(client, event_type)
        except Exception as exc:
            logger.warning("gdacs: fetch failed for eventtype=%s: %s", event_type, exc)
            errors.append(f"{event_type}: {exc}")
            continue

        any_success = True
        for feature in data.get("features", []):
            try:
                built = build_event(feature)
                if built is None:
                    continue
                event, ext_id = built

                fetched += 1
                if dedup.already_seen(SOURCE, ext_id):
                    skipped += 1
                    continue

                ingest("weather", event)
                dedup.mark_seen(SOURCE, ext_id)
                ingested += 1
            except RedisError as exc:
                # An unreachable dedup store is an infrastructure problem,
                # not a bad GDACS record -- don't mislabel it as a
                # malformed feature and keep limping through the batch on
                # a broken connection. Let it propagate: runner.run_once
                # catches it and records the whole gdacs poll as failed.
                logger.error("gdacs: dedup store unreachable (infrastructure error): %s", exc)
                raise
            except Exception as exc:
                logger.warning("gdacs: skipping malformed feature: %s", exc)

    # Only surface an error if every event type failed -- a few categories
    # failing while others succeed is partial data, not a poll failure.
    error = "; ".join(errors) if not any_success and errors else None
    return PollResult(fetched=fetched, ingested=ingested, skipped_duplicate=skipped, error=error)
