"""Generic ConflictDetector (Phase 19). V1 hardcoded exactly one check
(AG-5 shelter vs AG-6 destination); V2 makes that one check a registered
`ConflictRule` so adding route/medical/priority/evacuation rules later
doesn't require touching the detection loop. Conflicts are returned, never
silently resolved — a human decides."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Conflict:
    category: str
    agents: list[str]
    target: str
    values: dict[str, str]
    rationale: str


class ConflictRule(Protocol):
    def check(self, blackboard: dict) -> Conflict | None: ...


class ShelterDestinationMismatch:
    """AG-5 (capacity-aware shelter allocation) vs AG-6 (distance-only
    routing) — the one pair that can genuinely target the same resource
    and disagree, ported from V1."""

    category = "shelter_conflict"

    def check(self, blackboard: dict) -> Conflict | None:
        ag5 = blackboard.get("AG-5", {}).get("details", {}).get("shelter") or {}
        ag6 = blackboard.get("AG-6", {}).get("details", {}).get("destination") or {}
        ag5_id, ag6_id = ag5.get("id"), ag6.get("id")
        if not ag5_id or not ag6_id or ag5_id == ag6_id:
            return None
        return Conflict(
            category=self.category,
            agents=["AG-5", "AG-6"],
            target="evacuation_shelter",
            values={"AG-5": ag5_id, "AG-6": ag6_id},
            rationale=(
                f"AG-5 allocates evacuees to shelter {ag5_id} (capacity-aware) "
                f"but AG-6 routes them to shelter {ag6_id} (distance-only) — human must reconcile."
            ),
        )


DEFAULT_RULES: list[ConflictRule] = [ShelterDestinationMismatch()]


class ConflictDetector:
    def __init__(self, rules: list[ConflictRule] | None = None):
        self._rules = rules if rules is not None else DEFAULT_RULES

    def detect(self, blackboard: dict) -> list[Conflict]:
        conflicts = []
        for rule in self._rules:
            conflict = rule.check(blackboard)
            if conflict is not None:
                conflicts.append(conflict)
        return conflicts
