# Fixed / mock fixtures

## Local mocks (T1/T2)

| Fixture | Docs |
| --- | --- |
| Env sensors / fan / exhaust | `devcontainer/ha_config/configuration.yaml` |
| Tent sensor S3 + cal `cf-tent1-sensor01_*` | `packages/mock_cf_tent_sensor.yaml`, [sensor-calibration.md](sensor-calibration.md) |
| AIO868 machine controls | `packages/mock_cf_aio868.yaml`, [esphome-devices.md](esphome-devices.md) |
| Dedicated NFC scan/write | `packages/mock_cf_nfc_reader.yaml`, [nfc-readers-d1-mini32.md](nfc-readers-d1-mini32.md) |
| Manual fan tachometer / vents | `packages/mock_cf_tachometer.yaml`, [air-exchange-tachometer.md](air-exchange-tachometer.md) |
| Scale `esp32dev_*` + NFC select stub | `packages/mock_esp32dev_scale.yaml`, [mock-scale.md](../user/mock-scale.md) |
| ESP32 D1 Mini32 NFC wiring | [nfc-readers-d1-mini32.md](nfc-readers-d1-mini32.md) |
| ESPHome packages / devices | [esphome-devices.md](esphome-devices.md), `esphome/README.md` |

Controllable via `input_number` / `input_select` / `button.press` / `switch.turn_on`. Prefer mocks for code-flow tests.

## Live test VM (T3)

Record the fixed ESPHome device registry id, entity ids, and safe actuator allowlist in the workspace intermediate contract (`docs/intermediate/test-ha-contract.md`). Do not invent pin mappings.

Dedicated lab scale/NFC hardware (not floor production gear) should be used when testing human process flows — see workspace `docs/intermediate/weigh-station-process-deferred.md`.
