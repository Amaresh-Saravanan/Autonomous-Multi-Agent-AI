"""Uniform agent contract (TDD 4.1). Every agent returns a Recommendation with
non-empty evidence + rationale — enforced by Recommendation.validate_explainable().
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.models import Event, Recommendation


class Agent(ABC):
    id: str
    # PRD AC-2 / TDD 4.1 triggers(): which event source_types wake this agent.
    # Default = everything, for agents that must react to any signal (AG-1
    # assesses, AG-8 summarizes). Response/dispatch agents narrow this.
    triggers: frozenset[str] = frozenset({"iot", "weather", "satellite"})

    @abstractmethod
    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        """Read blackboard `state`, react to `events`, return one Recommendation."""
        raise NotImplementedError
