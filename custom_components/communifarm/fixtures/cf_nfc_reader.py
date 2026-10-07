"""Entity ID contract for dedicated Communifarm NFC reader mocks."""

from __future__ import annotations

ENTITY_NFC_SCAN_UID = "sensor.cf_mixroom_nfc_scan01_last_nfc_uid"
ENTITY_NFC_WRITE_UID = "sensor.cf_lab_nfc_write01_last_nfc_uid"
ENTITY_NFC_WRITE_PREPARE = "button.cf_lab_nfc_write01_prepare_ndef_write"

# Shared with scale stub / harvest services — still the primary last-scan text helper.
ENTITY_SHARED_LAST_NFC_UID = "input_text.esp32dev_last_nfc_uid"

CF_NFC_PUBLIC_ENTITIES: tuple[str, ...] = (
    ENTITY_NFC_SCAN_UID,
    ENTITY_NFC_WRITE_UID,
    ENTITY_NFC_WRITE_PREPARE,
)

CF_NFC_MOCK_INJECTORS: tuple[str, ...] = (
    "input_text.cf_mixroom_nfc_scan01_last_nfc_uid",
    "input_text.cf_lab_nfc_write01_last_nfc_uid",
    "input_button.cf_mixroom_nfc_scan01_simulate_scan",
    "input_button.cf_lab_nfc_write01_simulate_scan",
)
