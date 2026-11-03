# adr

## Purpose

Workspace directory `repos/communifarm/docs/adr`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `docs`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `0001-store-persistence.md` | `docs` | ADR 0001: Store-backed persistence for MVP — Operator/architecture docs — same change as code when user-visible. |
| `0002-dashboard-generation.md` | `docs` | ADR 0002: Generated Lovelace dashboard model — Operator/architecture docs — same change as code when user-visible. |
| `0003-communifarm-sqlite.md` | `docs` | ADR 0003: Communifarm SQLite for process / analysis events — Operator/architecture docs — same change as code when user-visible. |
| `0004-climate-control.md` | `docs` | ADR 0004: Climate tree and control ownership — Operator/architecture docs — same change as code when user-visible. |
| `0005-local-e2e-ci-evidence.md` | `docs` | ADR 0005: Local E2E evidence for merge CI — Operator/architecture docs — same change as code when user-visible. |
| `0006-nfc-dual-write-registry.md` | `docs` | ADR 0006: NFC dual-write registry (not central-only UID table) — Operator/architecture docs — same change as code when user-visible. |
| `0008-entity-bases-and-runtime-load.md` | `docs` | ADR 0008: Entity bases, runtime load, and maintainability — Operator/architecture docs — same change as code when user-visible. |
| `0007-ops-scheduling-alerts.md` | `docs` | ADR 0007: Ops scheduling and priority alerts — Operator/architecture docs — same change as code when user-visible. |
| `README.md` | `docs` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| 0001-store-persistence, docs, ADR 0001: Store-backed persistence for MVP, Status, Context, Decision, Consequences | `0001-store-persistence.md` |
| 0002-dashboard-generation, docs, ADR 0002: Generated Lovelace dashboard model, Status, Context, Decision, Consequences | `0002-dashboard-generation.md` |
| 0003-communifarm-sqlite, docs, ADR 0003: Communifarm SQLite for process / analysis events, Status, Context, Decision, Consequences, SQLite | `0003-communifarm-sqlite.md` |
| 0004-climate-control, docs, ADR 0004: Climate tree and control ownership, Status, Context, Decision, Consequences | `0004-climate-control.md` |
| 0005-local-e2e-ci-evidence, docs, ADR 0005: Local E2E evidence for merge CI, Status, Context, Decision, Consequences | `0005-local-e2e-ci-evidence.md` |
| 0006-nfc-dual-write-registry, docs, ADR 0006: NFC dual-write registry (not central-only UID table), Status, Context, Decision, Consequences, NFC | `0006-nfc-dual-write-registry.md` |
| 0008-entity-bases-and-runtime-load, docs, ADR 0008: Entity bases, runtime load, and maintainability, Status, Context, Findings, Inheritance (KEEP), Runtime load (acceptable for home scale), Security / dangerous patterns, Decision, Spike on this branch, Rejected alternatives | `0008-entity-bases-and-runtime-load.md` |
| 0007-ops-scheduling-alerts, docs, ADR 0007: Ops scheduling and priority alerts, AlarmEvent, ops queue | `0007-ops-scheduling-alerts.md` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
