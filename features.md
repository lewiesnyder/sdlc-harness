# Agent Harness Feature Catalog

This file is the durable planning catalog for the Agentic SDLC Harness itself.

## AH-001 — Repository configuration and schema validation

**Status:** Done
**Priority:** P0
**Dependencies:** None

**Acceptance criteria:**

- The harness loads `.agent-harness/config.yaml`.
- Invalid configuration fails closed with actionable errors.
- JSON schemas are versioned.

**Tasks:**

- [x] Define configuration schema.
- [x] Implement parser and semantic validation.
- [x] Add sample configuration.
- [x] Add configuration diagnostics command.

---

## AH-002 — Feature catalog parser and updater

**Status:** Done
**Priority:** P0
**Dependencies:** AH-001

**Acceptance criteria:**

- The parser finds exactly one feature by ID.
- Status-only updates preserve unrelated content.
- Optimistic concurrency detects changes to `main`.

**Tasks:**

- [x] Define supported feature block contract.
- [x] Implement parse and validation.
- [x] Implement surgical status/task updates.
- [x] Implement diff guard.

---

## AH-004 — Lifecycle state machine, authorization, and idempotency

**Status:** Done
**Priority:** P0
**Dependencies:** AH-001

**Acceptance criteria:**

- Every command maps to allowed source and target states.
- Actor permission is checked at execution time.
- Duplicate events return the existing logical run.

**Tasks:**

- [x] Define transition table.
- [x] Implement compare-and-set state store.
- [x] Implement permission lookup.
- [x] Implement idempotency keys.

---

## AH-006 — Provider adapter SDK and router

**Status:** Done
**Priority:** P0
**Dependencies:** AH-001

**Acceptance criteria:**

- Providers implement normalized submit/status/result operations.
- The router validates stage capability requirements.
- Contract tests can run against a fake provider.

**Tasks:**

- [x] Define request, result, and capability schemas.
- [x] Build adapter SDK.
- [x] Build fake provider.
- [x] Implement router.

---

## AH-003 — Feature claim, branch, and draft PR bootstrap

**Status:** Ready
**Priority:** P0
**Dependencies:** AH-001, AH-002, AH-004

**Acceptance criteria:**

- The feature is **Work in Progress** on `main` before branch creation.
- The branch is exactly `feature/<feature-id>`.
- A draft PR is created and linked to feature/source issue.

**Tasks:**

- [ ] Implement protected claim PR mode.
- [ ] Implement trusted coordinator mode.
- [ ] Create branch and draft PR.
- [ ] Dispatch planning directly.

---

## AH-009 — Plan generation and plan linting

**Status:** Ready
**Priority:** P0
**Dependencies:** AH-003, AH-005, AH-006

**Acceptance criteria:**

- `agent-plan` produces `.agent/plans/<feature-id>.md`.
- Required metadata and sections are present.
- Only permitted planning files change.

**Tasks:**

- [ ] Define plan schema/template.
- [ ] Build planning prompt.
- [ ] Implement plan linter.
