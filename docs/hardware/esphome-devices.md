# Communifarm ESPHome devices

Reusable ESPHome packages and HA template mocks for Communifarm device roles.

| Role | Hardware | ESPHome device | HA T1 package |
| --- | --- | --- | --- |
| Tent / env sensors | **ESP32-S3-WROOM-1** + BME688 + SHT3x + OneWire | `esphome/devices/cf-tent1-sensor01.yaml` | `mock_cf_tent_sensor.yaml` |
| Scale station | ESP32 D1 Mini32 / esp32dev + HX711 | `esphome/devices/cf-mixroom-scale01.yaml` | `mock_esp32dev_scale.yaml` (live-shaped `esp32dev_*`) |
| NFC scan-only | D1 Mini32 + PN532 I2C | `esphome/devices/cf-mixroom-nfc-scan01.yaml` | `mock_cf_nfc_reader.yaml` |
| NFC R/W bench | D1 Mini32 + PN532 SPI | `esphome/devices/cf-lab-nfc-write01.yaml` | `mock_cf_nfc_reader.yaml` |
| Machine controls | KinCony KC868-AIO | `esphome/devices/cf-lab-aio868.yaml` | `mock_cf_aio868.yaml` |

Generic env mocks (`sensor.mock_temperature`, `fan.mock_circulation_fan`, `switch.mock_exhaust`) remain in `configuration.yaml` for older tests.

Custom / future devices may use other modules (D1 Mini32, etc.). **Home tent sensors are ESP32-S3-WROOM-1** because those boards are already soldered.

## Shared calibration

| Package | Purpose |
| --- | --- |
| `esphome/packages/common/sensor-calibration.yaml` | Offsets, reference numbers, capture/reset buttons, calibrated outputs |
| [sensor-calibration.md](sensor-calibration.md) | Operator workflow |

Include the calibration package on any ESP node that needs semi-frequent field offsets.

## Board notes

| Board | Doc | Pin policy |
| --- | --- | --- |
| ESP32-S3-WROOM-1 | this page + device substitutions | Tent sensors; pins set per soldered harness (not guessed) |
| ESP32-WROOM-32 D1 Mini clone | [esp32-wroom-32-d1-mini-clone.md](esp32-wroom-32-d1-mini-clone.md) | NFC / lightweight custom nodes |
| NFC wiring | [nfc-readers-d1-mini32.md](nfc-readers-d1-mini32.md) | PN532 I2C scan; PN532 SPI / RC522 SPI with non-strap CS |
| KinCony KC868-AIO | this page | **No guessed relay GPIO.** Template switches until manufacturer map verified |

## Why AIO868 uses template switches

Communifarm policy: do not publish guessed pin mappings. The AIO package exposes semantic actuators (`Intake`, `Exhaust`, `Circulation`, `Humidifier`, `Heater`, `Pump`, `Valve`, `Fallback Enabled`) so onboarding and climate binding can proceed in T1. Replace templates with verified GPIO/relay platforms before T3 live actuation.

## Devcontainer injectors

| Device | Inject |
| --- | --- |
| Tent sensor | raw injectors + offset numbers + capture buttons — see [sensor-calibration.md](sensor-calibration.md) |
| AIO868 | `switch.turn_on/off` on `switch.cf_lab_aio868_*` |
| NFC scan | set `input_text.cf_mixroom_nfc_scan01_last_nfc_uid` then press simulate |
| Scale / shared harvest UID | existing `esp32dev_*` + `input_text.esp32dev_last_nfc_uid` |

## Testing

| Stage | Coverage |
| --- | --- |
| T0 | `tests/test_esphome_device_mocks.py`, `tests/test_esp32dev_scale_contract.py` |
| T1 | packages auto-loaded via `homeassistant.packages: !include_dir_named packages` |
| ESPHome compile | CI job builds `esphome/examples/compile/*.yaml` (no BSEC2) |
| T3 | Live lab hardware only; never floor production gear |

## Sources

- Workspace intake: `docs/intake/esp devices/scale.yaml`, D1 Mini32 pinout image
- ESPboards D1 Mini32 pinout (CC BY-NC 4.0)
- ESPHome BME680/BME688, SHT3xD, Dallas OneWire, RC522 / PN532 / SPI docs
- `.agents/skills/esphome-devices/SKILL.md`
