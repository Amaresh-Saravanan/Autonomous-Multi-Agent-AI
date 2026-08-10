# Dashboard Routes/Resources/Alerts Layers + Approve/Reject UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a routes layer, a resource layer, a severity-filtered alerts panel, and approve/reject buttons to the disaster-response dashboard (tracker 2.11, closing the UI gap noted in 2.9).

**Architecture:** One new backend endpoint (`GET /resources`, static passthrough) plus an extension of `frontend/index.html`'s existing vanilla-JS dashboard: a `recsById` Map becomes the single source of truth for recommendation state, driving the recommendation feed, the new alerts panel, and the approve/reject buttons. Routes and resources become two more map layers alongside the existing severity heat layer.

**Tech Stack:** Python 3.11 / FastAPI (backend, unchanged stack), plain HTML/JS + MapLibre GL via CDN (frontend, unchanged stack — no build step, no new dependency).

## Global Constraints

- Routes layer: line colored red if `details.blocked` is true, green otherwise.
- Resource layer: static markers from a new `GET /resources` endpoint, toggled via marker `display` style (not a GeoJSON layer).
- Alerts panel: shows recs where `severity >= 0.5 && status === "pending"`, newest first — client-side filter only, no backend alert engine (tracker 2.8 is out of scope).
- Approve/reject buttons call the existing `POST /recommendations/{id}/approve` and `/reject` endpoints — no new backend logic beyond the `/resources` route.
- Out of scope: alert dedup/threshold engine (2.8), conflict surfacing (2.2), any Next.js migration — stays in `frontend/index.html`.
- No JS test framework exists in this project. Each frontend task is verified with `node --check` (JS syntax) plus `grep` checks (content landed). A full manual browser walkthrough is done by the controller after Task 4, not delegated to a subagent — see the note at the end of this plan.
- The existing 15 backend tests, plus the 1 new one from Task 1, must stay green throughout (`cd backend && python -m pytest tests/ -v`).
- Full spec: `docs/superpowers/specs/2026-08-10-dashboard-layers-design.md`.

---

### Task 1: `GET /resources` backend endpoint

**Files:**
- Modify: `backend/app/main.py:1-29` (imports + insert new route after `/health`)
- Test: `backend/tests/test_slice.py`

**Interfaces:**
- Produces: `GET /resources` → `{"hospitals": [...], "shelters": [...], "teams": [...], "ambulances": [...]}`, each list non-empty, drawn straight from `backend/app/resources.py`'s `HOSPITALS`, `SHELTERS`, `TEAMS`, `AMBULANCES`. Consumed by Task 4 (resource layer fetch).

- [ ] **Step 1: Write the failing test**

Add this function to `backend/tests/test_slice.py`, right after `test_health()` (currently lines 18-21):

```python
def test_resources_endpoint_returns_all_categories():
    r = client.get("/resources")
    assert r.status_code == 200
    body = r.json()
    for key in ["hospitals", "shelters", "teams", "ambulances"]:
        assert key in body, f"missing {key} in /resources response"
        assert len(body[key]) > 0, f"{key} list is empty"
```

Also add it to the `if __name__ == "__main__":` block at the bottom of the file (currently lines 62-66), so the call list becomes:

```python
if __name__ == "__main__":
    test_health()
    test_resources_endpoint_returns_all_categories()
    test_normal_reading_does_not_raise_severity()
    test_critical_reading_raises_severity_with_evidence()
    print("OK: Phase 0 vertical slice self-test passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_slice.py::test_resources_endpoint_returns_all_categories -v`
