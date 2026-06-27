from __future__ import annotations

from enum import Enum


class CommandLabel(str, Enum):
    AGENT_START = "agent-start"
    AGENT_PLAN = "agent-plan"
    AGENT_REPLAN = "agent-replan"
    AGENT_IMPLEMENT = "agent-implement"
    AGENT_DEMO = "agent-demo"
    AGENT_REVIEW = "agent-review"
    AGENT_RETRY = "agent-retry"
    AGENT_CANCEL = "agent-cancel"

    def state_label(self) -> str | None:
        mapping = {
            CommandLabel.AGENT_PLAN: "agent-state/planning",
            CommandLabel.AGENT_REPLAN: "agent-state/planning",
            CommandLabel.AGENT_IMPLEMENT: "agent-state/implementing",
            CommandLabel.AGENT_DEMO: "agent-state/demoing",
            CommandLabel.AGENT_REVIEW: "agent-state/reviewing",
        }
        return mapping.get(self)
