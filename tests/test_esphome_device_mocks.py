"""Contract tests for Communifarm ESPHome HA mock packages and YAML layout."""

from __future__ import annotations

import re
from pathlib import Path

from custom_components.communifarm.fixtures.cf_aio868 import (
    CF_AIO868_MACHINE_SWITCHES,
    CF_AIO868_PUBLIC_ENTITIES,
)
from custom_components.communifarm.fixtures.cf_nfc_reader import (
    CF_NFC_MOCK_INJECTORS,
    CF_NFC_PUBLIC_ENTITIES,
)
from custom_components.communifarm.fixtures.cf_tent_sensor import (
    CF_TENT_SENSOR_CALIBRATION_BUTTONS,
    CF_TENT_SENSOR_CALIBRATION_NUMBERS,
    CF_TENT_SENSOR_MOCK_INJECTORS,
    CF_TENT_SENSOR_PUBLIC_ENTITIES,
)

REPO = Path(__file__).resolve().parents[1]
PACKAGES = REPO / "devcontainer" / "ha_config" / "packages"
ESPHOME = REPO / "esphome"


def test_tent_sensor_package_exposes_public_surface() -> None:
    text = (PACKAGES / "mock_cf_tent_sensor.yaml").read_text(encoding="utf-8")
    assert "cf-tent1-sensor01 BME Temperature Calibrated" in text
    assert "cf-tent1-sensor01 SHT Humidity Calibrated" in text
    assert "cf-tent1-sensor01 OneWire Temperature Calibrated" in text
    assert "Capture BME Temp Offset" in text
    assert CF_TENT_SENSOR_MOCK_INJECTORS[0] in text
    assert len(CF_TENT_SENSOR_PUBLIC_ENTITIES) == 6
    assert len(CF_TENT_SENSOR_CALIBRATION_NUMBERS) >= 9
    assert len(CF_TENT_SENSOR_CALIBRATION_BUTTONS) >= 7
    for entity_id in CF_TENT_SENSOR_PUBLIC_ENTITIES:
        assert "cf_tent1_sensor01" in entity_id


def test_sensor_calibration_package_is_reusable() -> None:
    cal = (ESPHOME / "packages" / "common" / "sensor-calibration.yaml").read_text(
        encoding="utf-8"
    )
    assert "cf_cal_bme_temp_offset" in cal
    assert "Capture BME Temp Offset" in cal
    assert "Reset All Sensor Offsets" in cal
    tent = (ESPHOME / "devices" / "cf-tent1-sensor01.yaml").read_text(encoding="utf-8")
    assert "esp32-s3-wroom-1.yaml" in tent
    assert "sensor-calibration.yaml" in tent
    monitor = (ESPHOME / "packages" / "roles" / "sensor-monitor.yaml").read_text(
        encoding="utf-8"
    )
    assert "bme680" in monitor
    assert "sht3xd" in monitor
    assert "dallas_temp" in monitor


def test_aio868_package_exposes_machine_switches() -> None:
    text = (PACKAGES / "mock_cf_aio868.yaml").read_text(encoding="utf-8")
    assert "cf-lab-aio868 Intake" in text
    assert "cf-lab-aio868 Exhaust" in text
    assert "cf-lab-aio868 Fallback Enabled" in text
    assert len(CF_AIO868_MACHINE_SWITCHES) == 7
    for entity_id in CF_AIO868_PUBLIC_ENTITIES:
        assert "cf_lab_aio868" in entity_id


def test_nfc_reader_package_exposes_scan_and_write_surfaces() -> None:
    text = (PACKAGES / "mock_cf_nfc_reader.yaml").read_text(encoding="utf-8")
    assert "cf-mixroom-nfc-scan01 Last NFC UID" in text
    assert "cf-lab-nfc-write01 Prepare NDEF Write" in text
    for entity_id in CF_NFC_PUBLIC_ENTITIES:
        assert entity_id.split(".", 1)[0] in {"sensor", "button"}
    assert CF_NFC_MOCK_INJECTORS[0] in text


def test_esphome_device_files_exist() -> None:
    expected = (
        "cf-tent1-sensor01.yaml",
        "cf-mixroom-scale01.yaml",
        "cf-mixroom-nfc-scan01.yaml",
        "cf-lab-nfc-write01.yaml",
        "cf-lab-aio868.yaml",
    )
    for name in expected:
        assert (ESPHOME / "devices" / name).is_file()
        assert (ESPHOME / "examples" / "compile" / name).is_file()


def test_esphome_packages_cover_roles_and_boards() -> None:
    for relative in (
        "packages/common/base.yaml",
        "packages/boards/esp32-d1-mini32.yaml",
        "packages/boards/kincony-kc868-aio.yaml",
        "packages/common/sensor-calibration.yaml",
        "packages/boards/esp32-s3-wroom-1.yaml",
        "packages/roles/sensor-monitor.yaml",
        "packages/roles/sensor-bme68x-bsec2.yaml",
        "packages/roles/motor-controller.yaml",
        "packages/roles/scale-station.yaml",
        "packages/roles/nfc-scanner.yaml",
        "packages/roles/nfc-writer.yaml",
    ):
        assert (ESPHOME / relative).is_file()


def test_kincony_board_package_does_not_publish_gpio_maps() -> None:
    text = (ESPHOME / "packages" / "boards" / "kincony-kc868-aio.yaml").read_text(
        encoding="utf-8"
    )
    assert "NOT published" in text
    assert re.search(r"GPIO\d+", text) is None
    assert re.search(r"(?m)^\s*pin:\s*\S+", text) is None
