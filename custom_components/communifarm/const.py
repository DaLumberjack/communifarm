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
DASHBOARD_VIEW_MIX = "mix"
DASHBOARD_VIEW_NFC_WRITE = "intake"  # Intake (was nfc-write)
DASHBOARD_VIEW_INTAKE = DASHBOARD_VIEW_NFC_WRITE
DASHBOARD_VIEW_BATCHES = "batches"
DASHBOARD_VIEW_CULTURE = "culture"
DASHBOARD_VIEW_PRODUCTION = "production"
DASHBOARD_VIEW_HARVEST = "harvest"
DASHBOARD_VIEW_POS = "pos"
DASHBOARD_VIEW_CLIMATE_LAYOUT = "climate-layout"
DASHBOARD_VIEW_CLIMATE_STATUS = "climate-status"
CLIMATE_LAYOUT_IMAGE = "/local/communifarm/cea-layout.png"

ENTITY_TEMPERATURE_TARGET = "number.communifarm_temperature_target"
ENTITY_HUMIDITY_TARGET = "number.communifarm_humidity_target"
ENTITY_ALLOWLISTED_SWITCH = "switch.communifarm_allowlisted_switch"
ENTITY_LC_STIR_PLATE = "switch.communifarm_lc_stir_plate"
ENTITY_BATCH_STAGE = "sensor.communifarm_batch_stage"
ENTITY_WEIGH_SESSION = "sensor.communifarm_weigh_session"
ENTITY_MIX_PROTOCOL = "sensor.communifarm_mix_protocol"
ENTITY_NFC_WRITE_STATUS = "sensor.communifarm_nfc_write_status"
ENTITY_FIELD_CAPACITY = "sensor.communifarm_field_capacity"
ENTITY_BATCH_NFC_UID = "sensor.communifarm_batch_nfc_uid"
ENTITY_RECIPE_SCALE = "number.communifarm_recipe_scale"
ENTITY_MANUAL_WEIGH_G = "number.communifarm_manual_weigh_g"
# Sentinel on ENTITY_MANUAL_WEIGH_G: omit from record_weight / use live scale.
MANUAL_WEIGH_OMIT_G = -1.0
ENTITY_BATCH_LIST = "sensor.communifarm_batch_list"
# Dashboard Batch list widget: newest first, capped (state-filtered widgets later).
BATCH_LIST_WIDGET_LIMIT = 10
ENTITY_BATCH_MILESTONES = "sensor.communifarm_batch_milestones"
ENTITY_CONTAINER_COUNT = "number.communifarm_container_count"
ENTITY_HEAT_TREATMENT = "select.communifarm_heat_treatment"
ENTITY_PRODUCTION_STATUS = "sensor.communifarm_production_status"
ENTITY_PLACEMENT_STORAGE = "sensor.communifarm_placement_storage"
ENTITY_PLACEMENT_COLD_STORAGE = "sensor.communifarm_placement_cold_storage"
ENTITY_PLACEMENT_FRUITING_TENT = "sensor.communifarm_placement_fruiting_tent"
ENTITY_PLACEMENT_INOCULATION_TENT = "sensor.communifarm_placement_inoculation_tent"
ENTITY_CONTAINER_TYPE = "select.communifarm_container_type"
ENTITY_ACTIVE_INOCULUM = "select.communifarm_active_inoculum"
ENTITY_ACTIVE_CULTURE_ID = "sensor.communifarm_active_culture_id"
ENTITY_VARIETY_LIST = "sensor.communifarm_variety_list"
ENTITY_CULTURE_INVENTORY = "sensor.communifarm_culture_inventory"
ENTITY_VARIETY_NAME = "text.communifarm_variety_name"
ENTITY_CATALOG_VARIETY = "select.communifarm_catalog_variety"
ENTITY_ACQUIRE_FORM = "select.communifarm_acquire_form"
ENTITY_ACQUIRE_SOURCE = "select.communifarm_acquire_source"
ENTITY_CULTURE_VESSEL_STATUS = "select.communifarm_culture_vessel_status"
ENTITY_BTN_CREATE_VARIETY = "button.communifarm_create_variety"
ENTITY_BTN_RETIRE_VARIETY = "button.communifarm_retire_variety"
ENTITY_BTN_ACQUIRE_CULTURE = "button.communifarm_acquire_culture"
ENTITY_BTN_SET_CULTURE_STATUS = "button.communifarm_set_culture_status"
ENTITY_SUBSTRATE_G = "number.communifarm_substrate_g_per_container"
ENTITY_HARVEST_MASS_G = "number.communifarm_harvest_mass_g"
ENTITY_NFC_CHECKIN = "sensor.communifarm_nfc_checkin"
ENTITY_SALES_STATUS = "sensor.communifarm_sales_status"
ENTITY_SALE_MASS_G = "number.communifarm_sale_mass_g"
ENTITY_SALE_LINE_AMOUNT = "number.communifarm_sale_line_amount"
ENTITY_PAYMENT_METHOD = "select.communifarm_payment_method"
ENTITY_SALE_VENUE = "select.communifarm_sale_venue"
ENTITY_SALE_BUYER = "select.communifarm_sale_buyer"
ENTITY_CLIMATE_STATUS = "sensor.communifarm_climate_status"
ENTITY_OPS_QUEUE = "sensor.communifarm_ops_queue"
ENTITY_TACHOMETER_STATUS = "sensor.communifarm_tachometer_status"

