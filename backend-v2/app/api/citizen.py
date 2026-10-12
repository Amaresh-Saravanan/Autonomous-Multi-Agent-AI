"""Citizen chat (AG-7). Device-authenticated like ingestion (Phase 7) —
fixes V1 problem #11 ("citizen chat is open"). AG-7 is invoked directly
here, not through the orchestrator chain (CLAUDE.md: it's request/response,
not event-triggered)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.citizen_assistance.agent import CitizenAssistant
from app.agents.citizen_assistance.schemas import ChatRequest, ChatResponse
from app.infrastructure.llm import get_llm_service
from app.infrastructure.database import get_db
from app.models.citizen import CitizenReport
from app.models.security import Device, RoleEnum, User
from app.security.devices import require_device
from app.security.permissions import ROLE_RANK, require_role

router = APIRouter(prefix="/api/v1/citizen", tags=["citizen"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, device: Device = Depends(require_device("citizen"))) -> ChatResponse:
    assistant = CitizenAssistant(llm=get_llm_service())
    return assistant.chat(body)


def _mask_contact(contact: str | None, user: User) -> str:
    """Reporter contact is PII: operators and above see it, viewers do not."""
    if not contact:
        return "anonymous"
    if ROLE_RANK[user.role] >= ROLE_RANK[RoleEnum.OPERATOR]:
        return contact
    return "hidden"


@router.get("/reports")
def list_reports(
    incident_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.VIEWER)),
) -> list[dict]:
    """Citizen report inbox with verification status (PRD UI-4, SEC-4)."""
    stmt = select(CitizenReport)
    if incident_id is not None:
        stmt = stmt.where(CitizenReport.incident_id == incident_id)
    rows = db.scalars(stmt.order_by(CitizenReport.created_at.desc()).limit(500))
    return [
        {
            "event_id": str(r.event_id or r.id),
            "incident_id": str(r.incident_id) if r.incident_id else "",
            "reporter_id": _mask_contact(r.reporter_contact, user),
            "message": r.message,
            "claimed_severity": r.claimed_severity,
            "confidence": r.verification_score,
            "flagged_for_review": r.flagged_for_review,
            "timestamp": r.created_at.isoformat(),
        }
        for r in rows
    ]
