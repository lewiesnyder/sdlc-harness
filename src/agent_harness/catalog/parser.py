from __future__ import annotations

import re
from pathlib import Path

from agent_harness.catalog.models import CatalogError, Feature, FeatureCatalog
from agent_harness.config.models import FeatureCatalogConfig

FEATURE_HEADER_RE = re.compile(
    r"^##\s+([A-Z][A-Z0-9]+-\d{3,})\s+[—\-]\s+(.+?)\s*$"
)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s+(.+?)\s*$", re.MULTILINE)
PRIORITY_RE = re.compile(r"^\*\*Priority:\*\*\s+(.+?)\s*$", re.MULTILINE)
DEPENDENCIES_RE = re.compile(r"^\*\*Dependencies:\*\*\s+(.+?)\s*$", re.MULTILINE)
TASK_RE = re.compile(r"^-\s+\[[ xX]\]\s+(.+?)\s*$", re.MULTILINE)
ACCEPTANCE_HEADER = "**Acceptance criteria:**"
TASKS_HEADER = "**Tasks:**"


def parse_catalog(
    catalog_path: Path,
    config: FeatureCatalogConfig | None = None,
) -> FeatureCatalog:
    """Parse features.md into structured feature records."""
    if not catalog_path.is_file():
        raise CatalogError(f"feature catalog not found: {catalog_path}")

    content = catalog_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    id_pattern = re.compile(config.id_pattern) if config else re.compile(r"^[A-Z][A-Z0-9]+-\d{3,}$")

    features: dict[str, Feature] = {}
    current_id: str | None = None
    current_title: str | None = None
    line_start = 0

    for index, line in enumerate(lines, start=1):
        match = FEATURE_HEADER_RE.match(line.rstrip("\n"))
        if not match:
            continue

        if current_id is not None:
            block = "".join(lines[line_start - 1 : index - 1])
            feature = _parse_feature_block(
                current_id, current_title or "", block, line_start, index - 1
            )
            if feature.id in features:
                raise CatalogError(f"duplicate feature ID: {feature.id}")
            if not id_pattern.match(feature.id):
                raise CatalogError(f"feature ID does not match pattern: {feature.id}")
            features[feature.id] = feature

        current_id = match.group(1)
        current_title = match.group(2).strip()
        line_start = index

    if current_id is not None:
        block = "".join(lines[line_start - 1 :])
        feature = _parse_feature_block(
            current_id, current_title or "", block, line_start, len(lines)
        )
        if feature.id in features:
            raise CatalogError(f"duplicate feature ID: {feature.id}")
        if not id_pattern.match(feature.id):
            raise CatalogError(f"feature ID does not match pattern: {feature.id}")
        features[feature.id] = feature

    return FeatureCatalog(path=str(catalog_path), content=content, features=features)


def _parse_feature_block(
    feature_id: str,
    title: str,
    block: str,
    line_start: int,
    line_end: int,
) -> Feature:
    status_match = STATUS_RE.search(block)
    if not status_match:
        raise CatalogError(f"feature {feature_id} missing **Status:** field")

    priority_match = PRIORITY_RE.search(block)
    dependencies: list[str] = []
    dep_match = DEPENDENCIES_RE.search(block)
    if dep_match:
        raw = dep_match.group(1).strip()
        if raw.lower() not in {"none", "n/a"}:
            dependencies = [part.strip() for part in re.split(r",|;", raw) if part.strip()]

    acceptance_criteria = _extract_bullet_section(block, ACCEPTANCE_HEADER)
    tasks = [m.group(1).strip() for m in TASK_RE.finditer(block)]

    return Feature(
        id=feature_id,
        title=title,
        status=status_match.group(1).strip(),
        line_start=line_start,
        line_end=line_end,
        priority=priority_match.group(1).strip() if priority_match else None,
        dependencies=dependencies,
        acceptance_criteria=acceptance_criteria,
        tasks=tasks,
    )


def _extract_bullet_section(block: str, header: str) -> list[str]:
    if header not in block:
        return []
    section = block.split(header, 1)[1]
    items: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("**") and not stripped.startswith("- "):
            break
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def update_feature_status(
    catalog: FeatureCatalog,
    feature_id: str,
    new_status: str,
    expected_content_sha: str | None = None,
) -> str:
    """Surgically update one feature's status, preserving unrelated content."""
    import hashlib

    if expected_content_sha:
        current_sha = hashlib.sha256(catalog.content.encode("utf-8")).hexdigest()
        if current_sha != expected_content_sha:
            raise CatalogError(
                "catalog changed since read; optimistic concurrency conflict detected"
            )

    feature = catalog.get(feature_id)
    lines = catalog.content.splitlines(keepends=True)
    block_lines = lines[feature.line_start - 1 : feature.line_end]

    new_block_lines: list[str] = []
    replaced = False
    for line in block_lines:
        if STATUS_RE.match(line.rstrip("\n")):
            new_block_lines.append(f"**Status:** {new_status}\n")
            replaced = True
        else:
            new_block_lines.append(line)

    if not replaced:
        raise CatalogError(f"could not locate status line for feature {feature_id}")

    updated_lines = (
        lines[: feature.line_start - 1] + new_block_lines + lines[feature.line_end :]
    )
    return "".join(updated_lines)
