# ha_config

## Purpose

Workspace directory `repos/communifarm/devcontainer/ha_config`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `dir`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `backups/` | `dir` | Child map — read `backups/README.md` before exploring. |
| `communifarm/` | `dir` | Child map — read `communifarm/README.md` before exploring. |
| `custom_components/` | `dir` | Child map — read `custom_components/README.md` before exploring. |
| `packages/` | `dir` | Child map — read `packages/README.md` before exploring. |
| `www/` | `ui` | Enter for ui work — read `www/README.md` (Feature index → Map). |
| `.ha_run.lock` | `ops` | ops file `.ha_run.lock`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `.HA_VERSION` | `ops` | ops file `.HA_VERSION`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `configuration.yaml` | `config` | config file `configuration.yaml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `home-assistant.log` | `ops` | ops file `home-assistant.log`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `home-assistant.log.1` | `ops` | ops file `home-assistant.log.1`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `home-assistant.log.fault` | `ops` | ops file `home-assistant.log.fault`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `home-assistant_v2.db` | `ops` | ops file `home-assistant_v2.db`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `home-assistant_v2.db-shm` | `ops` | ops file `home-assistant_v2.db-shm`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `home-assistant_v2.db-wal` | `ops` | ops file `home-assistant_v2.db-wal`. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| backups, dir | `backups/` |
| communifarm, dir | `communifarm/` |
| custom components, dir | `custom_components/` |
| packages, dir | `packages/` |
| www, ui | `www/` |
| .ha run, ops | `.ha_run.lock` |
| .HA VERSION, ops | `.HA_VERSION` |
| configuration, config, default_config, homeassistant, logger, template, input_number, input_boolean, switch | `configuration.yaml` |
| home-assistant, ops | `home-assistant.log` |
| home-assistant.log, ops | `home-assistant.log.1` |
| home-assistant.log, ops | `home-assistant.log.fault` |
| home-assistant v2, ops | `home-assistant_v2.db` |
| home-assistant v2, ops | `home-assistant_v2.db-shm` |
| home-assistant v2, ops | `home-assistant_v2.db-wal` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