ENTITY_BTN_DRYS_COMBINED = "button.communifarm_drys_combined"
ENTITY_BTN_WATER_ADDED = "button.communifarm_water_added"
ENTITY_BTN_DRY_WET_MIX = "button.communifarm_dry_wet_mix_started"
ENTITY_BTN_REMAINING_WATER = "button.communifarm_remaining_water_added"
ENTITY_BTN_SETTLING = "button.communifarm_settling_started"
ENTITY_BTN_FIELD_CAPACITY = "button.communifarm_field_capacity_reached"
ENTITY_BTN_RELOCATE_STERILE = "button.communifarm_relocate_for_sterilization"
ENTITY_BTN_CREATE_INVENTORY_LOT = "button.communifarm_create_inventory_lot"
ENTITY_BTN_PREPARE_NFC_WRITE = "button.communifarm_prepare_nfc_write"
ENTITY_BTN_CONFIRM_NFC_WRITE = "button.communifarm_confirm_nfc_write"
ENTITY_BTN_MIX_STEP_FROM_BADGE = "button.communifarm_mix_step_from_badge"
ENTITY_BTN_APPLY_TAG_SOURCE = "button.communifarm_apply_tag_source_scan"
ENTITY_BTN_RECORD_WATER_POUR = "button.communifarm_record_water_pour"
ENTITY_BTN_REGISTER_PRODUCTION_BLOCK = "button.communifarm_register_production_block"
ENTITY_BTN_SEED_SHIPMENT_TAGS = "button.communifarm_seed_shipment_nfc_tags"
ENTITY_BTN_IMPORT_NFC_FROM_ENTITY = "button.communifarm_import_nfc_from_entity"
ENTITY_INTAKE_TAG_UID = "select.communifarm_intake_tag_uid"
ENTITY_NFC_WRITE_OBJECT_TYPE = "select.communifarm_nfc_write_object_type"
ENTITY_NFC_WRITE_LABEL = "select.communifarm_nfc_write_label"
ENTITY_NFC_SCAN_MODE = "select.communifarm_nfc_scan_mode"
ENTITY_INTAKE_PROCESS_MODE = "select.communifarm_intake_process_mode"
ENTITY_INTAKE_ZONE = "select.communifarm_intake_zone"
ENTITY_RELOCATE_ZONE = "select.communifarm_relocate_zone"
ENTITY_INTAKE_AMOUNT = "number.communifarm_intake_amount"
ENTITY_INTAKE_COST = "number.communifarm_intake_cost"
ENTITY_INTAKE_AMOUNT_UNIT = "select.communifarm_intake_amount_unit"
ENTITY_INTAKE_PAYMENT = "select.communifarm_intake_payment_location"
ENTITY_INTAKE_TRACKED = "select.communifarm_intake_tracked"
ENTITY_INTAKE_RECEIPT = "select.communifarm_intake_receipt_tracked"
ENTITY_INTAKE_PURCHASE_LOCATION = "text.communifarm_intake_purchase_location"
ENTITY_INTAKE_PURCHASE_DATE = "text.communifarm_intake_purchase_date"
ENTITY_INTAKE_MACHINE_LABEL = "text.communifarm_intake_machine_label"
ENTITY_INTAKE_EMPLOYEE_LABEL = "text.communifarm_intake_employee_label"
ENTITY_BTN_COMPLETELY_MIXED = "button.communifarm_completely_mixed"
ENTITY_BTN_SEPARATE_CONTAINERS = "button.communifarm_separate_containers"
ENTITY_BTN_HEAT_TREATED = "button.communifarm_heat_treated"
ENTITY_BTN_STORED_COOLING = "button.communifarm_stored_for_cooling"
ENTITY_BTN_PRODUCTION_START = "button.communifarm_production_cycle_started"
ENTITY_BTN_COMPLETE_NEW_BATCH = "button.communifarm_complete_and_new_batch"
ENTITY_BTN_INOCULATE = "button.communifarm_inoculate_batch"
ENTITY_BTN_SELECT_INOCULUM_NFC = "button.communifarm_select_inoculum_from_nfc"
ENTITY_BTN_MOVE_INCUBATION = "button.communifarm_move_to_incubation"
ENTITY_BTN_MOVE_FRUITING = "button.communifarm_move_to_fruiting"
ENTITY_BTN_MOVE_HARVEST = "button.communifarm_move_to_harvest"
ENTITY_BTN_RECORD_HARVEST = "button.communifarm_record_harvest"
ENTITY_BTN_FINAL_HARVEST = "button.communifarm_final_harvest"
ENTITY_BTN_NFC_CHECKIN_HARVEST = "button.communifarm_nfc_checkin_harvest"
ENTITY_BTN_CONFIRM_CONTAINER_HARVEST = "button.communifarm_confirm_container_harvest"
ENTITY_BTN_CONFIRM_FINAL_CONTAINER_HARVEST = (
    "button.communifarm_confirm_final_container_harvest"
)
ENTITY_BTN_RECORD_SALE = "button.communifarm_record_sale"
ENTITY_BTN_RECORD_SALE_CLEANUP = "button.communifarm_record_sale_cleanup"

