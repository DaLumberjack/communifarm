"""Constants for the Communifarm integration."""

from __future__ import annotations

DOMAIN = "communifarm"
VERSION = "0.1.0"

CONF_SITE_NAME = "site_name"
CONF_ENVIRONMENT_NAME = "environment_name"
CONF_BATCH_NAME = "batch_name"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_FAN_ENTITY = "fan_entity"
CONF_SWITCH_ENTITY = "switch_entity"
CONF_STIR_PLATE_ENTITY = "stir_plate_entity"
CONF_TEMPERATURE_TARGET = "temperature_target"
CONF_HUMIDITY_TARGET = "humidity_target"

DEFAULT_TEMPERATURE_TARGET = 22.0
DEFAULT_HUMIDITY_TARGET = 60.0

ATTR_SITE_ID = "site_id"
ATTR_ENVIRONMENT_ID = "environment_id"
ATTR_BATCH_ID = "batch_id"

STORAGE_KEY = f"{DOMAIN}.state"
STORAGE_VERSION = 1

DASHBOARD_URL_PATH = "communifarm"
DASHBOARD_TITLE = "Communifarm"
DASHBOARD_ICON = "mdi:sprout"
DASHBOARD_VIEW_OVERVIEW = "overview"
DASHBOARD_VIEW_WEIGH = "weigh"
DASHBOARD_VIEW_BATCHES = "batches"

ENTITY_TEMPERATURE_TARGET = "number.communifarm_temperature_target"
ENTITY_HUMIDITY_TARGET = "number.communifarm_humidity_target"
ENTITY_ALLOWLISTED_SWITCH = "switch.communifarm_allowlisted_switch"
ENTITY_LC_STIR_PLATE = "switch.communifarm_lc_stir_plate"
ENTITY_BATCH_STAGE = "sensor.communifarm_batch_stage"
ENTITY_WEIGH_SESSION = "sensor.communifarm_weigh_session"
ENTITY_BATCH_NFC_UID = "sensor.communifarm_batch_nfc_uid"
ENTITY_RECIPE_SCALE = "number.communifarm_recipe_scale"
ENTITY_BATCH_LIST = "sensor.communifarm_batch_list"
ENTITY_BATCH_MILESTONES = "sensor.communifarm_batch_milestones"
ENTITY_CONTAINER_COUNT = "number.communifarm_container_count"
ENTITY_HEAT_TREATMENT = "select.communifarm_heat_treatment"

ENTITY_BTN_WATER_ADDED = "button.communifarm_water_added"
ENTITY_BTN_DRY_WET_MIX = "button.communifarm_dry_wet_mix_started"
ENTITY_BTN_SETTLING = "button.communifarm_settling_started"
ENTITY_BTN_FIELD_CAPACITY = "button.communifarm_field_capacity_reached"
ENTITY_BTN_COMPLETELY_MIXED = "button.communifarm_completely_mixed"
ENTITY_BTN_SEPARATE_CONTAINERS = "button.communifarm_separate_containers"
ENTITY_BTN_HEAT_TREATED = "button.communifarm_heat_treated"
ENTITY_BTN_STORED_COOLING = "button.communifarm_stored_for_cooling"
ENTITY_BTN_PRODUCTION_START = "button.communifarm_production_cycle_started"
ENTITY_BTN_COMPLETE_NEW_BATCH = "button.communifarm_complete_and_new_batch"

SERVICE_TRANSITION_BATCH = "transition_batch"
SERVICE_RECORD_WEIGHT = "record_weight"
SERVICE_RECORD_BATCH_MILESTONE = "record_batch_milestone"
SERVICE_COMPLETE_AND_NEW_BATCH = "complete_and_new_batch"
SERVICE_CREATE_MEDIA_BATCH = "create_media_batch"
SERVICE_RECORD_MEDIA_WEIGHT = "record_media_weight"
SERVICE_RECORD_MEDIA_MILESTONE = "record_media_milestone"
SERVICE_ACQUIRE_CULTURE = "acquire_culture"
SERVICE_INTRODUCE_CULTURE = "introduce_culture"

SIGNAL_WEIGH_SESSION_UPDATED = f"{DOMAIN}_weigh_session_updated"
SIGNAL_BATCH_UPDATED = f"{DOMAIN}_batch_updated"

# Scale entities used when recording from the Weigh station (live or mock).
ENTITY_SCALE_MASS_G = "sensor.esp32dev_calibrated_g"
ENTITY_SCALE_SELECTED_INGREDIENT = "input_select.esp32dev_selected_ingredient"
ENTITY_SCALE_NFC_UID = "input_text.esp32dev_last_nfc_uid"
ENTITY_SCALE_RECORD_BUTTON = "button.esp32dev_record_weight"
ENTITY_SCALE_TARE_BUTTON = "button.esp32dev_tare"
ENTITY_SCALE_LOCATION_TARE_BUTTON = "button.esp32dev_location_tare"

# Default empty weigh-session tracker (mutated at runtime in hass.data).
def new_weigh_session_tracker() -> dict:
    return {
        "tare_seen": False,
        "last_mass_g": None,
        "last_ingredient_key": None,
        "record_count": 0,
        "warnings": [],
        "last_reject": None,
    }

PLATFORMS = ["sensor", "number", "switch", "button", "select"]

BATCH_STAGE_PLANNED = "planned"
BATCH_STAGE_ACTIVE = "active"
BATCH_STAGE_COMPLETE = "complete"

ALLOWED_BATCH_TRANSITIONS = {
    BATCH_STAGE_PLANNED: {BATCH_STAGE_ACTIVE},
    BATCH_STAGE_ACTIVE: {BATCH_STAGE_COMPLETE},
    BATCH_STAGE_COMPLETE: set(),
}

ROLE_TEMPERATURE = "temperature_source"
ROLE_HUMIDITY = "humidity_source"
ROLE_FAN = "fan_actuator"
ROLE_SWITCH = "switch_actuator"
ROLE_LC_STIR_PLATE = "lc_stir_plate"
