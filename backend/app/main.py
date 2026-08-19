"""FastAPI skeleton — Phase 0 vertical slice (TDD 5, tracker 0.4/0.9).

Loop: POST /ingest/{source_type} -> normalize -> AG-1 -> blackboard ->
push recommendation over WebSocket to any connected dashboard.
"""
from __future__ import annotations

import time

import os

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import alerts
from . import audit
from . import auth
from . import blackboard
from . import citizen_reports
from . import incidents
from . import metrics
from . import orchestrator
from . import recommendations
from . import severity_grid
from .normalizers import normalize
from .resources import HOSPITALS, SHELTERS, TEAMS, AMBULANCES
from agents import citizen as citizen_agent

# frontend-next/ (Next.js + Tailwind) runs its own dev server on :3000 and is
# the only frontend. Access control here is a Bearer token (app/auth.py), not
# a cookie, so CORS isn't the security boundary anyway -- default stays
# permissive-but-not-wildcard so a stray webpage can't ride a logged-in user's
# cookies (defense in depth), and is still overridable via env for a real
# deployment with a hosted frontend. (The retired Phase 0 frontend/index.html
# shell was a file:// page sending Origin "null"; that's no longer allowed.)
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:8000,http://localhost:3000"
).split(",")

app = FastAPI(title="Disaster Response Platform - Phase 2 slice")
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"],
)

_ws_clients: list[WebSocket] = []


@app.middleware("http")
async def _record_request_metrics(request: Request, call_next):
    """Times every request for GET /metrics (tracker 3.8) — one touch point
    instead of hand-instrumenting each route body."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    route = request.scope.get("route")
    path = route.path if route is not None else request.url.path
    metrics.record(path, duration_ms)
    return response


@app.get("/health")
def health():
    return {"status": "ok", "using_redis": blackboard.using_redis()}


@app.post("/auth/login")
def login(body: dict):
    """Open endpoint — this IS the auth (tracker 3.4)."""
    user = auth.authenticate(body.get("username", ""), body.get("password", ""))
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = auth.issue_token(user["username"], user["role"], user["agency"])
    return {"access_token": token, "token_type": "bearer"}


@app.get("/metrics")
def get_metrics(user: dict = Depends(auth.require_role("operator"))):
    """Observability (tracker 3.8): request counts/latency per route plus
    recommendation acceptance rate = approved / (approved + rejected) among
    decided recs (pending recs excluded from the ratio's denominator)."""
    result = metrics.summary()
    recs = recommendations.list_recs()
    approved = sum(1 for r in recs if r["status"] == "approved")
    rejected = sum(1 for r in recs if r["status"] == "rejected")
    decided = approved + rejected
    result["recommendation_acceptance_rate"] = (approved / decided) if decided else None
    return result


@app.get("/resources")
def get_resources(user: dict = Depends(auth.require_role("viewer"))):
    return {
        "hospitals": HOSPITALS,
        "shelters": SHELTERS,
        "teams": TEAMS,
        "ambulances": AMBULANCES,
    }


@app.post("/ingest/{source_type}")
async def ingest(source_type: str, raw: dict):
    event = normalize(source_type, raw)
    incident_id = raw.get("incident_id") or incidents.assign_incident(event)

    # Enrich the blackboard with resolved state/district for this incident
    inc = incidents.get(incident_id)
    if inc:
        blackboard.merge(
            incident_id,
            {"state": inc.get("state"), "district": inc.get("district")},
        )

    recs = orchestrator.run(incident_id, [event])

    if alerts.should_push(incident_id, recs):
        for client in list(_ws_clients):
            try:
                await client.send_json({"incident_id": incident_id, "recommendations": recs})
            except Exception:  # noqa: BLE001 - drop dead clients
                _ws_clients.remove(client)

    return {"event_id": event.event_id, "incident_id": incident_id, "recommendations": recs}


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str, user: dict = Depends(auth.require_role("viewer"))):
    return blackboard.get(incident_id)


@app.get("/incidents/{incident_id}/severity")
def get_severity_grid(incident_id: str, user: dict = Depends(auth.require_role("viewer"))):
    """DS-1 severity heat-map as GeoJSON (TDD 5)."""
    return severity_grid.as_geojson(incident_id)


@app.get("/recommendations")
def list_recommendations(status: str | None = None, user: dict = Depends(auth.require_role("viewer"))):
    recs = recommendations.list_recs(status)
    if user["role"] == "admin":
        return recs
    # ponytail: no agent sets target_agency yet, so this filter is currently a
    # no-op for all real recommendations (they're all target_agency=None,
    # visible to everyone); wire it once agents know their target agency.
    return [r for r in recs if r.get("target_agency") in (user["agency"], None)]


def _decide(rec_id: str, new_status: str, actor: str) -> dict:
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
    audit.record(actor, new_status, rec_id, before, rec)
    return rec


@app.post("/recommendations/{rec_id}/approve")
def approve_recommendation(rec_id: str, user: dict = Depends(auth.require_role("operator"))):
    return _decide(rec_id, "approved", user["username"])


@app.post("/recommendations/{rec_id}/reject")
def reject_recommendation(rec_id: str, user: dict = Depends(auth.require_role("operator"))):
    return _decide(rec_id, "rejected", user["username"])


@app.post("/citizen/chat")
def citizen_chat(body: dict):
    return citizen_agent.chat(body.get("message", ""), body.get("language", "en"))


@app.get("/citizen/reports")
def get_citizen_reports(
    incident_id: str | None = None,
    user: dict = Depends(auth.require_role("viewer")),
):
    """PRD UI-4: browse citizen reports with their computed trust/verification
    status (app/citizen_verification.py), instead of that score being thrown
    away after the ingest response."""
    return citizen_reports.list_reports(incident_id)


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; client doesn't need to send
    except WebSocketDisconnect:
        _ws_clients.remove(websocket)
