# Local Home Assistant fixtures for Communifarm T1/T2

**Prerequisite:** Start the **Docker Desktop** application before `docker compose ... up`. The CLI alone is not enough; `docker version` must show a Server section. Details: [docs/user/local-development.md](../docs/user/local-development.md).

## What is committed vs ignored

| Commit (share with next developer) | Ignore (secrets / regenerable) |
|------------------------------------|--------------------------------|
| `configuration.yaml` (mock ESP entities) | `.storage/` (auth, tokens, registries) |
| `README.md` | `.cache/`, `.cloud/` |
| Default `blueprints/` shipped with HA | `home-assistant_v2.db*`, logs, `tts/` |
| `.devcontainer/*` compose + JSON | `backups/*.tar` (use workspace intake + OpenBao keys) |
| Repo-root `custom_components/communifarm/` | Nested `ha_config/custom_components/` (bind-mount overlay) |

Next developer: `docker compose -f .devcontainer/docker-compose.yml up -d homeassistant`, then either complete onboarding once, restore a backup from workspace `docs/intake/Dev Container Backups/` (keys via OpenBao / emergency kit intake — never git), or reuse a local `.storage` that is never pushed.

| Profile | Purpose |
|---------|---------|
| Empty / standalone | Communifarm mounted under `custom_components/communifarm`, no config entry yet |
| Mocked ESP set | `sensor.mock_temperature`, `sensor.mock_humidity`, `fan.mock_circulation_fan`, `switch.mock_exhaust` |
| Tent sensor (S3) | calibrated BME/SHT/OneWire + offsets — `packages/mock_cf_tent_sensor.yaml` |
| AIO868 machines | `switch.cf_lab_aio868_*` — `packages/mock_cf_aio868.yaml` |
| Dedicated NFC | `cf_mixroom_nfc_scan01_*` / `cf_lab_nfc_write01_*` — `packages/mock_cf_nfc_reader.yaml` |
| Manual tachometer | vent label / value / timestamp helpers — `packages/mock_cf_tachometer.yaml` |
| Mocked scale + NFC stub | `esp32dev_*` live-shaped entities — see [docs/user/mock-scale.md](../docs/user/mock-scale.md) |
| Seeded state | Local-only `.storage` or restored backup — not committed |

ESPHome YAML mockups live in `esphome/` (packages + devices). See [docs/hardware/esphome-devices.md](../docs/hardware/esphome-devices.md).

## Injecting conditions

```bash
# Environment mocks
# input_number.set_value → input_number.mock_temperature

# Scale mock (same IDs as live esp32dev)
# input_number.set_value → input_number.esp32dev_inject_calibrated_sensor
# input_select.select_option → input_select.esp32dev_selected_ingredient
# button.press → button.esp32dev_tare / button.esp32dev_record_weight
```

Mocks are the default for T1/T2. Live ESPHome in the devcontainer is a special case (networking + dedicated lab hardware) — documented in mock-scale.md. Human weigh/NFC process UI is deferred.

