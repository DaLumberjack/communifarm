# hardware

## Purpose

Workspace directory `repos/communifarm/docs/hardware`.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `docs`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `air-exchange-tachometer.md` | `docs` | Manual fan tachometer / air exchange — Operator/architecture docs — same change as code when user-visible. |
| `esp32-wroom-32-d1-mini-clone.md` | `docs` | ESP32-WROOM-32 D1 Mini Clone — Operator/architecture docs — same change as code when user-visible. |
| `esphome-devices.md` | `docs` | Communifarm ESPHome devices — Operator/architecture docs — same change as code when user-visible. |
| `fixtures.md` | `docs` | Fixed / mock fixtures — Operator/architecture docs — same change as code when user-visible. |
| `nfc-readers-d1-mini32.md` | `docs` | NFC Readers On ESP32 D1 Mini32 — Operator/architecture docs — same change as code when user-visible. |
| `README.md` | `docs` | This directory map (dim1 Map + dim2 Feature index). |
| `sensor-calibration.md` | `docs` | Sensor calibration (reusable) — Operator/architecture docs — same change as code when user-visible. |

## Feature index

| keywords / features | path |
|---------------------|------|
| air-exchange-tachometer, docs, Manual fan tachometer / air exchange, Why manual first, Workflow, Units, Devcontainer helpers, Testing, Sources | `air-exchange-tachometer.md` |
| esp32-wroom-32-d1-mini-clone, docs, ESP32-WROOM-32 D1 Mini Clone, Safe First-Pick Pins, Pins To Avoid For NFC Builds, Recommended Communifarm NFC Pin Budget, Electrical Notes, ESPHome Skeleton, Sources | `esp32-wroom-32-d1-mini-clone.md` |
| esphome-devices, docs, Communifarm ESPHome devices, Shared calibration, Board notes, Why AIO868 uses template switches, Devcontainer injectors, Testing, Sources, ESPHome | `esphome-devices.md` |
| fixtures, docs, Fixed / mock fixtures, Local mocks (T1/T2), Live test VM (T3) | `fixtures.md` |
| nfc-readers-d1-mini32, docs, NFC Readers On ESP32 D1 Mini32, Board Pins Used, Wiring Diagram: PN532 Mobile Scanner, Wiring Diagram: RC522 SPI Reader, NFC | `nfc-readers-d1-mini32.md` |
| sensor-calibration, docs, Sensor calibration (reusable), Why this is separate, Workflow, Channels, Reuse on another ESP device, BSEC2 IAQ (optional) | `sensor-calibration.md` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
