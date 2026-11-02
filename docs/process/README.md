# process

## Purpose

Workspace directory `repos/communifarm/docs/process`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `docs`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `test-cases/` | `docs` | Enter for docs work — read `test-cases/README.md` (Feature index → Map). |
| `mixing-batch.md` | `docs` | Mixing batch (hardwood substrate) — Operator/architecture docs — same change as code when user-visible. |
| `nfc-harvest-checkin.md` | `docs` | NFC resolve / check-in harvest — Operator/architecture docs — same change as code when user-visible. |
| `placement-locations.md` | `docs` | Placement locations (areas + zones) — Operator/architecture docs — same change as code when user-visible. |
| `point-of-sale.md` | `docs` | Point of sale / sales tracking — Operator/architecture docs — same change as code when user-visible. |
| `production-inoculate.md` | `docs` | Production inoculate (culture → substrate) — Operator/architecture docs — same change as code when user-visible. |
| `README.md` | `docs` | This directory map (dim1 Map + dim2 Feature index). |
| `starter-batch.md` | `docs` | Starter batch lifecycle — Operator/architecture docs — same change as code when user-visible. |
| `varieties-culture-vessels.md` | `docs` | Varieties + culture vessels (inoculum catalog) — Operator/architecture docs — same change as code when user-visible. |

## Feature index

| keywords / features | path |
|---------------------|------|
| test-cases, docs | `test-cases/` |
| mixing-batch, docs, Mixing batch (hardwood substrate), Flow, Manual weigh (scale fallback), Water, NFC inventory, Dashboards, Test cases, Sources, batch | `mixing-batch.md` |
| nfc-harvest-checkin, docs, NFC resolve / check-in harvest, Flow, Fridge / bagging (small residential fridge), Bind physical tags, Placement trends, Testing, NFC | `nfc-harvest-checkin.md` |
| placement-locations, docs, Placement locations (areas + zones), Hierarchy, Default seed layout, Soft area hints, Services, Culture / media (schema v8), Dashboard, Testing | `placement-locations.md` |
| point-of-sale, docs, Point of sale / sales tracking, Flow, Identity, Out of scope (this release) | `point-of-sale.md` |
| production-inoculate, docs, Production inoculate (culture → substrate), Locked defaults, Flow, Services, Dashboard Production tab, Testing | `production-inoculate.md` |
| starter-batch, docs, Starter batch lifecycle, batch | `starter-batch.md` |
| varieties-culture-vessels, docs, Varieties + culture vessels (inoculum catalog), Seed varieties, Flow, UI | `varieties-culture-vessels.md` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
