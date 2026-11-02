# architecture

## Purpose

Workspace directory `repos/communifarm/docs/architecture`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `docs`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `mvp.md` | `docs` | MVP architecture — Operator/architecture docs — same change as code when user-visible. |
| `nfc-schema.md` | `docs` | NFC / tag identity schema (Communifarm SQLite) — Operator/architecture docs — same change as code when user-visible. |
| `README.md` | `docs` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| mvp, docs, MVP architecture, Entity bases, Persistence, Dashboard targets | `mvp.md` |
| nfc-schema, docs, NFC / tag identity schema (Communifarm SQLite), Truth rules, Resolve order (first match wins), ERD (UML), Tables (NFC-touching), Registry / audit, Domain rows with `nfc_uid`, Dual-write helper, NFC, SQLite | `nfc-schema.md` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
