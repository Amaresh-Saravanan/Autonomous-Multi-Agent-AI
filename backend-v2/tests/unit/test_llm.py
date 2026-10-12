from app.infrastructure.llm import LLMService


class _SuccessClient:
    def complete(self, prompt: str, *, model: str, max_tokens: int) -> str:
        return "it's a flood, severity high"


class _FailingClient:
    def complete(self, prompt: str, *, model: str, max_tokens: int) -> str:
        raise RuntimeError("upstream timeout")


def test_successful_call_is_never_disguised_as_degraded():
    service = LLMService(_SuccessClient(), model="llama-3.3-70b-versatile", provider_name="groq")
    result = service.reason("describe the incident")
    assert result.status == "SUCCESS"
    assert result.reasoning_mode == "llm"
    assert result.fallback_used is False
    assert result.content == "it's a flood, severity high"


def test_failed_call_is_never_disguised_as_a_successful_rationale():
    service = LLMService(_FailingClient(), model="llama-3.3-70b-versatile", provider_name="groq", max_retries=1)
    result = service.reason("describe the incident")
    assert result.status == "DEGRADED"
    assert result.reasoning_mode == "deterministic_fallback"
    assert result.fallback_used is True
    assert result.content is None
    assert "upstream timeout" in result.fallback_reason


def test_no_client_configured_is_degraded_not_crashed():
    service = LLMService(None, model="llama-3.3-70b-versatile", provider_name="groq")
    result = service.reason("describe the incident")
    assert result.status == "DEGRADED"
    assert result.fallback_used is True
    assert "not configured" in result.fallback_reason
