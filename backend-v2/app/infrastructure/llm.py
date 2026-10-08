"""LLM service (Phase 12). Replaces V1 `llm.py` completely.

V1 problems fixed here:
- hardcoded `mixtral-8x7b-32768` → `LLM_MODEL` config, no model name in code
- import-time connectivity probe → lazy, only on first `reason()` call
- failures returned as a string the agent then stored as a successful
  rationale → every call returns a typed `LLMResult` with an explicit
  `status`; a caller that doesn't check `status` gets `content=None`
  instead of a plausible-looking fallback string, so silently treating a
  failure as a result is a visible bug, not a quiet one.
"""

import logging
import time
from functools import lru_cache
from typing import Literal, Protocol

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import get_settings

logger = logging.getLogger("app.llm")


class LLMResult(BaseModel):
    status: Literal["SUCCESS", "DEGRADED"]
    reasoning_mode: Literal["llm", "deterministic_fallback"]
    fallback_used: bool
    content: str | None = None
    model: str | None = None
    provider: str | None = None
    latency_ms: float
    fallback_reason: str | None = None


class LLMClient(Protocol):
    def complete(self, prompt: str, *, model: str, max_tokens: int) -> str: ...


class GroqClient:
    """Thin wrapper so `LLMService` doesn't import the `groq` SDK shape
    directly — keeps the provider swappable."""

    def __init__(self, api_key: str):
        from groq import Groq

        self._client = Groq(api_key=api_key)

    def complete(self, prompt: str, *, model: str, max_tokens: int) -> str:
        resp = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


class LLMService:
    def __init__(self, client: LLMClient | None, *, model: str, provider_name: str, max_retries: int = 2):
        self._client = client
        self.model = model
        self.provider_name = provider_name
        self._max_retries = max_retries

    def reason(self, prompt: str, max_tokens: int = 256) -> LLMResult:
        start = time.monotonic()

        if self._client is None:
            return self._degraded(start, "LLM provider not configured (missing API key or client)")

        try:
            content = self._call_with_retry(prompt, max_tokens)
        except Exception as exc:
            logger.warning("LLM call failed after retries: %s", exc)
            return self._degraded(start, str(exc))

        return LLMResult(
            status="SUCCESS",
            reasoning_mode="llm",
            fallback_used=False,
            content=content,
            model=self.model,
            provider=self.provider_name,
            latency_ms=(time.monotonic() - start) * 1000,
        )

    def _call_with_retry(self, prompt: str, max_tokens: int) -> str:
        @retry(stop=stop_after_attempt(self._max_retries), wait=wait_fixed(0.5), reraise=True)
        def _call() -> str:
            return self._client.complete(prompt, model=self.model, max_tokens=max_tokens)

        return _call()

    def _degraded(self, start: float, reason: str) -> LLMResult:
        return LLMResult(
            status="DEGRADED",
            reasoning_mode="deterministic_fallback",
            fallback_used=True,
            fallback_reason=reason,
            model=self.model,
            provider=self.provider_name,
            latency_ms=(time.monotonic() - start) * 1000,
        )


@lru_cache
def get_llm_service() -> LLMService:
    settings = get_settings()
    client: LLMClient | None = None
    if settings.llm_provider == "groq" and settings.groq_api_key:
        client = GroqClient(settings.groq_api_key)
    return LLMService(client, model=settings.llm_model, provider_name=settings.llm_provider)
