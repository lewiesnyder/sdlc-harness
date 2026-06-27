from __future__ import annotations

from dataclasses import dataclass, field


class CatalogError(Exception):
    """Raised when the feature catalog cannot be parsed or updated safely."""


@dataclass(frozen=True)
class Feature:
    id: str
    title: str
    status: str
    line_start: int
    line_end: int
    priority: str | None = None
    dependencies: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)

    def is_eligible(self, eligible_statuses: list[str]) -> bool:
        return self.status in eligible_statuses


@dataclass(frozen=True)
class FeatureCatalog:
    path: str
    content: str
    features: dict[str, Feature]

    def get(self, feature_id: str) -> Feature:
        if feature_id not in self.features:
            raise CatalogError(f"feature not found: {feature_id}")
        return self.features[feature_id]

    def duplicate_ids(self) -> list[str]:
        seen: dict[str, int] = {}
        for feature in self.features.values():
            seen[feature.id] = seen.get(feature.id, 0) + 1
        return [fid for fid, count in seen.items() if count > 1]
