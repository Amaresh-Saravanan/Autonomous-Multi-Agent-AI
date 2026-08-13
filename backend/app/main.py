"""FastAPI skeleton — Phase 0 vertical slice (TDD 5, tracker 0.4/0.9).

Loop: POST /ingest/{source_type} -> normalize -> AG-1 -> blackboard ->
push recommendation over WebSocket to any connected dashboard.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import alerts
from . import audit
from . import blackboard
from . import orchestrator
from . import recommendations
from . import severity_grid
from .normalizers import normalize
from .resources import HOSPITALS, SHELTERS, TEAMS, AMBULANCES
from agents import citizen as citizen_agent

app = FastAPI(title="Disaster Response Platform - Phase 2 slice")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_ws_clients: list[WebSocket] = []


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


@app.post("/ingest/{source_type}")
async def ingest(source_type: str, raw: dict):
    event = normalize(source_type, raw)
    incident_id = raw.get("incident_id", "default")

    recs = orchestrator.run(incident_id, [event])

    if alerts.should_push(incident_id, recs):
        conflicts = blackboard.get(incident_id).get("conflicts", [])
        for client in list(_ws_clients):
            try:
                await client.send_json({
                    "incident_id": incident_id,
                    "recommendations": recs,
                    "conflicts": conflicts,
                })
            except Exception:  # noqa: BLE001 - drop dead clients
                _ws_clients.remove(client)

    return {"event_id": event.event_id, "incident_id": incident_id, "recommendations": recs}


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    return blackboard.get(incident_id)


@app.get("/incidents/{incident_id}/severity")
def get_severity_grid(incident_id: str):
    """DS-1 severity heat-map as GeoJSON (TDD 5)."""
    return severity_grid.as_geojson(incident_id)


@app.get("/incidents/{incident_id}/conflicts")
def get_conflicts(incident_id: str):
    """Tracker 2.2 / AC-4: surfaced agent disagreements for this incident."""
    return blackboard.get(incident_id).get("conflicts", [])


@app.get("/recommendations")
def list_recommendations(status: str | None = None):
    return recommendations.list_recs(status)


def _decide(rec_id: str, new_status: str) -> dict:
    """Human approve/reject (tracker 2.9, PRD AC-5) — audited (TDD 5)."""
    rec = recommendations.get(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    before = dict(rec)
    rec["status"] = new_status
    recommendations.record(rec)
    # Only overwrite the blackboard if this rec is still the agent's latest —
    # a stale decision must not resurrect an older severity/action.
    current = blackboard.get(rec["incident_id"]).get(rec["agent_id"])
    if current and current.get("rec_id") == rec_id:
        blackboard.merge(rec["incident_id"], {rec["agent_id"]: rec})
    # ponytail: no RBAC yet (tracker 3.4), so actor is a fixed placeholder.
    audit.record("operator", new_status, rec_id, before, rec)
    return rec


@app.post("/recommendations/{rec_id}/approve")
def approve_recommendation(rec_id: str):
    return _decide(rec_id, "approved")


@app.post("/recommendations/{rec_id}/reject")
def reject_recommendation(rec_id: str):
    return _decide(rec_id, "rejected")


@app.post("/citizen/chat")
def citizen_chat(body: dict):
    return citizen_agent.chat(body.get("message", ""), body.get("language", "en"))


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; client doesn't need to send
    except WebSocketDisconnect:
        _ws_clients.remove(websocket)
