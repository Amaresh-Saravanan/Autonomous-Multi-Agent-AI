"""Typed LLM output for AG-1 (Phase 15). Parsing through a schema instead of
bare `json.loads` + broad except (V1 problem #8: the except clause read an
unbound `response` variable) means a malformed LLM reply raises a clean
`pydantic.ValidationError` the agent can catch deliberately."""

from pydantic import BaseModel, Field


class AG1LLMOutput(BaseModel):
    severity: float = Field(ge=0.0, le=1.0)
    action: str = "monitor"
    rationale: str = "LLM assessment."
