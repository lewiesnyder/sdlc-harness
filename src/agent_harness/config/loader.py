from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from jsonschema import Draft202012Validator

from agent_harness.config.models import HarnessConfig

DEFAULT_CONFIG_PATH = Path(".agent-harness/config.yaml")
SCHEMAS_DIR = Path(".agent-harness/schemas")


class ConfigError(Exception):
    """Raised when harness configuration cannot be loaded or validated."""


def _schema_path(name: str) -> Path:
    return SCHEMAS_DIR / name


def _load_schema(name: str) -> dict[str, Any]:
    path = _schema_path(name)
    if not path.is_file():
        raise ConfigError(f"schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(
    repo_root: Path | None = None,
    config_path: Path | None = None,
) -> HarnessConfig:
    """Load and validate harness configuration. Fails closed on any error."""
    root = repo_root or Path.cwd()
    path = config_path or (root / DEFAULT_CONFIG_PATH)

    if not path.is_file():
        raise ConfigError(f"configuration not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"configuration must be a mapping, got {type(raw).__name__}")

    schema = _load_schema("config.schema.json")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.path))
    if errors:
        messages = "; ".join(f"{'.'.join(map(str, e.path)) or 'root'}: {e.message}" for e in errors)
        raise ConfigError(f"configuration schema validation failed: {messages}")

    try:
        return HarnessConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"configuration semantic validation failed: {exc}") from exc


def validate_config_diagnostics(
    repo_root: Path | None = None,
    config_path: Path | None = None,
) -> list[str]:
    """Return actionable diagnostics for configuration issues."""
    root = repo_root or Path.cwd()
    diagnostics: list[str] = []

    try:
        config = load_config(repo_root=root, config_path=config_path)
    except ConfigError as exc:
        diagnostics.append(str(exc))
        return diagnostics

    if config.version != 1:
        diagnostics.append(
            f"unsupported config version {config.version}; only version 1 is supported"
        )

    for provider_name, provider in config.providers.items():
        if provider.credential and provider.credential.startswith(("sk-", "ghp_", "gho_")):
            diagnostics.append(
                f"providers.{provider_name}.credential appears to contain a secret value"
            )

    required_stages = {"plan", "replan", "implement", "review"}
    missing = required_stages - set(config.stages)
    if missing:
        diagnostics.append(f"missing required stages: {', '.join(sorted(missing))}")

    for stage_name, stage in config.stages.items():
        provider = config.providers[stage.provider]
        if stage.read_only and provider.adapter not in {"fake", "claude-code", "cursor-cloud"}:
            diagnostics.append(
                f"stage '{stage_name}' is read_only but provider adapter "
                f"'{provider.adapter}' may not support read-only execution"
            )

    return diagnostics


def validate_against_schema(instance: dict[str, Any], schema_name: str) -> None:
    """Validate a dict against a named harness schema."""
    schema = _load_schema(schema_name)
    jsonschema.validate(instance=instance, schema=schema)
