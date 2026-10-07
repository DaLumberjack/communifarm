# Sensor calibration (reusable)

Field offsets for BME688 / SHT3x / OneWire (and any future node that includes the package).

| Item | Location |
| --- | --- |
| ESPHome package | `esphome/packages/common/sensor-calibration.yaml` |
| Included by | tent sensor devices (and any other role that needs it) |
| HA mock | `devcontainer/ha_config/packages/mock_cf_tent_sensor.yaml` |

## Why this is separate

Calibration is semi-frequent and hardware-agnostic. Keep offsets / reference capture in one package so tent sensors, future mix-room monitors, and lab fixtures share the same workflow instead of forking YAML per board.

## Workflow

| Step | Action |
| --- | --- |
| 1 | Place a trusted reference thermometer / hygrometer / barometer next to the probe |
| 2 | Set **Reference Temperature / Humidity / Pressure** (HA number or device number) |
| 3 | Press **Capture \<channel\> Offset** for each sensor to calibrate |
| 4 | Bind Communifarm to **\* Calibrated** sensors, not raw diagnostics |
| 5 | Re-run capture when a probe drifts or after a node swap |

`offset = reference − raw`  
`calibrated = raw + offset`

Offsets restore on the ESP (`restore_value: true`) and show up in HA as native number entities for the live device.

## Channels

| Channel | Raw (diagnostic) | Offset number | Capture button | Calibrated output |
| --- | --- | --- | --- | --- |
| BME688 temp | BME Temperature Raw | BME Temp Offset | Capture BME Temp Offset | BME Temperature Calibrated |
| BME688 humidity | BME Humidity Raw | BME Humidity Offset | Capture BME Humidity Offset | BME Humidity Calibrated |
| BME688 pressure | BME Pressure Raw | BME Pressure Offset | Capture BME Pressure Offset | BME Pressure Calibrated |
| SHT3x temp | SHT Temperature Raw | SHT Temp Offset | Capture SHT Temp Offset | SHT Temperature Calibrated |
| SHT3x humidity | SHT Humidity Raw | SHT Humidity Offset | Capture SHT Humidity Offset | SHT Humidity Calibrated |
| OneWire temp | OneWire Temperature Raw | OneWire Temp Offset | Capture OneWire Temp Offset | OneWire Temperature Calibrated |

**Reset All Sensor Offsets** clears every offset to `0`.

## Reuse on another ESP device

```yaml
packages:
  calibration: !include ../packages/common/sensor-calibration.yaml
  # role must define: cf_raw_bme_*, cf_raw_sht_*, cf_raw_ow_temperature
```

If a device lacks a channel, either stub the raw id with a disabled template sensor or fork a thinner calibration package later — do not remove the shared package without updating all includers.

## BSEC2 IAQ (optional)

`packages/roles/sensor-bme68x-bsec2.yaml` adds Bosch IAQ / CO₂-eq. License forbids redistributing compiled binaries that include BSEC2 — keep it off CI and shared release builds.
