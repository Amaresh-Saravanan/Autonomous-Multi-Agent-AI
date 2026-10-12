"""Citizen chat (AG-7). Device-authenticated like ingestion (Phase 7) —
fixes V1 problem #11 ("citizen chat is open"). AG-7 is invoked directly
here, not through the orchestrator chain (CLAUDE.md: it's request/response,
not event-triggered)."""

from fastapi import APIRouter, Depends

from app.agents.citizen_assistance.agent import CitizenAssistant
from app.agents.citizen_assistance.schemas import ChatRequest, ChatResponse
from app.infrastructure.llm import get_llm_service
from app.models.security import Device
from app.security.devices import require_device

router = APIRouter(prefix="/api/v1/citizen", tags=["citizen"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, device: Device = Depends(require_device("citizen"))) -> ChatResponse:
    assistant = CitizenAssistant(llm=get_llm_service())
    return assistant.chat(body)