SERVICE_TRANSITION_BATCH = "transition_batch"
SERVICE_RECORD_WEIGHT = "record_weight"
SERVICE_RECORD_BATCH_MILESTONE = "record_batch_milestone"
SERVICE_COMPLETE_AND_NEW_BATCH = "complete_and_new_batch"
SERVICE_CREATE_MEDIA_BATCH = "create_media_batch"
SERVICE_RECORD_MEDIA_WEIGHT = "record_media_weight"
SERVICE_RECORD_MEDIA_MILESTONE = "record_media_milestone"
SERVICE_ACQUIRE_CULTURE = "acquire_culture"
SERVICE_CREATE_VARIETY = "create_variety"
SERVICE_RETIRE_VARIETY = "retire_variety"
SERVICE_SET_CULTURE_STATUS = "set_culture_status"
SERVICE_INTRODUCE_CULTURE = "introduce_culture"
SERVICE_INOCULATE_BATCH = "inoculate_batch"
SERVICE_ADVANCE_PRODUCTION_STAGE = "advance_production_stage"
SERVICE_RECORD_HARVEST = "record_harvest"
SERVICE_ADD_BATCH_NOTE = "add_batch_note"
SERVICE_SET_CHECK_REMINDER = "set_check_reminder"
SERVICE_ENSURE_PLACEMENT_LAYOUT = "ensure_placement_layout"
SERVICE_ENSURE_CLIMATE_LAYOUT = "ensure_climate_layout"
SERVICE_TICK_CLIMATE = "tick_climate"
SERVICE_BIND_CLIMATE_ROLE = "bind_climate_role"
SERVICE_SET_BATCH_LOCATION = "set_batch_location"
SERVICE_SET_CULTURE_LOCATION = "set_culture_location"
SERVICE_SET_MEDIA_LOCATION = "set_media_location"
SERVICE_RESOLVE_NFC = "resolve_nfc"
SERVICE_CHECK_IN = "check_in"
SERVICE_BIND_NFC = "bind_nfc"
SERVICE_CREATE_INVENTORY_LOT = "create_inventory_lot"
SERVICE_CREATE_EMPLOYEE_BADGE = "create_employee_badge"
SERVICE_PREPARE_NFC_WRITE = "prepare_nfc_write"
SERVICE_CONFIRM_NFC_WRITE = "confirm_nfc_write"
SERVICE_COMPLETE_MIX_STEP_FROM_BADGE = "complete_mix_step_from_badge"
SERVICE_APPLY_TAG_SOURCE_SCAN = "apply_tag_source_scan"
SERVICE_RELOCATE_FOR_STERILIZATION = "relocate_for_sterilization"
SERVICE_SEED_SHIPMENT_NFC_TAGS = "seed_shipment_nfc_tags"
SERVICE_IMPORT_NFC_FROM_ENTITY = "import_nfc_from_entity"
SERVICE_RECORD_CONTAINER_HARVEST = "record_container_harvest"
SERVICE_RECORD_SALE = "record_sale"
SERVICE_RECORD_SALE_CLEANUP = "record_sale_cleanup"
SERVICE_UPSERT_AIR_VENT = "upsert_air_vent"
SERVICE_RECORD_TACHOMETER = "record_tachometer"

