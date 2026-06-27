"""Lifecycle state machine, authorization, and idempotency (AH-004)."""

from agent_harness.state.commands import CommandLabel
from agent_harness.state.idempotency import build_idempotency_key
from agent_harness.state.machine import (
    AuthorizationError,
    StateMachine,
    TransitionError,
    TransitionRequest,
    TransitionResult,
)
from agent_harness.state.models import LifecycleState, Permission

__all__ = [
    "AuthorizationError",
    "CommandLabel",
    "LifecycleState",
    "Permission",
    "StateMachine",
    "TransitionError",
    "TransitionRequest",
    "TransitionResult",
    "build_idempotency_key",
]
