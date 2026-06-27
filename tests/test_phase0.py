import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_harness.catalog.parser import parse_catalog, update_feature_status
from agent_harness.catalog.updater import assert_status_only_diff, validate_dependencies
from agent_harness.config.loader import ConfigError, load_config, validate_against_schema
from agent_harness.provider.contract import (
    AuthorizationRef,
    ContextRef,
    Operation,
    OutputSpec,
    PolicyRef,
    RepositoryRef,
    RunRequest,
    WorkItemRef,
)
from agent_harness.provider.fake import FakeProvider
from agent_harness.provider.router import ProviderRouter, RouterError
from agent_harness.state.commands import CommandLabel
from agent_harness.state.idempotency import build_idempotency_key
from agent_harness.state.machine import StateMachine, TransitionRequest, TransitionError
from agent_harness.state.models import LifecycleState, Permission


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_valid_config() -> None:
    config = load_config(repo_root=REPO_ROOT)
    assert config.version == 1
    assert config.feature_catalog.path == "features.md"
    assert "fake" in config.providers
    assert config.repository.feature_branch("AH-003") == "feature/AH-003"


def test_config_rejects_unknown_provider_reference(tmp_path: Path) -> None:
    bad_config = tmp_path / "config.yaml"
    bad_config.write_text(
        """
version: 1
feature_catalog:
  path: features.md
  id_pattern: "^AH-[0-9]{3}$"
  eligible_statuses: [Ready]
  in_progress_status: Work in Progress
  done_status: Done
repository:
  default_branch: main
  branch_template: "feature/{feature_id}"
  plan_template: ".agent/plans/{feature_id}.md"
  claim_mode: protected-claim-pr
providers:
  fake:
    adapter: fake
stages:
  plan:
    provider: missing-provider
""",
        encoding="utf-8",
    )
    harness_dir = tmp_path / ".agent-harness"
    harness_dir.mkdir()
    schemas_src = REPO_ROOT / ".agent-harness" / "schemas"
    (harness_dir / "schemas").mkdir()
    for schema_file in schemas_src.glob("*.json"):
        (harness_dir / "schemas" / schema_file.name).write_text(
            schema_file.read_text(encoding="utf-8"), encoding="utf-8"
        )

    with pytest.raises(ConfigError, match="unknown provider"):
        load_config(repo_root=tmp_path, config_path=bad_config)


def test_parse_feature_catalog() -> None:
    config = load_config(repo_root=REPO_ROOT)
    catalog = parse_catalog(REPO_ROOT / "features.md", config.feature_catalog)
    feature = catalog.get("AH-001")
    assert feature.status == "Done"
    assert feature.priority == "P0"
    assert len(feature.tasks) >= 1
    assert len(feature.acceptance_criteria) >= 1


def test_status_only_update() -> None:
    config = load_config(repo_root=REPO_ROOT)
    catalog = parse_catalog(REPO_ROOT / "features.md", config.feature_catalog)
    updated = update_feature_status(catalog, "AH-003", "Work in Progress")
    assert_status_only_diff(catalog.content, updated, "AH-003", catalog)
    assert "**Status:** Work in Progress" in updated


def test_dependency_validation() -> None:
    config = load_config(repo_root=REPO_ROOT)
    catalog = parse_catalog(REPO_ROOT / "features.md", config.feature_catalog)
    assert validate_dependencies(catalog, "AH-003") == []
    incomplete = validate_dependencies(catalog, "AH-009")
    assert "AH-003" in incomplete


def test_state_machine_happy_path() -> None:
    machine = StateMachine()
    request = TransitionRequest(
        command=CommandLabel.AGENT_START,
        current_state=LifecycleState.READY,
        actor="reviewer",
        actor_permission=Permission.WRITE,
        repo_id="repo-1",
        pr_number=10,
        head_sha="sha-1",
    )
    result = machine.transition(request, feature_id="AH-003")
    assert result.to_state == LifecycleState.CLAIMING

    duplicate = machine.transition(request, feature_id="AH-003")
    assert duplicate.duplicate is True


def test_state_machine_rejects_unauthorized() -> None:
    machine = StateMachine()
    request = TransitionRequest(
        command=CommandLabel.AGENT_IMPLEMENT,
        current_state=LifecycleState.PLAN_REVIEW,
        actor="guest",
        actor_permission=Permission.READ,
        repo_id="repo-1",
        pr_number=10,
        head_sha="sha-1",
    )
    with pytest.raises(TransitionError, match="not in the allowed set"):
        machine.transition(request, feature_id="AH-003")


def test_state_machine_rejects_invalid_transition() -> None:
    machine = StateMachine()
    request = TransitionRequest(
        command=CommandLabel.AGENT_IMPLEMENT,
        current_state=LifecycleState.READY,
        actor="reviewer",
        actor_permission=Permission.WRITE,
        repo_id="repo-1",
        pr_number=10,
        head_sha="sha-1",
    )
    with pytest.raises(TransitionError, match="invalid transition"):
        machine.transition(request, feature_id="AH-003")


def test_idempotency_key_format() -> None:
    key = build_idempotency_key("repo-1", 42, "PLAN", "abc", "plan-sha", "2026-01-01T00:00:00Z")
    assert key == "repo-1:42:PLAN:abc:plan-sha:2026-01-01T00:00:00Z"


def test_fake_provider_plan_run() -> None:
    provider = FakeProvider()
    request = _sample_request(Operation.PLAN)
    handle = provider.submit(request)
    result = provider.result(handle)
    assert result.status.value == "SUCCEEDED"
    assert ".agent/plans/AH-001.md" in result.output.changed_paths


def test_router_stage_execution() -> None:
    config = load_config(repo_root=REPO_ROOT)
    router = ProviderRouter(config)
    request = _sample_request(Operation.PLAN)
    result = router.route_stage("plan", request)
    assert result.provider == "fake"
    assert result.output.summary


def test_router_rejects_wrong_operation() -> None:
    config = load_config(repo_root=REPO_ROOT)
    router = ProviderRouter(config)
    request = _sample_request(Operation.IMPLEMENT)
    with pytest.raises(RouterError, match="expects operation"):
        router.route_stage("plan", request)


def test_run_request_matches_schema() -> None:
    request = _sample_request(Operation.REVIEW)
    payload = request.model_dump_normalized()
    schema_path = REPO_ROOT / ".agent-harness/schemas/run-request.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_against_schema(payload, "run-request.schema.json")


def _sample_request(operation: Operation) -> RunRequest:
    return RunRequest(
        operation=operation,
        idempotency_key="repo:1:PLAN:abc:none:none",
        repository=RepositoryRef(
            owner="org",
            name="repo",
            default_branch="main",
            base_sha="abc",
            head_sha="abc",
            feature_branch="feature/AH-001",
        ),
        work_item=WorkItemRef(feature_id="AH-001", pull_request_number=1),
        authorization=AuthorizationRef(
            actor="human",
            actor_permission="write",
            authorized_at=datetime.now(timezone.utc),
        ),
        context=ContextRef(
            manifest_uri="file:///tmp/manifest.json",
            plan_path=".agent/plans/AH-001.md",
        ),
        policy=PolicyRef(profile="default", timeout_seconds=60),
        output=OutputSpec(required_schema="run-result.schema.json", commit_allowed=True),
    )
