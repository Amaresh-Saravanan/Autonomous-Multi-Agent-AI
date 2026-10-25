"""USGS earthquake poller: public, no API key. Filters the rolling
all-hour feed by a configurable bounding box and minimum magnitude."""

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.ingestion.pollers.results import PollResult
from app.ingestion.schemas import IoTEvent

logger = logging.getLogger("app.pollers")

SOURCE = "usgs"
FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
def fetch(client: httpx.Client) -> dict:
    resp = client.get(FEED_URL, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def _in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def build_event(feature: dict) -> tuple[IoTEvent, str] | None:
    """None if the feature is missing coordinates or a magnitude --
    both required to place and size the reading."""
    props = feature.get("properties", {})
    coords = (feature.get("geometry") or {}).get("coordinates")
    mag = props.get("mag")
    if not coords or len(coords) < 2 or mag is None:
        return None

    lon, lat = coords[0], coords[1]
    event = IoTEvent(
        sensor_id=feature["id"],
        metric="magnitude",
        reading=mag,
        unit=props.get("magType") or "mag",
        lat=lat,
        lon=lon,
    )
    return event, feature["id"]


def poll(
    *,
    bbox: tuple[float, float, float, float],
    min_magnitude: float,
    client: httpx.Client,
    ingest,
    dedup,
) -> PollResult:
    try:
        data = fetch(client)
    except Exception as exc:
        logger.warning("usgs: fetch failed: %s", exc)
        return PollResult(fetched=0, ingested=0, skipped_duplicate=0, error=str(exc))

    fetched = ingested = skipped = 0
    for feature in data.get("features", []):
        built = build_event(feature)
        if built is None:
            continue
        event, ext_id = built

        if event.reading < min_magnitude or not _in_bbox(event.lon, event.lat, bbox):
            continue

        fetched += 1
        if dedup.already_seen(SOURCE, ext_id):
            skipped += 1
            continue

        ingest("iot", event)
        dedup.mark_seen(SOURCE, ext_id)
        ingested += 1

    return PollResult(fetched=fetched, ingested=ingested, skipped_duplicate=skipped, error=None)
