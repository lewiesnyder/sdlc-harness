from __future__ import annotations


def build_idempotency_key(
    repo_id: str,
    pr_number: int,
    operation: str,
    head_sha: str,
    plan_sha: str | None = None,
    feedback_cutoff: str | None = None,
) -> str:
    """Build the recommended idempotency key from SDLC.md section 15.5."""
    plan_part = plan_sha or "none"
    feedback_part = feedback_cutoff or "none"
    return f"{repo_id}:{pr_number}:{operation}:{head_sha}:{plan_part}:{feedback_part}"
