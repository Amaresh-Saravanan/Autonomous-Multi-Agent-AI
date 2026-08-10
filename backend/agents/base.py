"""Uniform agent contract (TDD 4.1). Every agent returns a Recommendation with
non-empty evidence + rationale — enforced by Recommendation.validate_explainable().
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.models import Event, Recommendation


class Agent(ABC):
    id: str

    @abstractmethod
    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        """Read blackboard `state`, react to `events`, return one Recommendation."""
        raise NotImplementedError
