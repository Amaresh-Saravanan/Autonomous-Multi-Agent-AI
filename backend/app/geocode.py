"""Reverse geocoding for state/district resolution via Nominatim (free, unauthenticated).

Resolves (lat, lon) -> (state, district) for administrative boundary enrichment.
All failures (network error, bad response, malformed JSON, rate limited) degrade
silently to (None, None) — never raises, consistent with llm.py and blackboard.py's
defensive patterns in this codebase.

ponytail: single free unauthenticated Nominatim endpoint, in-process dict cache,
no retry/backoff, no self-hosted Nominatim — swap to a self-hosted instance or a
paid geocoding API if request volume exceeds the ~1req/sec courtesy limit, or add
a shared/persistent cache if a multi-process deployment makes the in-memory one
ineffective.
"""
from __future__ import annotations

import httpx
from . import geo_utils

_cache: dict[str, tuple[str | None, str | None]] = {}
_client = httpx.Client(timeout=5.0)


def reverse(lat: float, lon: float) -> tuple[str | None, str | None]:
    """Return (state, district) for a coordinate, or (None, None) on failure.

    Uses Nominatim reverse geocoding. Results are cached by quantized lat/lon
    (geo_utils' ~1.1km cells) to avoid hammering the API for nearby events.
    """
    cell = geo_utils.cell_id(lat, lon)
    if cell in _cache:
        return _cache[cell]

    try:
        resp = _client.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "zoom": 10,
                "addressdetails": 1,
            },
            headers={
                "User-Agent": "autonomous-multi-agent-disaster-response/1.0"
            },
        )
        if resp.status_code != 200:
            result = (None, None)
        else:
            data = resp.json()
            addr = data.get("address", {})
            state = addr.get("state")
            # Try district variants in order (state_district, county, district)
            district = (
                addr.get("state_district")
                or addr.get("county")
                or addr.get("district")
            )
            result = (state, district)
    except (
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValueError,  # JSON decode
        KeyError,
        TypeError,
    ):
        result = (None, None)

    _cache[cell] = result
    return result


def reset() -> None:
    """Clear the cache (test isolation)."""
    _cache.clear()
