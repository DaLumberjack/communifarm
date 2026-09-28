"""Entity ID contract for the local esp32dev scale mock (matches live names)."""

from __future__ import annotations

ENTITY_ESP32DEV_CALIBRATED_G = "sensor.esp32dev_calibrated_g"
ENTITY_ESP32DEV_CALIBRATED_SENSOR = "sensor.esp32dev_calibrated_sensor"
ENTITY_ESP32DEV_CALIBRATION_VALUE = "sensor.esp32dev_calibration_value"
ENTITY_ESP32DEV_G = "sensor.esp32dev_g"
ENTITY_ESP32DEV_KG = "sensor.esp32dev_kg"
ENTITY_ESP32DEV_RAW = "sensor.esp32dev_raw"
ENTITY_ESP32DEV_RAW_SCALE_VALUE = "sensor.esp32dev_raw_scale_value"
ENTITY_ESP32DEV_TARED_MASS = "sensor.esp32dev_tared_mass_on_scale"
ENTITY_ESP32DEV_TEMPERATURE = "sensor.esp32dev_temperature"
ENTITY_ESP32DEV_HUMIDITY = "sensor.esp32dev_humidity"
ENTITY_ESP32DEV_PRESSURE = "sensor.esp32dev_pressure"
ENTITY_ESP32DEV_LAST_RECORDED = "sensor.esp32dev_last_recorded"
ENTITY_ESP32DEV_TARE = "button.esp32dev_tare"
ENTITY_ESP32DEV_LOCATION_TARE = "button.esp32dev_location_tare"
ENTITY_ESP32DEV_RECORD_WEIGHT = "button.esp32dev_record_weight"
ENTITY_ESP32DEV_SCALE_BASE_WEIGHT = "number.esp32dev_scale_base_weight"
ENTITY_ESP32DEV_SCALE_WEIGHTLESS_CAL = "number.esp32dev_scale_weightless_calibration"
ENTITY_ESP32DEV_SELECTED_INGREDIENT = "input_select.esp32dev_selected_ingredient"

# Public surface — prefer these in Communifarm bindings / process code.
ESP32DEV_PUBLIC_ENTITIES: tuple[str, ...] = (
    ENTITY_ESP32DEV_CALIBRATED_G,
    ENTITY_ESP32DEV_CALIBRATED_SENSOR,
    ENTITY_ESP32DEV_CALIBRATION_VALUE,
    ENTITY_ESP32DEV_G,
    ENTITY_ESP32DEV_KG,
    ENTITY_ESP32DEV_RAW,
    ENTITY_ESP32DEV_RAW_SCALE_VALUE,
    ENTITY_ESP32DEV_TARED_MASS,
    ENTITY_ESP32DEV_TEMPERATURE,
    ENTITY_ESP32DEV_HUMIDITY,
    ENTITY_ESP32DEV_PRESSURE,
    ENTITY_ESP32DEV_LAST_RECORDED,
    ENTITY_ESP32DEV_TARE,
    ENTITY_ESP32DEV_LOCATION_TARE,
    ENTITY_ESP32DEV_RECORD_WEIGHT,
    ENTITY_ESP32DEV_SCALE_BASE_WEIGHT,
    ENTITY_ESP32DEV_SCALE_WEIGHTLESS_CAL,
    ENTITY_ESP32DEV_SELECTED_INGREDIENT,
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
