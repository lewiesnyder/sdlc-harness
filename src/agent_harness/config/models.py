from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ClaimMode(str, Enum):
    PROTECTED_CLAIM_PR = "protected-claim-pr"
    TRUSTED_COORDINATOR = "trusted-coordinator"


class FeatureCatalogConfig(BaseModel):
    path: str
    id_pattern: str
    eligible_statuses: list[str]
    in_progress_status: str
    done_status: str


class RepositoryConfig(BaseModel):
    default_branch: str = "main"
    branch_template: str
    plan_template: str
    claim_mode: ClaimMode
    draft_pull_request: bool = True

    @field_validator("branch_template")
    @classmethod
    def branch_must_include_feature_id(cls, value: str) -> str:
        if "{feature_id}" not in value:
            raise ValueError("branch_template must contain {feature_id}")
        return value

    @field_validator("plan_template")
    @classmethod
    def plan_must_include_feature_id(cls, value: str) -> str:
        if "{feature_id}" not in value:
            raise ValueError("plan_template must contain {feature_id}")
        return value

    def feature_branch(self, feature_id: str) -> str:
        return self.branch_template.format(feature_id=feature_id)

    def plan_path(self, feature_id: str) -> str:
        return self.plan_template.format(feature_id=feature_id)


class ProviderConfig(BaseModel):
    adapter: str
    credential: str | None = None


class StageConfig(BaseModel):
    provider: str
    timeout_minutes: int | None = None
    max_cost_usd: float | None = None
    read_only: bool = False
    artifact_sink: str | None = None


class SecurityConfig(BaseModel):
    require_same_repository_branch: bool = True
    allowed_author_permissions: list[Literal["write", "maintain", "admin"]] = Field(
        default_factory=lambda: ["write", "maintain", "admin"]
    )
    protected_paths: list[str] = Field(default_factory=list)
    network_profile: str = "package-registries-only"
    prohibit_production_credentials: bool = True
    pin_actions_by_sha: bool = True


class ReviewConfig(BaseModel):
    blocking_severities: list[str] = Field(default_factory=lambda: ["critical", "high"])
    require_acceptance_traceability: bool = True
    invalidate_on_new_commit: bool = True


class TelemetryConfig(BaseModel):
    otlp_endpoint_secret: str | None = None
    service_name: str = "agentic-sdlc-harness"
    capture_prompt_content: bool = False


class HarnessConfig(BaseModel):
    version: int
    feature_catalog: FeatureCatalogConfig
    repository: RepositoryConfig
    providers: dict[str, ProviderConfig]
    stages: dict[str, StageConfig]
    commands: dict[str, str] = Field(default_factory=dict)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)

    @model_validator(mode="after")
    def validate_provider_references(self) -> HarnessConfig:
        for stage_name, stage in self.stages.items():
            if stage.provider not in self.providers:
                raise ValueError(
                    f"stage '{stage_name}' references unknown provider '{stage.provider}'"
                )
        return self

    @model_validator(mode="after")
    def reject_embedded_secrets(self) -> HarnessConfig:
        """Fail closed if configuration appears to embed secret values."""
        suspicious_keys = {"password", "secret", "api_key", "token", "private_key"}
        raw = self.model_dump()
        self._scan_for_embedded_secrets(raw, suspicious_keys, path="config")
        return self

    @staticmethod
    def _scan_for_embedded_secrets(
        obj: object, suspicious_keys: set[str], path: str
    ) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()
                if key_lower in suspicious_keys and isinstance(value, str) and value:
                    raise ValueError(
                        f"configuration at '{path}.{key}' appears to embed a secret value; "
                        "reference secret names only"
                    )
                HarnessConfig._scan_for_embedded_secrets(
                    value, suspicious_keys, f"{path}.{key}"
                )
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                HarnessConfig._scan_for_embedded_secrets(
                    item, suspicious_keys, f"{path}[{index}]"
                )

    def stage_timeout_seconds(self, stage_name: str) -> int:
        stage = self.stages[stage_name]
        minutes = stage.timeout_minutes or 60
        return minutes * 60
