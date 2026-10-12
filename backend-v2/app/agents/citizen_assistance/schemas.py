"""AG-7 chat contracts (Phase 5/15)."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    language: str = "en"


class ChatResponse(BaseModel):
    reply: str
    language: str  # language the reply is actually written in
    reasoning_mode: str  # "llm" | "retrieval_fallback" | "unavailable"
    sources: list[str]
    # True when the reply is NOT in the language the citizen asked for (no
    # translation available and no LLM): the UI must say so.
    language_fallback: bool = False
