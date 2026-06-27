from __future__ import annotations

from datetime import datetime, timezone

from agent_harness.provider.contract import (
    ErrorRef,
    Operation,
    ProviderAdapter,
    ProviderCapabilities,
    RunHandle,
    RunRequest,
    RunResult,
    RunOutput,
    RunStatus,
    UsageRef,
)


class FakeProvider(ProviderAdapter):
    """Deterministic in-process provider for contract and transition tests."""

    def __init__(self, name: str = "fake") -> None:
        self.name = name
        self._handles: dict[str, RunRequest] = {}
        self._results: dict[str, RunResult] = {}

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name,
            cloud_execution=False,
            async_polling=False,
            follow_up=False,
            native_git_push=True,
            read_only_mode=True,
            structured_output=True,
            video_capture=True,
            usage_reporting=True,
            supported_operations=list(Operation),
        )

    def submit(self, request: RunRequest) -> RunHandle:
        run_id = self.new_run_id()
        handle = RunHandle(
            run_id=run_id,
            provider=self.name,
            provider_run_id=f"{self.name}-{run_id[:8]}",
            status=RunStatus.RUNNING,
        )
        self._handles[handle.run_id] = request
        self._results[handle.run_id] = self._build_result(request, handle)
        return handle

    def status(self, handle: RunHandle) -> RunStatus:
        result = self._results.get(handle.run_id)
        if result is None:
            return RunStatus.FAILED
        return result.status

    def result(self, handle: RunHandle) -> RunResult:
        result = self._results.get(handle.run_id)
        if result is None:
            raise KeyError(f"unknown run handle: {handle.run_id}")
        return result

    def cancel(self, handle: RunHandle) -> RunStatus:
        result = self._results.get(handle.run_id)
        if result:
            cancelled = result.model_copy(update={"status": RunStatus.CANCELLED})
            self._results[handle.run_id] = cancelled
        return RunStatus.CANCELLED

    def _build_result(self, request: RunRequest, handle: RunHandle) -> RunResult:
        now = datetime.now(timezone.utc)
        feature_id = request.work_item.feature_id
        changed_paths: list[str] = []
        commits: list[str] = []
        summary = f"fake {request.operation.value.lower()} run completed"

        if request.operation in {Operation.PLAN, Operation.REPLAN}:
            plan_path = request.context.plan_path or f".agent/plans/{feature_id}.md"
            changed_paths = [plan_path]
            commits = [f"plan-{feature_id}-fake"]
            summary = f"committed plan artifact at {plan_path}"
        elif request.operation == Operation.IMPLEMENT:
            changed_paths = ["src/example.py"]
            commits = [f"impl-{feature_id}-fake"]
            summary = "implementation changes committed to feature branch"
        elif request.operation == Operation.DEMO:
            changed_paths = []
            summary = "demo artifact published to github-artifact sink"
        elif request.operation == Operation.REVIEW:
            changed_paths = []
            summary = "read-only review completed with no blocking findings"

        if request.operation == Operation.REVIEW and request.policy.profile == "fail-review":
            return RunResult(
                run_id=handle.run_id,
                provider=self.name,
                provider_run_id=handle.provider_run_id,
                operation=request.operation,
                status=RunStatus.FAILED,
                started_at=now,
                completed_at=now,
                input={
                    "base_sha": request.repository.base_sha,
                    "head_sha": request.repository.head_sha,
                    "plan_sha": request.context.plan_sha,
                },
                output=RunOutput(summary="review failed by policy"),
                usage=UsageRef(model="fake-model", input_tokens=10, output_tokens=5, cost_usd=0.0),
                error=ErrorRef(
                    category="policy",
                    retryable=False,
                    message="blocking finding",
                ),
            )

        return RunResult(
            run_id=handle.run_id,
            provider=self.name,
            provider_run_id=handle.provider_run_id,
            operation=request.operation,
            status=RunStatus.SUCCEEDED,
            started_at=now,
            completed_at=now,
            input={
                "base_sha": request.repository.base_sha,
                "head_sha": request.repository.head_sha,
                "plan_sha": request.context.plan_sha,
            },
            output=RunOutput(
                resulting_head_sha=request.repository.head_sha,
                commits=commits,
                changed_paths=changed_paths,
                summary=summary,
            ),
            usage=UsageRef(model="fake-model", input_tokens=100, output_tokens=50, cost_usd=0.01),
        )
