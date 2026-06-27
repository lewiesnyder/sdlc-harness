# AGENTS.md

## Cursor Cloud specific instructions

### What this repository is

This repo contains the **Agentic SDLC Harness** design specification (`SDLC.md`)
and a growing **Python control-plane implementation** under `src/agent_harness/`.

The harness orchestrates human-governed agent loops on GitHub. Phase 0 delivers
configuration validation, feature catalog parsing, lifecycle state machine
contracts, and a provider SDK with a fake provider.

### Dependency management

Use **uv** for Python dependencies:

```bash
uv sync --all-packages --all-groups --all-extras
```

### Build / test / run

```bash
# Validate harness configuration
uv run agent-harness config-check

# Lint the feature catalog
uv run agent-harness catalog-lint

# Run tests
uv run pytest

# Dry-run a fake provider stage
uv run agent-harness fake-run --stage plan --feature-id AH-001
```

### Working on the docs (lint / preview)

The design spec remains in long-form Markdown. Lint on demand:

```bash
npx --yes markdownlint-cli2 "SDLC.md"
```

Note: default rules report many `MD013/line-length` items for `SDLC.md`; those
are stylistic, not defects.

`SDLC.md` contains 2 Mermaid blocks that should render without errors when
previewed with a client-side renderer (`marked` + `mermaid` from a CDN).

### Repository layout

```text
.agent-harness/     Config, schemas, prompts, policies
src/agent_harness/  Python implementation
features.md         Feature catalog
SDLC.md             Full design specification
tests/              pytest suite
```
