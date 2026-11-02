# packages

## Purpose

Workspace directory `repos/communifarm/devcontainer/ha_config/packages`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `dir`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `mock_cf_aio868.yaml` | `config` | config file `mock_cf_aio868.yaml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `mock_cf_nfc_reader.yaml` | `config` | config file `mock_cf_nfc_reader.yaml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `mock_cf_tachometer.yaml` | `config` | config file `mock_cf_tachometer.yaml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `mock_cf_tent_sensor.yaml` | `config` | config file `mock_cf_tent_sensor.yaml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `mock_esp32dev_scale.yaml` | `config` | config file `mock_esp32dev_scale.yaml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| mock cf aio868, config, input_boolean, input_text, template | `mock_cf_aio868.yaml` |
| mock cf nfc reader, config, input_text, input_select, input_number, input_button, template, automation | `mock_cf_nfc_reader.yaml` |
| mock cf tachometer, config, input_text, input_select, input_number, input_button, automation | `mock_cf_tachometer.yaml` |
| mock cf tent sensor, config, input_number, input_button, template, automation | `mock_cf_tent_sensor.yaml` |
| mock esp32dev scale, config, input_number, input_text, input_select, input_button, template, automation | `mock_esp32dev_scale.yaml` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
