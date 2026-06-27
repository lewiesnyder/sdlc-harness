# AGENTS.md

## Cursor Cloud specific instructions

### What this repository is

This repo is **documentation-only**. It currently contains a single design
specification, `SDLC.md` ("Agentic SDLC Harness"). There is **no application
code, package manager, build system, automated test suite, or service** to run.
Do not expect `package.json`, `pyproject.toml`, a lockfile, `.cursor/environment.json`,
or a Dockerfile — none exist.

Because there are no dependencies, the startup update script is intentionally a
no-op. Nothing needs to be installed for normal work on this repo.

### Working on the docs (lint / preview)

The "development" workflow here is editing and validating Markdown. The toolchain
is not committed; run it on demand via `npx` (Node 22 + npm are available):

- Lint: `npx --yes markdownlint-cli2 "SDLC.md"`
  - Note: with default rules this reports many `MD013/line-length` items because
    the spec is written as long-form prose. Those are stylistic, not defects.
- Preview / render (incl. Mermaid diagrams): there is no committed previewer.
  A simple approach is to render the Markdown in a browser with a client-side
  renderer (e.g. `marked` + `mermaid` from a CDN). `SDLC.md` contains 2 Mermaid
  blocks (a `stateDiagram-v2` and a `flowchart`) that should render without errors.

### Build / test / run

There is nothing to build, test, or run. If application code is added later,
update this section and add a real update script + run/test commands.
