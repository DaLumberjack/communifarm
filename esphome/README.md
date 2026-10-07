# ESPHome packages and device mockups for Communifarm

```text
esphome/
├── packages/
│   ├── common/     base, wifi, diagnostics, provisioning, failsafe
│   ├── boards/     d1-mini32, esp32-s3-wroom-1, kincony-kc868-aio (no guessed pins)
│   └── roles/      sensor-monitor, motor-controller, scale-station, nfc-scanner, nfc-writer
├── devices/        deployment YAML (uses !secret wifi_*)
└── examples/compile/  CI compile targets (dummy Wi-Fi, no secrets)
```

| Device | Board | Role | HA T1 mock |
| --- | --- | --- | --- |
| `cf-tent1-sensor01` | **ESP32-S3-WROOM-1** | BME688 + SHT3x + OneWire + calibration | `packages/mock_cf_tent_sensor.yaml` |
| `cf-mixroom-scale01` | D1 Mini32 / esp32dev | scale | existing `mock_esp32dev_scale.yaml` |
| `cf-mixroom-nfc-scan01` | D1 Mini32 + PN532 I2C | scan-only NFC | `packages/mock_cf_nfc_reader.yaml` |
| `cf-lab-nfc-write01` | D1 Mini32 + PN532 SPI | bench R/W | same NFC mock injectors |
| `cf-lab-aio868` | KinCony KC868-AIO | machine controls | `packages/mock_cf_aio868.yaml` |

Shared calibration: `packages/common/sensor-calibration.yaml` (include on any env node).  
KinCony relays stay **template switches** until manufacturer pin maps are verified.

Docs: `docs/hardware/esphome-devices.md`, `docs/hardware/sensor-calibration.md`
