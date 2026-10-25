"""Open-Meteo poller: weather + flood, public, no API key. One HTTP call
each to the forecast and flood APIs per configured point, merged into a
single WeatherEvent per point (one point = one incident signal, not two)."""

import logging
from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.ingestion.pollers.results import PollResult
from app.ingestion.schemas import WeatherEvent

logger = logging.getLogger("app.pollers")

SOURCE = "open_meteo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
def _get(client: httpx.Client, url: str, params: dict) -> dict:
    resp = client.get(url, params=params, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_point(client: httpx.Client, lat: float, lon: float) -> tuple[dict, dict]:
    """Returns (forecast_json, flood_json). The flood API has no coverage
    for every point (e.g. the open ocean); a failure there just means no
    flood info is folded into the alert text, not a poll failure."""
    forecast = _get(
        client,
        FORECAST_URL,
        {"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,wind_speed_10m"},
    )
    try:
        flood = _get(client, FLOOD_URL, {"latitude": lat, "longitude": lon, "daily": "river_discharge"})
    except Exception as exc:
        logger.info("open_meteo: no flood data for (%s, %s): %s", lat, lon, exc)
        flood = {}
    return forecast, flood


def build_event(name: str, lat: float, lon: float, forecast: dict, flood: dict) -> tuple[WeatherEvent, str]:
    """Returns (event, dedup_id). The dedup id is Open-Meteo's own
    `current.time` reading timestamp for this point -- the feed has no
    discrete event id, so this is the honest "has this specific reading
    already been ingested" signal rather than a fabricated one."""
    current = forecast.get("current", {})
    daily = flood.get("daily", {})
    discharge_series = daily.get("river_discharge") or []
    discharge = discharge_series[0] if discharge_series else None

    alert = f"river_discharge={discharge}m3/s" if discharge is not None else None

    event = WeatherEvent(
        location=name,
        temp_c=current.get("temperature_2m"),
        humidity_pct=current.get("relative_humidity_2m"),
        wind_speed_kmh=current.get("wind_speed_10m"),
        alert=alert,
        lat=lat,
        lon=lon,
    )
    reading_time = current.get("time") or datetime.now(timezone.utc).isoformat()
    return event, f"{name}:{reading_time}"


def poll(*, points: list[tuple[str, float, float]], client: httpx.Client, ingest, dedup) -> PollResult:
    fetched = ingested = skipped = 0
    for name, lat, lon in points:
        try:
            forecast, flood = fetch_point(client, lat, lon)
        except Exception as exc:
            logger.warning("open_meteo: failed to fetch point %s: %s", name, exc)
            continue

        fetched += 1
        event, dedup_id = build_event(name, lat, lon, forecast, flood)
        if dedup.already_seen(SOURCE, dedup_id):
            skipped += 1
            continue

        ingest("weather", event)
        dedup.mark_seen(SOURCE, dedup_id)
        ingested += 1

    return PollResult(fetched=fetched, ingested=ingested, skipped_duplicate=skipped, error=None)
