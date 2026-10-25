# Alert Dedup/Threshold Engine — Design

**Date:** 2026-08-12
**Tracker item:** 2.8 (`docs/MIGRATION_TRACKER.md`)
**Status:** approved

## Problem

Every `POST /ingest/{source_type}` call broadcasts all 7 agent recommendations
over `/ws/alerts` unconditionally, even routine low-severity ones (e.g. a
repeated "monitor" reading). PRD lists "alert fatigue" as a named risk,
mitigated by "severity thresholds + dedup + prioritization." Tracker 2.8
flags this as not yet built.

## Scope

Gate the WebSocket broadcast only. The `/ingest` HTTP response stays
complete regardless (a direct request always gets its full answer — only the
*notification* is gated). Recording (`recommendations.record`,
`blackboard.merge`, severity grid updates) is unaffected, since those happen
inside `orchestrator.run()` and stay unconditional — this preserves the full
audit trail and the dashboard's `GET /recommendations` completeness.

**Out of scope:** filtering which recs appear *within* a pushed WS payload
(all-or-nothing per batch, not per-rec); a dedicated `/alerts` endpoint
(TDD mentions `GET /alerts/stream` but that duplicates the dashboard's
existing client-side severity filter and is bigger scope than this tracker
item asks for).

## Design

### New module: `backend/app/alerts.py`

In-memory state (same pattern as `blackboard.py`/`recommendations.py`):
tracks the last-pushed `(action, severity)` per `(incident_id, agent_id)`.

```python
THRESHOLD = 0.5  # matches the frontend Alerts panel's severity cutoff

_last_pushed: dict[str, dict] = {}  # f"{incident_id}:{agent_id}" -> {"action", "severity"}


def should_push(incident_id: str, recs: list[dict]) -> bool:
    any_new = False
    for rec in recs:
        if rec["severity"] < THRESHOLD:
            continue
        key = f"{incident_id}:{rec['agent_id']}"
        prev = _last_pushed.get(key)
        current = {"action": rec["action"], "severity": rec["severity"]}
        if prev != current:
            any_new = True
        _last_pushed[key] = current
    return any_new
```

Every alert-worthy rec's state is refreshed on each call regardless of
whether it counts as "new" — so a genuine change (severity climbing from 0.6
to 0.9) always pushes, and an unchanged repeat never does, and the next
comparison after a push is always against the latest known state.

### `backend/app/main.py` change

The `/ingest` handler's WS broadcast loop (currently unconditional) is
wrapped in the gate:

```python
if alerts.should_push(incident_id, recs):
    for client in list(_ws_clients):
        try:
            await client.send_json({"incident_id": incident_id, "recommendations": recs})
        except Exception:  # noqa: BLE001 - drop dead clients
            _ws_clients.remove(client)
```

Everything else in `/ingest` (normalize, `orchestrator.run()`, the HTTP
return value) is untouched.

## Error handling

None new — the existing dead-WS-client cleanup inside the broadcast loop is
unchanged.

## Testing

New `backend/tests/test_alerts.py`, unit-testing `should_push` directly (no
HTTP/WS needed):
- First high-severity rec for a given `(incident_id, agent_id)` → `True`.
- Identical repeat (same action + severity) → `False`.
- Changed severity for the same agent → `True` again.
- All-low-severity batch → `False`.

Existing 16 backend tests must stay green — none of them assert on WS
broadcast behavior today (they use `TestClient`, HTTP only), so this change
is safe against the existing suite.