SIGNAL_WEIGH_SESSION_UPDATED = f"{DOMAIN}_weigh_session_updated"
SIGNAL_BATCH_UPDATED = f"{DOMAIN}_batch_updated"
SIGNAL_NFC_CHECKIN_UPDATED = f"{DOMAIN}_nfc_checkin_updated"
SIGNAL_SALES_UPDATED = f"{DOMAIN}_sales_updated"
SIGNAL_CULTURE_UPDATED = f"{DOMAIN}_culture_updated"
SIGNAL_CLIMATE_UPDATED = f"{DOMAIN}_climate_updated"
SIGNAL_OPS_UPDATED = f"{DOMAIN}_ops_updated"
SIGNAL_TACHOMETER_UPDATED = f"{DOMAIN}_tachometer_updated"

CLIMATE_TICK_SECONDS = 60

# Scale entities used when recording from the Weigh station (live or mock).
ENTITY_SCALE_MASS_G = "sensor.esp32dev_calibrated_g"
ENTITY_SCALE_SELECTED_INGREDIENT = "input_select.esp32dev_selected_ingredient"
ENTITY_SCALE_NFC_UID = "input_text.esp32dev_last_nfc_uid"
ENTITY_SCALE_RECORD_BUTTON = "button.esp32dev_record_weight"
ENTITY_SCALE_TARE_BUTTON = "button.esp32dev_tare"
ENTITY_SCALE_LOCATION_TARE_BUTTON = "button.esp32dev_location_tare"

# Mix-room field-capacity / moisture capacitance mock (salts skew — calibrate).
ENTITY_FIELD_CAPACITY_RAW = "sensor.cf_mixroom_field_capacity_pct"
FIELD_CAPACITY_MIN_OK = 40.0
FIELD_CAPACITY_MAX_OK = 70.0
# Reject water pours that would push the batch sum past target × this factor.
WATER_OVERADD_FACTOR = 1.05

# Default empty weigh-session tracker (mutated at runtime in hass.data).
def new_weigh_session_tracker() -> dict:
    return {
        "tare_seen": False,
        "last_mass_g": None,
        "last_ingredient_key": None,
        "record_count": 0,
        "warnings": [],
        "last_reject": None,
        "last_mass_source": None,
    }

PLATFORMS = ["sensor", "number", "switch", "button", "select", "text", "binary_sensor"]

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
