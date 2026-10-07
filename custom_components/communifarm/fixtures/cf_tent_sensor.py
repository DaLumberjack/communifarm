"""Entity ID contract for cf-tent1-sensor01 tent environment + calibration mock."""

from __future__ import annotations

# Preferred Communifarm bindings — calibrated channels.
ENTITY_TENT1_BME_TEMP_CAL = "sensor.cf_tent1_sensor01_bme_temperature_calibrated"
ENTITY_TENT1_BME_HUM_CAL = "sensor.cf_tent1_sensor01_bme_humidity_calibrated"
ENTITY_TENT1_BME_PRESSURE_CAL = "sensor.cf_tent1_sensor01_bme_pressure_calibrated"
ENTITY_TENT1_SHT_TEMP_CAL = "sensor.cf_tent1_sensor01_sht_temperature_calibrated"
ENTITY_TENT1_SHT_HUM_CAL = "sensor.cf_tent1_sensor01_sht_humidity_calibrated"
ENTITY_TENT1_OW_TEMP_CAL = "sensor.cf_tent1_sensor01_onewire_temperature_calibrated"

CF_TENT_SENSOR_PUBLIC_ENTITIES: tuple[str, ...] = (
    ENTITY_TENT1_BME_TEMP_CAL,
    ENTITY_TENT1_BME_HUM_CAL,
    ENTITY_TENT1_BME_PRESSURE_CAL,
    ENTITY_TENT1_SHT_TEMP_CAL,
    ENTITY_TENT1_SHT_HUM_CAL,
    ENTITY_TENT1_OW_TEMP_CAL,
)

CF_TENT_SENSOR_CALIBRATION_NUMBERS: tuple[str, ...] = (
    "input_number.cf_tent1_sensor01_bme_temp_offset",
    "input_number.cf_tent1_sensor01_bme_hum_offset",
    "input_number.cf_tent1_sensor01_bme_pressure_offset",
    "input_number.cf_tent1_sensor01_sht_temp_offset",
    "input_number.cf_tent1_sensor01_sht_hum_offset",
    "input_number.cf_tent1_sensor01_ow_temp_offset",
    "input_number.cf_tent1_sensor01_reference_temperature",
    "input_number.cf_tent1_sensor01_reference_humidity",
    "input_number.cf_tent1_sensor01_reference_pressure",
)

CF_TENT_SENSOR_CALIBRATION_BUTTONS: tuple[str, ...] = (
    "input_button.cf_tent1_sensor01_capture_bme_temp",
    "input_button.cf_tent1_sensor01_capture_bme_hum",
    "input_button.cf_tent1_sensor01_capture_bme_pressure",
    "input_button.cf_tent1_sensor01_capture_sht_temp",
    "input_button.cf_tent1_sensor01_capture_sht_hum",
    "input_button.cf_tent1_sensor01_capture_ow_temp",
    "input_button.cf_tent1_sensor01_reset_all_offsets",
)

CF_TENT_SENSOR_MOCK_INJECTORS: tuple[str, ...] = (
    "input_number.cf_tent1_sensor01_inject_bme_temperature_raw",
    "input_number.cf_tent1_sensor01_inject_bme_humidity_raw",
    "input_number.cf_tent1_sensor01_inject_bme_pressure_raw",
    "input_number.cf_tent1_sensor01_inject_sht_temperature_raw",
    "input_number.cf_tent1_sensor01_inject_sht_humidity_raw",
    "input_number.cf_tent1_sensor01_inject_ow_temperature_raw",
)

# Backward-compatible aliases used by older tests/docs wording.
ENTITY_TENT1_TEMPERATURE = ENTITY_TENT1_BME_TEMP_CAL
ENTITY_TENT1_HUMIDITY = ENTITY_TENT1_BME_HUM_CAL
ENTITY_TENT1_PRESSURE = ENTITY_TENT1_BME_PRESSURE_CAL
