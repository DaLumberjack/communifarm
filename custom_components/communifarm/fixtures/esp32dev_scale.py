"""Entity ID contract for the local esp32dev scale mock (matches live names)."""

from __future__ import annotations

# Public surface — prefer these in Communifarm bindings / process code.
ESP32DEV_PUBLIC_ENTITIES: tuple[str, ...] = (
    "sensor.esp32dev_calibrated_g",
    "sensor.esp32dev_calibrated_sensor",
    "sensor.esp32dev_calibration_value",
    "sensor.esp32dev_g",
    "sensor.esp32dev_kg",
    "sensor.esp32dev_raw",
    "sensor.esp32dev_raw_scale_value",
    "sensor.esp32dev_tared_mass_on_scale",
    "sensor.esp32dev_temperature",
    "sensor.esp32dev_humidity",
    "sensor.esp32dev_pressure",
    "sensor.esp32dev_last_recorded",
    "button.esp32dev_tare",
    "button.esp32dev_location_tare",
    "button.esp32dev_record_weight",
    "number.esp32dev_scale_base_weight",
    "number.esp32dev_scale_weightless_calibration",
    "input_select.esp32dev_selected_ingredient",
)

# Mock injectors — T1 only; not on live ESPHome.
ESP32DEV_MOCK_INJECTORS: tuple[str, ...] = (
    "input_number.esp32dev_inject_calibrated_sensor",
    "input_number.esp32dev_tare_offset",
    "input_number.esp32dev_inject_raw",
    "input_number.esp32dev_inject_base_weight",
    "input_number.esp32dev_inject_weightless_cal",
    "input_number.esp32dev_inject_temperature",
    "input_number.esp32dev_inject_humidity",
    "input_number.esp32dev_inject_pressure",
    "input_text.esp32dev_last_recorded",
    "input_text.esp32dev_last_nfc_uid",
    "input_button.esp32dev_simulate_nfc_scan",
)

RECIPE_INGREDIENTS: tuple[str, ...] = (
    "hardwood pellets",
    "hardwood shavings",
    "shredded organic wheat straw",
    "organic worm castings",
    "organic wheat bran",
    "vermiculite",
    "coco coir",
    "gypsum",
    "potash",
)

NFC_UID_TO_INGREDIENT: dict[str, str] = {
    "nfc-hardwood-pellets": "hardwood pellets",
    "nfc-hardwood-shavings": "hardwood shavings",
    "nfc-wheat-straw": "shredded organic wheat straw",
    "nfc-worm-castings": "organic worm castings",
    "nfc-wheat-bran": "organic wheat bran",
    "nfc-vermiculite": "vermiculite",
    "nfc-coco-coir": "coco coir",
    "nfc-gypsum": "gypsum",
    "nfc-potash": "potash",
}
