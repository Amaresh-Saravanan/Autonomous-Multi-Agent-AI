"""LLM client — Groq for Phase 1+ (optional, free tier).
Falls back to rule-based reasoning if key is missing or API unreachable.
"""
from __future__ import annotations
import os

_client = None
_available = False

if os.getenv("GROQ_API_KEY"):
    try:
        from groq import Groq  # type: ignore
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
        # Test connectivity
        _client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        _available = True
    except Exception as e:
        print(f"Groq init failed (will use rule-based fallback): {e}")


def available() -> bool:
    return _available


def reason(prompt: str, max_tokens: int = 256) -> str:
    """Call Groq Mixtral-8x7B. If unavailable, return a placeholder."""
    if not _available:
        return "[rule-based fallback; set GROQ_API_KEY to enable LLM reasoning]"
    try:
        resp = _client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"[LLM call failed: {e}]"
