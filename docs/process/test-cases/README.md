# test-cases

## Purpose

Workspace directory `repos/communifarm/docs/process/test-cases`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `docs`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `air-exchange-tachometer.md` | `docs` | Air-exchange tachometer — test cases — Operator/architecture docs — same change as code when user-visible. |
| `climate-layout.md` | `docs` | Climate layout — test cases — Operator/architecture docs — same change as code when user-visible. |
| `mixing-batch.md` | `docs` | Mixing batch — test cases — Operator/architecture docs — same change as code when user-visible. |
| `nfc-scan-audit.md` | `docs` | NFC scan audit / dual-write — test cases — Operator/architecture docs — same change as code when user-visible. |
| `operator-personas.md` | `docs` | Operator personas — test cases — Operator/architecture docs — same change as code when user-visible. |
| `production-inoculate.md` | `docs` | Production inoculate — test cases — Operator/architecture docs — same change as code when user-visible. |
| `README.md` | `docs` | This directory map (dim1 Map + dim2 Feature index). |
| `TEMPLATE.md` | `docs` | <process name> — test cases — Operator/architecture docs — same change as code when user-visible. |

## Feature index

| keywords / features | path |
|---------------------|------|
| air-exchange-tachometer, docs, Air-exchange tachometer — test cases, label-vent — register a labeled vent before measuring, record-reading — timestamped value per vent, schema-v13 — upgrade keeps prior production rows | `air-exchange-tachometer.md` |
| climate-layout, docs, Climate layout — test cases, layout-image — the floor plan is visible, Expected record | `climate-layout.md` |
| mixing-batch, docs, Mixing batch — test cases, INV1 — new UUID for same ingredient name, Setup, Steps, Expected record, W1 — water sum and over-add reject, M1 — badge checkpoint after dry weigh, D1 — Mix vs Weigh dashboards, batch | `mixing-batch.md` |
| nfc-scan-audit, docs, NFC scan audit / dual-write — test cases, NFC | `nfc-scan-audit.md` |
| operator-personas, docs, Operator personas — test cases, OP1 — 95% scan then press (single bag), OP2 — 40% dropdown then scan then press, OP3 — No bag context → entire batch, OP4 — Non-container Tag source does not fake a bag move | `operator-personas.md` |
| production-inoculate, docs, Production inoculate — test cases, P1 — Storage inventory after Mix relocate, P2 — Move to incubation with optional bag NFC, Sources | `production-inoculate.md` |
| TEMPLATE, docs, <process name> — test cases, <step id> — <operator step in plain language>, Setup, Steps, Expected record, Sources | `TEMPLATE.md` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
