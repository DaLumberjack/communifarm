# fixtures

## Purpose

Communifarm HA custom component subtree.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `fixture`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `__init__.py` | `config` | Shared fixture contracts for local mocks (entity ID surfaces). — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `cf_aio868.py` | `ops` | Entity ID contract for cf-lab-aio868 KinCony AIO machine-controller mock. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `cf_nfc_reader.py` | `ops` | Entity ID contract for dedicated Communifarm NFC reader mocks. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `cf_tent_sensor.py` | `ops` | Entity ID contract for cf-tent1-sensor01 tent environment + calibration mock. — Runbooks/scripts — inspect before execute; no secrets in git. |
| `esp32dev_scale.py` | `ops` | Entity ID contract for the local esp32dev scale mock (matches live names). — Runbooks/scripts — inspect before execute; no secrets in git. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| config, init | `__init__.py` |
| cf aio868, ops, ENTITY_AIO_INTAKE, ENTITY_AIO_EXHAUST, ENTITY_AIO_CIRCULATION, ENTITY_AIO_HUMIDIFIER, ENTITY_AIO_HEATER, ENTITY_AIO_PUMP, ENTITY_AIO_VALVE, ENTITY_AIO_FALLBACK, ENTITY_AIO_CONTROL_STATE, ENTITY_AIO_SAFE_ACTUATION | `cf_aio868.py` |
| cf nfc reader, ops, ENTITY_NFC_SCAN_UID, ENTITY_NFC_WRITE_UID, ENTITY_NFC_WRITE_PREPARE, ENTITY_FIELD_CAPACITY_PCT, ENTITY_SHARED_LAST_NFC_UID, CF_NFC_PUBLIC_ENTITIES, CF_NFC_MOCK_INJECTORS, nfc, reader | `cf_nfc_reader.py` |
| cf tent sensor, ops, ENTITY_TENT1_BME_TEMP_CAL, ENTITY_TENT1_BME_HUM_CAL, ENTITY_TENT1_BME_PRESSURE_CAL, ENTITY_TENT1_SHT_TEMP_CAL, ENTITY_TENT1_SHT_HUM_CAL, ENTITY_TENT1_OW_TEMP_CAL, CF_TENT_SENSOR_PUBLIC_ENTITIES, CF_TENT_SENSOR_CALIBRATION_NUMBERS, CF_TENT_SENSOR_CALIBRATION_BUTTONS, CF_TENT_SENSOR_MOCK_INJECTORS | `cf_tent_sensor.py` |
| esp32dev scale, ops, ENTITY_ESP32DEV_CALIBRATED_G, ENTITY_ESP32DEV_CALIBRATED_SENSOR, ENTITY_ESP32DEV_CALIBRATION_VALUE, ENTITY_ESP32DEV_G, ENTITY_ESP32DEV_KG, ENTITY_ESP32DEV_RAW, ENTITY_ESP32DEV_RAW_SCALE_VALUE, ENTITY_ESP32DEV_TARED_MASS, ENTITY_ESP32DEV_TEMPERATURE, ENTITY_ESP32DEV_HUMIDITY | `esp32dev_scale.py` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
