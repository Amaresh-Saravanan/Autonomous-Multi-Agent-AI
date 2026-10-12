"""AG-8 output shape (Phase 15)."""

from pydantic import BaseModel


class SituationSummary(BaseModel):
    major_risks: list[str]
    max_severity: float
    priorities: list[str]
