# Backend V2 API Reference

All routes except `/health` and `/ws/alerts` are versioned under
`/api/v1`. Auth: `Authorization: Bearer <JWT>` for user endpoints,
`X-Device-Id`/`X-Device-Secret` for ingestion + citizen chat.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | open | liveness-ish, kept for V1 parity |
| GET | `/api/v1/health` | open | |
| GET | `/api/v1/health/live` | open | process up |
| GET | `/api/v1/health/ready` | open | checks DB connectivity |
| GET | `/api/v1/health/metrics` | open | Prometheus text format |
| POST | `/api/v1/auth/login` | open | `{email,password}` → `{access_token,token_type,role,agency_id}` |
| POST | `/api/v1/ingestion/iot` | device (`source_type=iot`) | `IoTEvent` → 202 `{event_id,incident_id,status}` |
| POST | `/api/v1/ingestion/weather` | device (`weather`) | `WeatherEvent` → 202 |
| POST | `/api/v1/ingestion/satellite` | device (`satellite`) | `SatelliteEvent` → 202 |
| POST | `/api/v1/ingestion/citizen` | device (`citizen`) | `CitizenReport` → 202; does not enqueue agent processing |
| GET | `/api/v1/incidents` | VIEWER+ | list, newest-updated first |
| GET | `/api/v1/incidents/{id}` | VIEWER+ | |
| GET | `/api/v1/recommendations?incident_id=` | VIEWER+ | agency-filtered (NULL target → ADMIN only) |
| POST | `/api/v1/recommendations/{id}/decide` | OPERATOR+ (ADMIN for `override`) | `{decision,reason?,replacement_action?}` |
| POST | `/api/v1/citizen/chat` | device (`citizen`) | `{message,language}` → `{reply,language,reasoning_mode,sources}` |
| GET | `/api/v1/alerts` | VIEWER+ | agency-filtered |
| GET | `/api/v1/resources` | VIEWER+ | hospitals/shelters/teams/ambulances/supplies snapshot |
| GET | `/api/v1/audit` | ADMIN | |
| WS | `/ws/alerts?token=<JWT>` | JWT via query param | agency-filtered alert push |

## Error shape

Every error response (via `app/errors.py`'s handlers): `{"error": "<code>",
"message": "<safe message>", "details": {...}}`. No stack traces leak into
responses; unexpected exceptions map to a generic `internal_error` 500.

## Not exposed (by design)

Drone, social media, and GIS ingestion have no endpoint — no V1
normalizer exists for any of them (see `docs/BACKEND_V2_MIGRATION.md`
DEFERRED list).
