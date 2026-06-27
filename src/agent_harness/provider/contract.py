from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Operation(str, Enum):
    PLAN = "PLAN"
    REPLAN = "REPLAN"
    IMPLEMENT = "IMPLEMENT"
    DEMO = "DEMO"
    REVIEW = "REVIEW"


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED = "BLOCKED"


class ProviderCapabilities(BaseModel):
    name: str
    cloud_execution: bool = False
    async_polling: bool = True
    follow_up: bool = False
    native_git_push: bool = False
    read_only_mode: bool = False
    structured_output: bool = True
    video_capture: bool = False
    usage_reporting: bool = False
    max_runtime_seconds: int = 7200
    supported_operations: list[Operation] = Field(
        default_factory=lambda: list(Operation)
    )


class RepositoryRef(BaseModel):
    owner: str
    name: str
    default_branch: str
    base_sha: str
    head_sha: str
    feature_branch: str


class WorkItemRef(BaseModel):
    feature_id: str
    pull_request_number: int
    issue_number: int | None = None


class AuthorizationRef(BaseModel):
    actor: str
    actor_permission: str
    authorized_at: datetime


class ContextRef(BaseModel):
    manifest_uri: str
    plan_path: str | None = None
    plan_sha: str | None = None
    feedback_cutoff: datetime | None = None


class PolicyRef(BaseModel):
    profile: str
    allowed_paths: list[str] = Field(default_factory=list)
    protected_paths: list[str] = Field(default_factory=list)
    network_profile: str = "package-registries-only"
    tool_profile: str = "default"
    timeout_seconds: int = 3600
    max_cost_usd: float | None = None
    max_turns: int | None = None


class OutputSpec(BaseModel):
    required_schema: str
    commit_allowed: bool
    artifact_sink: str | None = None


class RunRequest(BaseModel):
    schema_version: str = "1.0"
    operation: Operation
    idempotency_key: str
    repository: RepositoryRef
    work_item: WorkItemRef
    authorization: AuthorizationRef
    context: ContextRef
    policy: PolicyRef
    output: OutputSpec
    telemetry: dict[str, str | None] = Field(default_factory=dict)

    def model_dump_normalized(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["authorization"]["authorized_at"] = self.authorization.authorized_at.isoformat()
        if self.context.feedback_cutoff:
            data["context"]["feedback_cutoff"] = self.context.feedback_cutoff.isoformat()
        return data


class RunHandle(BaseModel):
    run_id: str
    provider: str
    provider_run_id: str
    status: RunStatus = RunStatus.PENDING


class ArtifactRef(BaseModel):
    kind: str
    uri: str
    sha256: str
    expires_at: datetime | None = None


class RunOutput(BaseModel):
    resulting_head_sha: str | None = None
    commits: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    structured_result_uri: str | None = None
    summary: str = ""


class UsageRef(BaseModel):
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class ErrorRef(BaseModel):
    category: str | None = None
    retryable: bool | None = None
    message: str | None = None


class RunResult(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    provider: str
    provider_run_id: str
    operation: Operation
    status: RunStatus
    started_at: datetime
    completed_at: datetime
    input: dict[str, str | None]
    output: RunOutput
    usage: UsageRef = Field(default_factory=UsageRef)
    error: ErrorRef | None = None

    def model_dump_normalized(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ProviderAdapter(ABC):
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def submit(self, request: RunRequest) -> RunHandle:
        raise NotImplementedError

    @abstractmethod
    def status(self, handle: RunHandle) -> RunStatus:
        raise NotImplementedError

    @abstractmethod
    def result(self, handle: RunHandle) -> RunResult:
        raise NotImplementedError

    def cancel(self, handle: RunHandle) -> RunStatus:
        return RunStatus.CANCELLED

    def new_run_id(self) -> str:
        return str(uuid4())
