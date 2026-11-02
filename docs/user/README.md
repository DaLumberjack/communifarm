# user

## Purpose

Workspace directory `repos/communifarm/docs/user`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `docs`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `climate.md` | `docs` | Climate rooms and machines — Operator/architecture docs — same change as code when user-visible. |
| `dashboard.md` | `docs` | Dashboard — Operator/architecture docs — same change as code when user-visible. |
| `local-development.md` | `docs` | Local development — Operator/architecture docs — same change as code when user-visible. |
| `mock-scale.md` | `docs` | Mock esp32dev scale (local T1/T2) — Operator/architecture docs — same change as code when user-visible. |
| `onboarding.md` | `docs` | Onboarding — Operator/architecture docs — same change as code when user-visible. |
| `openbao.md` | `docs` | OpenBao (HA test secrets) — Operator/architecture docs — same change as code when user-visible. |
| `README.md` | `docs` | This directory map (dim1 Map + dim2 Feature index). |
| `storage.md` | `docs` | Communifarm SQLite (process / analysis data) — Operator/architecture docs — same change as code when user-visible. |
| `test-vm-deploy.md` | `docs` | Test VM deployment (T3 only) — Operator/architecture docs — same change as code when user-visible. |
| `versioning.md` | `docs` | Versioning and merge — Operator/architecture docs — same change as code when user-visible. |

## Feature index

| keywords / features | path |
|---------------------|------|
| climate, docs, Climate rooms and machines, Seed the layout, Preset climates, Bind a sensor or machine, What the tick does | `climate.md` |
| dashboard, docs, Weigh session, Mix protocol, Intake (NFC mark + purchase), Batches tab | `dashboard.md` |
| local-development, docs, Local development, Prerequisite: use `py` for Python, Prerequisite: Docker Desktop must be running, if Stopped: Start-Service com.docker.service  (or launch Docker Desktop), Dev container / compose, First boot vs preferred reuse, Steps, Testing stages, Playwright suites (scratch vs setup vs seeded), Merge-request E2E evidence (no HA in GitHub Actions) | `local-development.md` |
| mock-scale, docs, Mock esp32dev scale (local T1/T2), Live-shaped entities, NFC stub (option B), How to drive the mock, After HA is up (and OpenBao login for Playwright if needed):, Developer Tools → Services, or e2e helpers in e2e/helpers/mock-scale.ts, Set gross calibrated mass, Select ingredient (simulates NFC without UID map), Or NFC path:, Net mass is 0 until inject rises — or set Communifarm manual weigh: | `mock-scale.md` |
| onboarding, docs | `onboarding.md` |
| openbao, docs, OpenBao (HA test secrets), Secret location, Provision the Playwright token (first-time / rotate), 1) Login to HA via OpenBao username/password, mint token, write e2e/.generated/, 2) Patch kv/ha-test (requires bao login), Or both:, Start OpenBao (terminal 1), Bash (Git Bash / MSYS), PowerShell (reference), Unseal + login (terminal 2) | `openbao.md` |
| storage, docs, Communifarm SQLite (process / analysis data), Why not Recorder?, Master batch hub (`batches`), Culture media hub (`media_batches` + `culture_lots`), SQLite | `storage.md` |
| test-vm-deploy, docs, Test VM deployment (T3 only), Optional once: ssh-keyscan -H 192.168.102.20 >> scripts/known_hosts.test, On failure: | `test-vm-deploy.md` |
| versioning, docs, Versioning and merge | `versioning.md` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
