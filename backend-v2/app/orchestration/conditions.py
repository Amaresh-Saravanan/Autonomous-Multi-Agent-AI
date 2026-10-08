"""Conditional routing (Phase 16). Beyond V1's "skip if source_type not in
triggers": dispatch agents (rescue/medical/shelter/route) don't run for a
trivial-severity event — a real behavioral improvement over V1, which ran
every agent on every event regardless of severity."""

from app.agents.base import AgentContext, BaseAgent

MIN_DISPATCH_SEVERITY = 0.3
DISPATCH_AGENT_IDS = {"AG-3", "AG-4", "AG-5", "AG-6"}


def should_run(agent: BaseAgent, context: AgentContext) -> bool:
    if not agent.can_handle(context):
        return False
    if agent.id in DISPATCH_AGENT_IDS:
        severity = context.blackboard.get("AG-1", {}).get("severity", context.severity)
        return severity >= MIN_DISPATCH_SEVERITY
    return True
