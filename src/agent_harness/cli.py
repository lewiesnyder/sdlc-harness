from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from agent_harness.catalog.parser import parse_catalog, update_feature_status
from agent_harness.catalog.updater import assert_status_only_diff, validate_dependencies
from agent_harness.config.loader import ConfigError, load_config, validate_config_diagnostics
from agent_harness.state.commands import CommandLabel
from agent_harness.state.machine import StateMachine, TransitionRequest
from agent_harness.state.models import LifecycleState, Permission

console = Console()


@click.group()
@click.option(
    "--repo-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Repository root path.",
)
@click.pass_context
def main(ctx: click.Context, repo_root: Path) -> None:
    """Agentic SDLC Harness CLI."""
    ctx.ensure_object(dict)
    ctx.obj["repo_root"] = repo_root.resolve()


@main.command("config-check")
@click.pass_context
def config_check(ctx: click.Context) -> None:
    """Validate harness configuration and print diagnostics."""
    root: Path = ctx.obj["repo_root"]
    diagnostics = validate_config_diagnostics(repo_root=root)
    if diagnostics:
        for item in diagnostics:
            console.print(f"[red]error[/red] {item}")
        raise SystemExit(1)
    config = load_config(repo_root=root)
    console.print("[green]configuration valid[/green]")
    console.print(f"catalog: {config.feature_catalog.path}")
    console.print(f"providers: {', '.join(config.providers)}")


@main.command("catalog-lint")
@click.pass_context
def catalog_lint(ctx: click.Context) -> None:
    """Parse and lint the feature catalog."""
    root: Path = ctx.obj["repo_root"]
    try:
        config = load_config(repo_root=root)
    except ConfigError as exc:
        console.print(f"[red]config error[/red] {exc}")
        raise SystemExit(1) from exc

    catalog_path = root / config.feature_catalog.path
    catalog = parse_catalog(catalog_path, config.feature_catalog)
    console.print(f"[green]parsed {len(catalog.features)} features[/green] from {catalog_path}")

    for feature in catalog.features.values():
        incomplete = validate_dependencies(
            catalog, feature.id, done_status=config.feature_catalog.done_status
        )
        if incomplete:
            console.print(
                f"[yellow]warning[/yellow] {feature.id} has incomplete dependencies: "
                f"{', '.join(incomplete)}"
            )


@main.command("catalog-show")
@click.argument("feature_id")
@click.pass_context
def catalog_show(ctx: click.Context, feature_id: str) -> None:
    """Show one feature from the catalog."""
    root: Path = ctx.obj["repo_root"]
    config = load_config(repo_root=root)
    catalog = parse_catalog(root / config.feature_catalog.path, config.feature_catalog)
    feature = catalog.get(feature_id)

    table = Table(title=feature.id)
    table.add_column("field")
    table.add_column("value")
    table.add_row("title", feature.title)
    table.add_row("status", feature.status)
    table.add_row("priority", feature.priority or "")
    table.add_row("dependencies", ", ".join(feature.dependencies) or "none")
    table.add_row("tasks", str(len(feature.tasks)))
    table.add_row("acceptance criteria", str(len(feature.acceptance_criteria)))
    console.print(table)


@main.command("transition-check")
@click.option("--from-state", required=True)
@click.option("--command", required=True)
@click.option("--actor", default="human")
@click.option("--permission", default="write")
@click.pass_context
def transition_check(
    ctx: click.Context,
    from_state: str,
    command: str,
    actor: str,
    permission: str,
) -> None:
    """Dry-run a lifecycle transition."""
    machine = StateMachine()
    try:
        cmd = CommandLabel(command)
    except ValueError:
        cmd = command

    request = TransitionRequest(
        command=cmd,
        current_state=LifecycleState(from_state),
        actor=actor,
        actor_permission=Permission(permission),
        repo_id="local",
        pr_number=1,
        head_sha="abc123",
    )
    result = machine.transition(request, feature_id="FEAT-001")
    console.print(
        f"[green]accepted[/green] {result.from_state.value} -> {result.to_state.value}"
    )


@main.command("fake-run")
@click.option("--stage", default="plan")
@click.option("--feature-id", default="AH-001")
@click.pass_context
def fake_run(ctx: click.Context, stage: str, feature_id: str) -> None:
    """Execute a fake provider run for the configured stage."""
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
    from agent_harness.provider.router import ProviderRouter

    root: Path = ctx.obj["repo_root"]
    config = load_config(repo_root=root)
    router = ProviderRouter(config)

    operation = {
        "plan": Operation.PLAN,
        "replan": Operation.REPLAN,
        "implement": Operation.IMPLEMENT,
        "demo": Operation.DEMO,
        "review": Operation.REVIEW,
    }[stage]

    request = RunRequest(
        operation=operation,
        idempotency_key=f"local:1:{operation.value}:abc123:none:none",
        repository=RepositoryRef(
            owner="org",
            name="repo",
            default_branch="main",
            base_sha="abc123",
            head_sha="abc123",
            feature_branch=f"feature/{feature_id}",
        ),
        work_item=WorkItemRef(feature_id=feature_id, pull_request_number=1),
        authorization=AuthorizationRef(
            actor="human",
            actor_permission="write",
            authorized_at=datetime.now(timezone.utc),
        ),
        context=ContextRef(manifest_uri="file:///tmp/manifest.json"),
        policy=PolicyRef(profile="default", timeout_seconds=60),
        output=OutputSpec(required_schema="run-result.schema.json", commit_allowed=True),
    )
    result = router.route_stage(stage, request)
    console.print(f"[green]{result.status.value}[/green] {result.output.summary}")
