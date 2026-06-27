from __future__ import annotations

import difflib
import re

from agent_harness.catalog.models import CatalogError, FeatureCatalog

STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*\s+.+$", re.MULTILINE)


def assert_status_only_diff(
    original: str,
    updated: str,
    feature_id: str,
    catalog: FeatureCatalog,
) -> None:
    """Ensure a catalog update changed only the target feature's status line."""
    if original == updated:
        return

    original_lines = original.splitlines()
    updated_lines = updated.splitlines()

    if len(original_lines) != len(updated_lines):
        raise CatalogError(
            f"status update for {feature_id} changed line count; only status may change"
        )

    feature = catalog.get(feature_id)
    for index, (before, after) in enumerate(zip(original_lines, updated_lines, strict=True)):
        line_number = index + 1
        if before == after:
            continue
        if not (feature.line_start <= line_number <= feature.line_end):
            raise CatalogError(
                f"status update for {feature_id} modified line {line_number} "
                "outside the feature block"
            )
        if not STATUS_LINE_RE.match(before) or not STATUS_LINE_RE.match(after):
            raise CatalogError(
                f"status update for {feature_id} modified non-status line {line_number}"
            )


def validate_dependencies(
    catalog: FeatureCatalog,
    feature_id: str,
    done_status: str = "Done",
) -> list[str]:
    """Return dependency IDs that are not complete."""
    feature = catalog.get(feature_id)
    incomplete: list[str] = []
    for dep_id in feature.dependencies:
        if dep_id not in catalog.features:
            incomplete.append(dep_id)
            continue
        dep = catalog.features[dep_id]
        if dep.status != done_status:
            incomplete.append(dep_id)
    return incomplete


def diff_summary(original: str, updated: str) -> str:
    """Human-readable unified diff for diagnostics."""
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile="before",
            tofile="after",
        )
    )
