# Dashboard Routes/Resources/Alerts Layers + Approve/Reject UI — Design

**Date:** 2026-08-10
**Tracker item:** 2.11 (`docs/MIGRATION_TRACKER.md`), also closes the UI gap noted under 2.9
**Status:** approved

## Problem

The frontend (`frontend/index.html`) is still the Phase 0 shell: a live map with
only the severity heat layer, and a recommendation feed with no way to act on
a recommendation. Tracker 2.11 asks for a routes layer, a resource layer, and
an alerts panel. Tracker 2.9's own note explicitly defers the approve/reject
UI to 2.11 ("API only, no UI button yet — that's 2.11").

## Scope

- Routes layer: render AG-6's route line on the map, colored by blocked status.
- Resource layer: render the static resource registry (hospitals, shelters,
  teams, ambulances) as map markers.
- Alerts panel: a severity-filtered (`severity >= 0.5`, `status === "pending"`)
  view, separate from the full recommendation feed.
- Approve/reject buttons on recommendation cards, wired to the existing
  `POST /recommendations/{id}/approve` and `/reject` endpoints.
- **Out of scope:** the alert dedup/threshold engine (tracker 2.8) — the
  alerts panel filters client-side on data that's already unfiltered from the
  backend. Conflict surfacing (tracker 2.2). Any move to Next.js — this stays
  in the single `frontend/index.html` file (Phase 0 shell), per the README's
  and tracker's existing statement that the full Next.js dashboard is
  Phase 1.5+.

## Design

### Backend: `backend/app/main.py`

New route:

```python
@app.get("/resources")
def get_resources():
    return {
        "hospitals": HOSPITALS,
        "shelters": SHELTERS,
        "teams": TEAMS,
        "ambulances": AMBULANCES,
    }
```

Straight passthrough of the static registry in `backend/app/resources.py` —
no new logic, no filtering.

### Backend test: `backend/tests/test_slice.py`

One new test asserting `GET /resources` returns all four keys as non-empty
lists.

### Frontend: `frontend/index.html`

**State store:** `const recsById = new Map();` — every recommendation ever
received, keyed by `rec.rec_id`. Replaces the current append-only rendering;
this is the single source of truth both render functions read from.

**Card rendering:** `renderCard(rec)` builds one card's DOM element (existing
severity-based styling unchanged) and, when `rec.status === "pending"`, adds
Approve/Reject buttons wired to a `decide(recId, action)` function.

**Two panels, one store:**
- `renderFeed()` — clears and rebuilds `#feed` from all of `recsById`'s
  values, newest first (by `created_at`).
- `renderAlerts()` — clears and rebuilds a new `#alerts-panel` from the
  subset where `severity >= 0.5 && status === "pending"`, newest first.

Both are called any time `recsById` changes: on WS message, on the ingest
HTTP response, and after an approve/reject completes.

**Approve/reject:** `decide(recId, action)` does
`POST ${API}/recommendations/${recId}/${action}`, and on success sets
`recsById.set(recId, updatedRecFromResponse)` then calls `renderFeed()` and
`renderAlerts()`. On failure, `alert('Failed to update recommendation')` —
no retry logic, consistent with the rest of this file's current error-handling
depth.

**Routes layer:** `const routesByIncident = {};` updated whenever a rec with
`agent_id === "AG-6"` arrives, storing `{route_line, blocked}` from
`rec.details`. A GeoJSON source `"routes"` (added on `map.on("load")`
alongside the existing `"severity"` source) is refreshed from
`Object.values(routesByIncident)` as `LineString` features. Line color: red
if `blocked`, green otherwise (matching the existing severity color
vocabulary loosely — red = problem). Toggle checkbox added to `#layers`,
same pattern as the existing severity toggle.

**Resource layer:** On `map.on("load")`, `fetch(`${API}/resources`)` once;
for each entry in each category, create a `maplibregl.Marker` (color-coded:
hospital = red cross styling via a distinct color, shelter = blue, team =
purple, ambulance = orange — reuse plain color-only markers, no custom icons)
and add to the map, keeping references in an array. Toggle checkbox in
`#layers` sets `marker.getElement().style.display = checked ? "" : "none"`
for each — markers aren't GeoJSON layers so they don't use
`setLayoutProperty` like the severity/routes layers do.

**Layout:** `#alerts-panel` is a new panel, positioned above or alongside
the existing `#panel` (exact placement is an implementation-time CSS call,
not a behavioral requirement — reuse the existing `.card` styling).

## Error handling

- Approve/reject POST failure → `alert()`, no retry.
- `/resources` fetch failure on load → `console.error`, resource layer stays
  empty; map and feed continue working (non-fatal, matches the existing
  severity-refresh's best-effort pattern — that function has no error
  handling either).

## Testing

- Backend: one new test for `GET /resources` (shape/non-empty check). The
  existing 15-test suite plus this one new test must stay green.
- Frontend: no test framework exists in this project (plain HTML/JS via CDN,
  no build step). Verification is manual, done after implementation: start
  the backend, open `index.html`, send a critical spike via the existing
  simulate button, and confirm a route line appears, resource markers are
  visible, the alerts panel shows the new high-severity recommendation, and
  clicking approve/reject updates the card and removes it from the alerts
  panel. This matches tracker 1.10's own precedent ("visually confirmed in
  browser").
