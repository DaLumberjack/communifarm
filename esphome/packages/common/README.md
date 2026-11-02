# common

## Purpose

Workspace directory `repos/communifarm/esphome/packages/common`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `esphome`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `base.yaml` | `esphome` | esphome file `base.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `diagnostics.yaml` | `esphome` | esphome file `diagnostics.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `failsafe.yaml` | `esphome` | esphome file `failsafe.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `network-wifi.yaml` | `esphome` | esphome file `network-wifi.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `provisioning.yaml` | `esphome` | esphome file `provisioning.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |
| `sensor-calibration.yaml` | `esphome` | esphome file `sensor-calibration.yaml`. — Device YAML — compile-tested; no guessed pin maps. |

## Feature index

| keywords / features | path |
|---------------------|------|
| base, esphome, logger, api, ota | `base.yaml` |
| diagnostics, esphome, text_sensor, sensor, binary_sensor | `diagnostics.yaml` |
| failsafe, esphome, globals, text_sensor, switch | `failsafe.yaml` |
| network-wifi, esphome, wifi, captive_portal | `network-wifi.yaml` |
| provisioning, esphome, improv_serial, esp32_improv | `provisioning.yaml` |
| sensor-calibration, esphome, number, button, sensor, text_sensor | `sensor-calibration.yaml` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
