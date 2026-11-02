# roles

## Purpose

Workspace directory `repos/communifarm/esphome/packages/roles`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `esphome`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `motor-controller.yaml` | `esphome` | esphome file `motor-controller.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `nfc-scanner.yaml` | `esphome` | esphome file `nfc-scanner.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `nfc-writer.yaml` | `esphome` | esphome file `nfc-writer.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |
| `scale-station.yaml` | `esphome` | esphome file `scale-station.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `sensor-bme68x-bsec2.yaml` | `esphome` | esphome file `sensor-bme68x-bsec2.yaml`. — Device YAML — compile-tested; no guessed pin maps. |
| `sensor-monitor.yaml` | `esphome` | esphome file `sensor-monitor.yaml`. — Device YAML — compile-tested; no guessed pin maps. |

## Feature index

| keywords / features | path |
|---------------------|------|
| motor-controller, esphome, switch, binary_sensor | `motor-controller.yaml` |
| nfc-scanner, esphome, i2c, pn532_i2c, text_sensor | `nfc-scanner.yaml` |
| nfc-writer, esphome, spi, pn532_spi, text_sensor, button | `nfc-writer.yaml` |
| scale-station, esphome, i2c, globals, sensor, button | `scale-station.yaml` |
| sensor-bme68x-bsec2, esphome, bme68x_bsec2_i2c, sensor, text_sensor | `sensor-bme68x-bsec2.yaml` |
| sensor-monitor, esphome, i2c, one_wire, sensor | `sensor-monitor.yaml` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
