"""LLM prompt for AG-1 (Phase 15, ported from V1)."""


def build_prompt(events_summary: str) -> str:
    return f"""Analyze these disaster-related sensor/weather events and assess severity (0.0=low, 1.0=critical).
Return JSON: {{"severity": <float>, "action": "<str>", "rationale": "<str>"}}

Events:
{events_summary}

Be concise."""
