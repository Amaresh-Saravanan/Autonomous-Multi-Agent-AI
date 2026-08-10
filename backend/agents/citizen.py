"""AG-7 Citizen Assistance — multilingual chat, on-demand (not part of the
ingest pipeline). Uses LLM if available; canned fallback otherwise.
"""
from __future__ import annotations
from app import llm

FALLBACK_MSG = (
    "Emergency guidance is currently limited (LLM unavailable). "
    "For immediate danger, contact local emergency services directly."
)


def chat(message: str, language: str = "en") -> dict:
    if llm.available():
        prompt = (
            f"You are an emergency assistance chatbot. Respond in language code '{language}'. "
            f"Be calm, concise, and actionable. Citizen message: {message}"
        )
        reply = llm.reason(prompt, max_tokens=200)
    else:
        reply = FALLBACK_MSG
    return {"reply": reply, "language": language, "llm_used": llm.available()}
