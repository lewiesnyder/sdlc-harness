from __future__ import annotations

from enum import Enum


class LifecycleState(str, Enum):
    READY = "READY"
    CLAIMING = "CLAIMING"
    PLANNING = "PLANNING"
    PLAN_REVIEW = "PLAN_REVIEW"
    REPLANNING = "REPLANNING"
    IMPLEMENTING = "IMPLEMENTING"
    VERIFYING = "VERIFYING"
    IMPLEMENTATION_REVIEW = "IMPLEMENTATION_REVIEW"
    DEMOING = "DEMOING"
    DEMO_READY = "DEMO_READY"
    REVIEWING = "REVIEWING"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    READY_TO_MERGE = "READY_TO_MERGE"
    MERGED = "MERGED"
    FINALIZING = "FINALIZING"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    MAINTAIN = "maintain"
    ADMIN = "admin"

    def satisfies(self, required: Permission) -> bool:
        order = [Permission.READ, Permission.WRITE, Permission.MAINTAIN, Permission.ADMIN]
        return order.index(self) >= order.index(required)
