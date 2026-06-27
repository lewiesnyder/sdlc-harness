# Agentic SDLC Harness

Python implementation of the [Agentic SDLC Harness](SDLC.md) — a GitHub-centered orchestration system for human-governed agent loops.

## Phase 0 status

This repository currently implements the **Phase 0 foundation** from SDLC.md section 23:

- **AH-001** — configuration loading and schema validation
- **AH-002** — feature catalog parser and surgical status updates
- **AH-004** — lifecycle state machine with authorization and idempotency
- **AH-006** — provider adapter SDK, router, and fake provider

## Quick start

```bash
uv sync --all-packages --all-groups --all-extras
uv run agent-harness config-check
uv run agent-harness catalog-lint
uv run pytest
```

## CLI

| Command | Purpose |
|---|---|
| `agent-harness config-check` | Validate `.agent-harness/config.yaml` |
| `agent-harness catalog-lint` | Parse and lint `features.md` |
| `agent-harness catalog-show <id>` | Show one feature record |
| `agent-harness transition-check` | Dry-run a lifecycle transition |
| `agent-harness fake-run --stage plan` | Execute a fake provider stage run |

## Layout

```text
.agent-harness/     Harness configuration, schemas, prompts, policies
src/agent_harness/  Python control-plane foundation
features.md         Feature catalog
SDLC.md             Full design specification
```

## Next steps

Phase 1 will add bootstrap, context building, planning/replanning workflows, and the first real provider adapter.
