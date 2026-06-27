"""Feature catalog parser and updater (AH-002)."""

from agent_harness.catalog.models import CatalogError, Feature, FeatureCatalog
from agent_harness.catalog.parser import parse_catalog, update_feature_status
from agent_harness.catalog.updater import assert_status_only_diff, validate_dependencies

__all__ = [
    "CatalogError",
    "Feature",
    "FeatureCatalog",
    "assert_status_only_diff",
    "parse_catalog",
    "update_feature_status",
    "validate_dependencies",
]
