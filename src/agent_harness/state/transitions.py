from __future__ import annotations

from agent_harness.state.commands import CommandLabel
from agent_harness.state.models import LifecycleState

# Maps (command, source_state) -> target_state. Absence means invalid transition.
TRANSITION_TABLE: dict[tuple[CommandLabel | str, LifecycleState], LifecycleState] = {
    ("agent-start", LifecycleState.READY): LifecycleState.CLAIMING,
    (CommandLabel.AGENT_START, LifecycleState.READY): LifecycleState.CLAIMING,
    ("bootstrap-complete", LifecycleState.CLAIMING): LifecycleState.PLANNING,
    ("plan-complete", LifecycleState.PLANNING): LifecycleState.PLAN_REVIEW,
    (CommandLabel.AGENT_REPLAN, LifecycleState.PLAN_REVIEW): LifecycleState.REPLANNING,
    ("replan-complete", LifecycleState.REPLANNING): LifecycleState.PLAN_REVIEW,
    (CommandLabel.AGENT_IMPLEMENT, LifecycleState.PLAN_REVIEW): LifecycleState.IMPLEMENTING,
    ("implement-complete", LifecycleState.IMPLEMENTING): LifecycleState.VERIFYING,
    ("verification-pass", LifecycleState.VERIFYING): LifecycleState.IMPLEMENTATION_REVIEW,
    ("verification-fail", LifecycleState.VERIFYING): LifecycleState.CHANGES_REQUESTED,
    (CommandLabel.AGENT_IMPLEMENT, LifecycleState.IMPLEMENTATION_REVIEW): LifecycleState.IMPLEMENTING,
    (CommandLabel.AGENT_DEMO, LifecycleState.IMPLEMENTATION_REVIEW): LifecycleState.DEMOING,
    (CommandLabel.AGENT_REVIEW, LifecycleState.IMPLEMENTATION_REVIEW): LifecycleState.REVIEWING,
    ("demo-complete", LifecycleState.DEMOING): LifecycleState.DEMO_READY,
    (CommandLabel.AGENT_REVIEW, LifecycleState.DEMO_READY): LifecycleState.REVIEWING,
    (CommandLabel.AGENT_IMPLEMENT, LifecycleState.DEMO_READY): LifecycleState.IMPLEMENTING,
    ("review-pass", LifecycleState.REVIEWING): LifecycleState.READY_TO_MERGE,
    ("review-fail", LifecycleState.REVIEWING): LifecycleState.CHANGES_REQUESTED,
    (CommandLabel.AGENT_IMPLEMENT, LifecycleState.CHANGES_REQUESTED): LifecycleState.IMPLEMENTING,
    (CommandLabel.AGENT_REPLAN, LifecycleState.CHANGES_REQUESTED): LifecycleState.REPLANNING,
    (CommandLabel.AGENT_IMPLEMENT, LifecycleState.READY_TO_MERGE): LifecycleState.IMPLEMENTING,
    (CommandLabel.AGENT_REVIEW, LifecycleState.READY_TO_MERGE): LifecycleState.REVIEWING,
    ("human-merge", LifecycleState.READY_TO_MERGE): LifecycleState.MERGED,
    ("finalize-start", LifecycleState.MERGED): LifecycleState.FINALIZING,
    ("finalize-complete", LifecycleState.FINALIZING): LifecycleState.DONE,
    (CommandLabel.AGENT_RETRY, LifecycleState.BLOCKED): LifecycleState.PLANNING,
    (CommandLabel.AGENT_CANCEL, LifecycleState.BLOCKED): LifecycleState.CANCELLED,
}

INTERNAL_EVENTS = {
    "bootstrap-complete",
    "plan-complete",
    "replan-complete",
    "implement-complete",
    "verification-pass",
    "verification-fail",
    "demo-complete",
    "review-pass",
    "review-fail",
    "human-merge",
    "finalize-start",
    "finalize-complete",
}
