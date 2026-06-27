from __future__ import annotations

from agent_harness.config.models import HarnessConfig
from agent_harness.provider.contract import (
    Operation,
    ProviderAdapter,
    ProviderCapabilities,
    RunHandle,
    RunRequest,
    RunResult,
)
from agent_harness.provider.fake import FakeProvider


class RouterError(Exception):
    """Raised when provider routing or capability validation fails."""


STAGE_OPERATION_MAP = {
    "plan": Operation.PLAN,
    "replan": Operation.REPLAN,
    "implement": Operation.IMPLEMENT,
    "demo": Operation.DEMO,
    "review": Operation.REVIEW,
}


class ProviderRouter:
    """Routes normalized run requests to configured provider adapters."""

    def __init__(
        self,
        config: HarnessConfig,
        adapters: dict[str, ProviderAdapter] | None = None,
    ) -> None:
        self.config = config
        self.adapters = adapters or {}
        self._ensure_default_fake_adapter()

    def _ensure_default_fake_adapter(self) -> None:
        for name, provider in self.config.providers.items():
            if provider.adapter == "fake" and name not in self.adapters:
                self.adapters[name] = FakeProvider(name=name)

    def capabilities(self, provider_name: str) -> ProviderCapabilities:
        adapter = self._get_adapter(provider_name)
        return adapter.capabilities()

    def route_stage(self, stage_name: str, request: RunRequest) -> RunResult:
        if stage_name not in self.config.stages:
            raise RouterError(f"unknown stage: {stage_name}")
        stage = self.config.stages[stage_name]
        expected_operation = STAGE_OPERATION_MAP.get(stage_name)
        if expected_operation and request.operation != expected_operation:
            raise RouterError(
                f"stage '{stage_name}' expects operation {expected_operation.value}, "
                f"got {request.operation.value}"
            )

        adapter = self._get_adapter(stage.provider)
        caps = adapter.capabilities()
        self._validate_capabilities(stage_name, stage.read_only, request.operation, caps)

        handle = adapter.submit(request)
        return adapter.result(handle)

    def submit_stage(self, stage_name: str, request: RunRequest) -> RunHandle:
        stage = self.config.stages[stage_name]
        adapter = self._get_adapter(stage.provider)
        self._validate_capabilities(
            stage_name,
            stage.read_only,
            request.operation,
            adapter.capabilities(),
        )
        return adapter.submit(request)

    def _get_adapter(self, provider_name: str) -> ProviderAdapter:
        if provider_name not in self.config.providers:
            raise RouterError(f"unknown provider: {provider_name}")
        if provider_name not in self.adapters:
            raise RouterError(
                f"no adapter registered for provider '{provider_name}'"
            )
        return self.adapters[provider_name]

    def _validate_capabilities(
        self,
        stage_name: str,
        read_only: bool,
        operation: Operation,
        caps: ProviderCapabilities,
    ) -> None:
        if operation not in caps.supported_operations:
            raise RouterError(
                f"provider '{caps.name}' does not support operation {operation.value}"
            )
        if read_only and not caps.read_only_mode and operation == Operation.REVIEW:
            raise RouterError(
                f"stage '{stage_name}' requires read-only review capability"
            )
        if operation == Operation.DEMO and not caps.video_capture:
            raise RouterError(
                f"stage '{stage_name}' requires demo/video capability from provider '{caps.name}'"
            )

        stage = self.config.stages[stage_name]
        timeout_seconds = self.config.stage_timeout_seconds(stage_name)
        if timeout_seconds > caps.max_runtime_seconds:
            raise RouterError(
                f"stage '{stage_name}' timeout exceeds provider max runtime"
            )

        if stage.max_cost_usd is not None and not caps.usage_reporting:
            raise RouterError(
                f"stage '{stage_name}' has cost budget but provider '{caps.name}' "
                "does not report usage"
            )
