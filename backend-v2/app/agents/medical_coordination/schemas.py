"""AG-4 output shape (Phase 15)."""

from pydantic import BaseModel


class MedicalAllocation(BaseModel):
    hospital_id: str
    hospital_name: str
    casualty_estimate: int
    ambulance_id: str | None = None