Expected: FAIL with a 404 status code (route doesn't exist yet) — the assertion `assert r.status_code == 200` fails.

- [ ] **Step 3: Implement the route**

In `backend/app/main.py`, change the import block (currently lines 11-17):

```python
from . import audit
from . import blackboard
from . import orchestrator
from . import recommendations
from . import severity_grid
from .normalizers import normalize
from agents import citizen as citizen_agent
```

to:

```python
from . import audit
from . import blackboard
from . import orchestrator
from . import recommendations
from . import severity_grid
from .normalizers import normalize
from .resources import HOSPITALS, SHELTERS, TEAMS, AMBULANCES
from agents import citizen as citizen_agent
```

Then add this route immediately after the `/health` route (currently lines 27-29), before `/ingest`:

```python
@app.get("/health")
def health():
    return {"status": "ok", "using_redis": blackboard.using_redis()}


@app.get("/resources")
def get_resources():
    return {
        "hospitals": HOSPITALS,
        "shelters": SHELTERS,
        "teams": TEAMS,
        "ambulances": AMBULANCES,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_slice.py::test_resources_endpoint_returns_all_categories -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: `16 passed` (the prior 15 plus this new one).

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_slice.py
git commit -m "Add GET /resources endpoint (tracker 2.11)"
```

---

### Task 2: Frontend state store, alerts panel, approve/reject buttons

**Files:**
- Modify: `frontend/index.html` (CSS block, `#panel` HTML, and the dashboard `<script>` block)

**Interfaces:**
- Consumes: none from Task 1 (the resource fetch is Task 4's job).
- Produces (JS symbols later tasks build on): `recsById` (a `Map<string, object>` of every recommendation seen, keyed by `rec_id`), `sortedRecs()` (returns all values of `recsById` newest-first by `created_at`), `renderCard(rec)`, `renderFeed()`, `renderAlerts()`, `decide(recId, action)`, `ingestRecommendations(recs)` (the single entry point that both the WS handler and the send-form handler call to register new recs into the store and trigger re-renders).

- [ ] **Step 1: Add `.actions` button styling**

In `frontend/index.html`, find this CSS rule (currently line 40):

```css
  .card .why { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
```

Add immediately after it:

```css
  .card .why { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
  .card .actions { margin-top: 8px; display: flex; gap: 8px; }
  .card .actions button {
    cursor: pointer; font-size: 11px; padding: 4px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: rgba(255,255,255,0.05); color: var(--text-primary);
  }
```

- [ ] **Step 2: Add the alerts section to `#panel`**

Find this HTML block (currently lines 60-64):

```html
  <div id="panel">
    <h2>Recommendations</h2>
    <div id="status">connecting…</div>
    <div id="feed"></div>
  </div>
```

Replace with:

```html
  <div id="panel">
    <h2>Alerts</h2>
    <div id="alerts-feed"></div>
    <hr style="border-color: var(--border); margin: 12px 0;" />
    <h2>Recommendations</h2>
    <div id="status">connecting…</div>
    <div id="feed"></div>
  </div>
```

- [ ] **Step 3: Replace the dashboard script**

Find the entire `<script>...</script>` block (currently lines 72-169, the one starting `const API = "http://localhost:8000";`). Replace its full contents with:

```html
  <script>
    const API = "http://localhost:8000";
    const map = new maplibregl.Map({
      container: "map",
      style: "https://demotiles.maplibre.org/style.json",
      center: [80.2707, 13.0827],
      zoom: 10,
    });

    const statusEl = document.getElementById("status");
    const feedEl = document.getElementById("feed");
    const alertsFeedEl = document.getElementById("alerts-feed");
    let currentIncidentId = null;
    let severityLayerReady = false;

    const recsById = new Map();

    // DS-1 severity heat layer (tracker 1.10): color ramp matches the .card
    // severity classes above — one severity language across map + feed.
    map.on("load", () => {
      map.addSource("severity", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "severity-fill", type: "fill", source: "severity",
        paint: {
          "fill-color": [
            "interpolate", ["linear"], ["get", "severity"],
            0, "#22C55E", 0.5, "#EAB308", 0.85, "#F97316", 1, "#EF4444",
          ],
          "fill-opacity": 0.35,
        },
      });
      severityLayerReady = true;
    });

    document.getElementById("toggle-severity").addEventListener("change", (e) => {
      if (severityLayerReady) {
        map.setLayoutProperty("severity-fill", "visibility", e.target.checked ? "visible" : "none");
      }
    });

    async function refreshSeverity(incidentId) {
      if (!severityLayerReady || !incidentId) return;
      const res = await fetch(`${API}/incidents/${incidentId}/severity`);
      const geojson = await res.json();
      map.getSource("severity").setData(geojson);
    }

    function sevClass(sev) {
      if (sev >= 0.85) return "sev-critical";
      if (sev >= 0.5) return "sev-high";
      return "";
    }

    async function decide(recId, action) {
      try {
        const res = await fetch(`${API}/recommendations/${recId}/${action}`, { method: "POST" });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const updated = await res.json();
        recsById.set(updated.rec_id, updated);
        renderFeed();
        renderAlerts();
      } catch (err) {
        alert("Failed to update recommendation");
      }
    }

    function renderCard(rec) {
      const div = document.createElement("div");
      div.className = "card " + sevClass(rec.severity);
      div.innerHTML = `
        <div class="action">${rec.agent_id} · ${rec.action}</div>
        <div class="why">${rec.rationale}</div>
        <div class="why">confidence ${rec.confidence.toFixed(2)} · ${rec.status}</div>
      `;
      if (rec.status === "pending") {
        const actions = document.createElement("div");
        actions.className = "actions";
        const approveBtn = document.createElement("button");
        approveBtn.textContent = "Approve";
        approveBtn.addEventListener("click", () => decide(rec.rec_id, "approve"));
        const rejectBtn = document.createElement("button");
        rejectBtn.textContent = "Reject";
        rejectBtn.addEventListener("click", () => decide(rec.rec_id, "reject"));
        actions.appendChild(approveBtn);
        actions.appendChild(rejectBtn);
        div.appendChild(actions);
      }
      return div;
    }

    function sortedRecs() {
      return [...recsById.values()].sort((a, b) => b.created_at.localeCompare(a.created_at));
    }

    function renderFeed() {
      feedEl.innerHTML = "";
      sortedRecs().forEach((rec) => feedEl.appendChild(renderCard(rec)));
    }

    function renderAlerts() {
      alertsFeedEl.innerHTML = "";
      sortedRecs()
        .filter((rec) => rec.severity >= 0.5 && rec.status === "pending")
        .forEach((rec) => alertsFeedEl.appendChild(renderCard(rec)));
    }

    function addMarker(rec) {
      if (rec.geo && rec.geo.coordinates && rec.geo.coordinates.length === 2) {
        new maplibregl.Marker({ color: rec.severity >= 0.85 ? "#EF4444" : "#F97316" })
          .setLngLat(rec.geo.coordinates)
          .setPopup(new maplibregl.Popup().setText(rec.rationale))
          .addTo(map);
      }
    }

    function ingestRecommendations(recs) {
      recs.forEach((rec) => {
        recsById.set(rec.rec_id, rec);
        addMarker(rec);
      });
      renderFeed();
      renderAlerts();
    }

    function connectWS() {
      const ws = new WebSocket(API.replace("http", "ws") + "/ws/alerts");
      ws.onopen = () => (statusEl.textContent = "live");
      ws.onclose = () => { statusEl.textContent = "reconnecting…"; setTimeout(connectWS, 2000); };
      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        ingestRecommendations(msg.recommendations);
        currentIncidentId = msg.incident_id;
        refreshSeverity(currentIncidentId);
      };
    }
    connectWS();

    document.getElementById("send-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const reading = parseFloat(document.getElementById("reading").value);
      const res = await fetch(API + "/ingest/iot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sensor_id: "wl-042", metric: "water_level", reading,
          unit: "m", lat: 13.0827, lon: 80.2707, incident_id: "demo-1",
        }),
      });
      const body = await res.json();
      ingestRecommendations(body.recommendations); // also render via HTTP response, not just WS
      currentIncidentId = body.incident_id;
      refreshSeverity(currentIncidentId);
    });
  </script>
```

Note what changed vs. the old script: `renderRec` is gone, replaced by `renderCard` (builds one card, now with approve/reject buttons) + `renderFeed`/`renderAlerts` (rebuild their containers from `recsById`) + `ingestRecommendations` (the new single entry point — both the WS handler and the send-form handler now call this instead of looping and calling the old `renderRec` directly). Marker creation is factored into `addMarker`, called from `ingestRecommendations` — same one-marker-per-received-rec behavior as before, just relocated.

- [ ] **Step 4: Verify JS syntax**

Run (from the repo root):

```bash
TMPJS=$(mktemp --suffix=.js)
python -c "
import re
html = open('frontend/index.html', encoding='utf-8').read()
matches = re.findall(r'<script>(.*?)</script>', html, re.S)
open('$TMPJS', 'w', encoding='utf-8').write(matches[-1])
"
node --check "$TMPJS" && echo "JS syntax OK"
rm "$TMPJS"
```

Expected: `JS syntax OK`, no output from `node --check` (silent = valid).

- [ ] **Step 5: Verify the new pieces landed**

Run: `grep -c "alerts-feed\|recsById\|renderAlerts\|function decide" frontend/index.html`
Expected: a count of `4` or higher (each string appears at least once).

- [ ] **Step 6: Run the backend test suite (regression check — this task didn't touch backend, but confirm nothing else broke)**

Run: `cd backend && python -m pytest tests/ -v`
Expected: `16 passed` (unchanged from Task 1).

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "Add alerts panel and approve/reject buttons to dashboard (tracker 2.11)"
```

---

### Task 3: Routes layer

**Files:**
- Modify: `frontend/index.html` (`#layers` HTML, and the dashboard `<script>` block from Task 2)

**Interfaces:**
- Consumes: `ingestRecommendations(recs)` from Task 2 (this task adds a route-specific side effect inside it).
- Produces: `routesByIncident` (object keyed by `incident_id`, each value `{route_line, blocked}` from an AG-6 rec's `details`), `refreshRoutes()`.

- [ ] **Step 1: Add the routes layer toggle checkbox**

Find this HTML (currently in `#layers`):

```html
  <div id="layers">
    <label><input type="checkbox" id="toggle-severity" checked /> Severity heat layer</label>
  </div>
```

Replace with:

```html
  <div id="layers">
    <label><input type="checkbox" id="toggle-severity" checked /> Severity heat layer</label>
    <label><input type="checkbox" id="toggle-routes" checked /> Routes</label>
  </div>
```

- [ ] **Step 2: Add the routes GeoJSON source + layer**

In the `map.on("load", () => { ... })` handler from Task 2 (the one that adds the `"severity"` source), add the routes source and layer right after `severityLayerReady = true;`:

```javascript
    map.on("load", () => {
      map.addSource("severity", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "severity-fill", type: "fill", source: "severity",
        paint: {
          "fill-color": [
            "interpolate", ["linear"], ["get", "severity"],
            0, "#22C55E", 0.5, "#EAB308", 0.85, "#F97316", 1, "#EF4444",
          ],
          "fill-opacity": 0.35,
        },
      });
      severityLayerReady = true;

      map.addSource("routes", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "routes-line", type: "line", source: "routes",
        paint: {
          "line-color": ["case", ["get", "blocked"], "#EF4444", "#22C55E"],
          "line-width": 3,
          "line-dasharray": ["case", ["get", "blocked"], ["literal", [2, 2]], ["literal", [1, 0]]],
        },
      });
    });
```

- [ ] **Step 3: Add the toggle listener and `refreshRoutes`**

Find the severity toggle listener from Task 2:

```javascript
    document.getElementById("toggle-severity").addEventListener("change", (e) => {
      if (severityLayerReady) {
        map.setLayoutProperty("severity-fill", "visibility", e.target.checked ? "visible" : "none");
      }
    });
```

Add immediately after it:

```javascript
    document.getElementById("toggle-routes").addEventListener("change", (e) => {
      map.setLayoutProperty("routes-line", "visibility", e.target.checked ? "visible" : "none");
    });

    const routesByIncident = {};

    function refreshRoutes() {
      const features = Object.entries(routesByIncident).map(([incidentId, r]) => ({
        type: "Feature",
        geometry: { type: "LineString", coordinates: r.route_line },
        properties: { incident_id: incidentId, blocked: r.blocked },
      }));
      map.getSource("routes").setData({ type: "FeatureCollection", features });
    }
```

- [ ] **Step 4: Update `ingestRecommendations` to capture AG-6 routes**

Find this function from Task 2:

```javascript
    function ingestRecommendations(recs) {
      recs.forEach((rec) => {
        recsById.set(rec.rec_id, rec);
        addMarker(rec);
      });
      renderFeed();
      renderAlerts();
    }
```

Replace with:

```javascript
    function ingestRecommendations(recs) {
      let routesChanged = false;
      recs.forEach((rec) => {
        recsById.set(rec.rec_id, rec);
        addMarker(rec);
        if (rec.agent_id === "AG-6" && rec.details && rec.details.route_line) {
          routesByIncident[rec.incident_id] = {
            route_line: rec.details.route_line,
            blocked: !!rec.details.blocked,
          };
          routesChanged = true;
        }
      });
      renderFeed();
      renderAlerts();
      if (routesChanged) refreshRoutes();
    }
```

- [ ] **Step 5: Verify JS syntax**

Run (from the repo root):

```bash
TMPJS=$(mktemp --suffix=.js)
python -c "
import re
html = open('frontend/index.html', encoding='utf-8').read()
matches = re.findall(r'<script>(.*?)</script>', html, re.S)
open('$TMPJS', 'w', encoding='utf-8').write(matches[-1])
"
node --check "$TMPJS" && echo "JS syntax OK"
rm "$TMPJS"
```

Expected: `JS syntax OK`.

- [ ] **Step 6: Verify the new pieces landed**

Run: `grep -c "routesByIncident\|refreshRoutes\|toggle-routes\|routes-line" frontend/index.html`
Expected: a count of `4` or higher.

- [ ] **Step 7: Run the backend test suite (regression check)**

Run: `cd backend && python -m pytest tests/ -v`
Expected: `16 passed`.

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html
git commit -m "Add routes layer to dashboard (tracker 2.11)"
```

---

### Task 4: Resource layer

**Files:**
- Modify: `frontend/index.html` (`#layers` HTML, and the dashboard `<script>` block from Task 3)

**Interfaces:**
- Consumes: `GET /resources` from Task 1 (`{"hospitals": [...], "shelters": [...], "teams": [...], "ambulances": [...]}`, each item shaped `{id, name, lat, lon, ...}` per `backend/app/resources.py`).
- Produces: `resourceMarkers` (array of `maplibregl.Marker` instances), `loadResources()`.

- [ ] **Step 1: Add the resource layer toggle checkbox**

Find this HTML (as left by Task 3):

```html
  <div id="layers">
    <label><input type="checkbox" id="toggle-severity" checked /> Severity heat layer</label>
    <label><input type="checkbox" id="toggle-routes" checked /> Routes</label>
  </div>
```

Replace with:

```html
  <div id="layers">
    <label><input type="checkbox" id="toggle-severity" checked /> Severity heat layer</label>
    <label><input type="checkbox" id="toggle-routes" checked /> Routes</label>
    <label><input type="checkbox" id="toggle-resources" checked /> Resources</label>
  </div>
```

- [ ] **Step 2: Add `loadResources` and the toggle listener**

Find the routes toggle listener from Task 3:

```javascript
    document.getElementById("toggle-routes").addEventListener("change", (e) => {
      map.setLayoutProperty("routes-line", "visibility", e.target.checked ? "visible" : "none");
    });
```

Add immediately after it:

```javascript
    document.getElementById("toggle-resources").addEventListener("change", (e) => {
      resourceMarkers.forEach((m) => {
        m.getElement().style.display = e.target.checked ? "" : "none";
      });
    });

    const RESOURCE_COLORS = { hospitals: "#EF4444", shelters: "#3B82F6", teams: "#A855F7", ambulances: "#F97316" };
    const resourceMarkers = [];

    async function loadResources() {
      try {
        const res = await fetch(`${API}/resources`);
        const data = await res.json();
        Object.entries(RESOURCE_COLORS).forEach(([category, color]) => {
          (data[category] || []).forEach((item) => {
            const marker = new maplibregl.Marker({ color })
              .setLngLat([item.lon, item.lat])
              .setPopup(new maplibregl.Popup().setText(`${category.slice(0, -1)}: ${item.name || item.id}`))
              .addTo(map);
            resourceMarkers.push(marker);
          });
        });
      } catch (err) {
        console.error("Failed to load resources", err);
      }
    }
```

- [ ] **Step 3: Call `loadResources` once the map is ready**

Find `connectWS();` (the line that starts the WebSocket connection, right after the `connectWS` function definition). Add immediately after it:

```javascript
    connectWS();
    loadResources();
```

- [ ] **Step 4: Verify JS syntax**

Run (from the repo root):

```bash
TMPJS=$(mktemp --suffix=.js)
python -c "
import re
html = open('frontend/index.html', encoding='utf-8').read()
matches = re.findall(r'<script>(.*?)</script>', html, re.S)
open('$TMPJS', 'w', encoding='utf-8').write(matches[-1])
"
node --check "$TMPJS" && echo "JS syntax OK"
rm "$TMPJS"
```

Expected: `JS syntax OK`.

- [ ] **Step 5: Verify the new pieces landed**

Run: `grep -c "loadResources\|resourceMarkers\|toggle-resources\|RESOURCE_COLORS" frontend/index.html`
Expected: a count of `4` or higher.

- [ ] **Step 6: Run the backend test suite (regression check)**

Run: `cd backend && python -m pytest tests/ -v`
Expected: `16 passed`.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "Add resource layer to dashboard (tracker 2.11)"
```

---

## Manual Verification (controller-run, not a subagent task)

No JS test framework exists in this project, so `node --check` and `grep` in Tasks 2-4 only catch syntax errors and confirm code landed — they don't prove the UI actually works. Before this branch is considered done, the controller (not a dispatched subagent) must:

1. Start the backend: `cd backend && python -m uvicorn app.main:app --reload`
2. Open `frontend/index.html` in a browser (via claude-in-chrome or equivalent)
3. Click "Send critical spike" and confirm:
   - A route line appears on the map (green if clear, red-dashed if blocked)
   - Resource markers (red/blue/purple/orange) are visible on the map
   - The new high-severity recommendation appears in the **Alerts** section
   - Clicking Approve or Reject on a card updates its status text and removes it from the Alerts section (it should still appear in the full Recommendations feed below)
4. Toggle each of the three layer checkboxes off and on, confirming the corresponding map layer/markers hide and reappear

This matches tracker 1.10's own precedent ("visually confirmed in browser") and the explicit instruction in the design spec's Testing section.
