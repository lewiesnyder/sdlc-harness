from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from agent_harness.state.commands import CommandLabel
from agent_harness.state.idempotency import build_idempotency_key
from agent_harness.state.models import LifecycleState, Permission
from agent_harness.state.transitions import INTERNAL_EVENTS, TRANSITION_TABLE


class TransitionError(Exception):
    """Raised when a lifecycle transition is invalid or unauthorized."""


class AuthorizationError(TransitionError):
    """Raised when the actor lacks permission for a command."""


@dataclass(frozen=True)
class TransitionRequest:
    command: CommandLabel | str
    current_state: LifecycleState
    actor: str
    actor_permission: Permission
    repo_id: str
    pr_number: int
    head_sha: str
    plan_sha: str | None = None
    feedback_cutoff: str | None = None
    expected_head_sha: str | None = None
    expected_plan_sha: str | None = None
    idempotency_key: str | None = None

    def resolved_idempotency_key(self) -> str:
        if self.idempotency_key:
            return self.idempotency_key
        operation = (
            self.command.value
            if isinstance(self.command, CommandLabel)
            else str(self.command)
        )
        return build_idempotency_key(
            self.repo_id,
            self.pr_number,
            operation,
            self.head_sha,
            self.plan_sha,
            self.feedback_cutoff,
        )


@dataclass
class TransitionResult:
    accepted: bool
    from_state: LifecycleState
    to_state: LifecycleState | None
    idempotency_key: str
    duplicate: bool = False
    message: str = ""
    consumed_command_label: str | None = None
    state_label: str | None = None
    recorded_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class StateRecord:
    state: LifecycleState
    head_sha: str
    plan_sha: str | None = None
    last_idempotency_key: str | None = None
    active_run_id: str | None = None


class StateMachine:
    """Validates lifecycle transitions with authorization and idempotency."""

    def __init__(
        self,
        allowed_permissions: list[Permission] | None = None,
        min_permission: Permission = Permission.WRITE,
    ) -> None:
        self.allowed_permissions = allowed_permissions or [
            Permission.WRITE,
            Permission.MAINTAIN,
            Permission.ADMIN,
        ]
        self.min_permission = min_permission
        self._records: dict[str, StateRecord] = {}
        self._idempotency_index: dict[str, TransitionResult] = {}

    def _feature_key(self, repo_id: str, feature_id: str) -> str:
        return f"{repo_id}:{feature_id}"

    def get_record(self, repo_id: str, feature_id: str) -> StateRecord | None:
        return self._records.get(self._feature_key(repo_id, feature_id))

    def compare_and_set(
        self,
        repo_id: str,
        feature_id: str,
        expected_state: LifecycleState,
        new_record: StateRecord,
    ) -> bool:
        key = self._feature_key(repo_id, feature_id)
        current = self._records.get(key)
        if current is None:
            if expected_state != LifecycleState.READY:
                return False
        elif current.state != expected_state:
            return False
        self._records[key] = new_record
        return True

    def authorize(self, request: TransitionRequest) -> None:
        if str(request.command) in INTERNAL_EVENTS:
            return
        if request.actor_permission not in self.allowed_permissions:
            raise AuthorizationError(
                f"actor '{request.actor}' permission '{request.actor_permission.value}' "
                "is not in the allowed set"
            )
        if not request.actor_permission.satisfies(self.min_permission):
            raise AuthorizationError(
                f"actor '{request.actor}' requires at least "
                f"'{self.min_permission.value}' permission"
            )

    def validate_shas(self, request: TransitionRequest) -> None:
        if request.expected_head_sha and request.expected_head_sha != request.head_sha:
            raise TransitionError(
                "head SHA changed since authorization; a new command is required"
            )
        if (
            request.command == CommandLabel.AGENT_IMPLEMENT
            and request.expected_plan_sha
            and request.plan_sha
            and request.expected_plan_sha != request.plan_sha
        ):
            raise TransitionError(
                "plan SHA changed since authorization; re-add agent-implement"
            )

    def transition(
        self,
        request: TransitionRequest,
        feature_id: str,
    ) -> TransitionResult:
        idem_key = request.resolved_idempotency_key()
        if idem_key in self._idempotency_index:
            prior = self._idempotency_index[idem_key]
            return TransitionResult(
                accepted=prior.accepted,
                from_state=prior.from_state,
                to_state=prior.to_state,
                idempotency_key=idem_key,
                duplicate=True,
                message="duplicate event; returning existing logical run",
                consumed_command_label=prior.consumed_command_label,
                state_label=prior.state_label,
            )

        self.authorize(request)
        self.validate_shas(request)

        command_key: CommandLabel | str = request.command
        lookup = (command_key, request.current_state)
        target = TRANSITION_TABLE.get(lookup)
        if target is None:
            raise TransitionError(
                f"invalid transition: command '{request.command}' "
                f"not allowed from state '{request.current_state.value}'"
            )

        consumed_label = None
        state_label = None
        if isinstance(request.command, CommandLabel):
            consumed_label = request.command.value
            state_label = request.command.state_label()

        result = TransitionResult(
            accepted=True,
            from_state=request.current_state,
            to_state=target,
            idempotency_key=idem_key,
            message=f"transition {request.current_state.value} -> {target.value}",
            consumed_command_label=consumed_label,
            state_label=state_label,
        )
        self._idempotency_index[idem_key] = result

        record = StateRecord(
            state=target,
            head_sha=request.head_sha,
            plan_sha=request.plan_sha,
            last_idempotency_key=idem_key,
        )
        self._records[self._feature_key(request.repo_id, feature_id)] = record
        return result
