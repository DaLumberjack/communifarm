# .devcontainer

## Purpose

Workspace directory `repos/communifarm/.devcontainer`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `dir`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `devcontainer.json` | `config` | config file `devcontainer.json`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `docker-compose.yml` | `config` | config file `docker-compose.yml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| devcontainer, config | `devcontainer.json` |
| docker-compose, config, services | `docker-compose.yml` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
