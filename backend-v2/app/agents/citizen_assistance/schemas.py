"""AG-7 chat contracts (Phase 5/15)."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    language: str = "en"


class ChatResponse(BaseModel):
    reply: str
    language: str
    reasoning_mode: str  # "llm" | "retrieval_fallback" | "unavailable"
    sources: list[str]
