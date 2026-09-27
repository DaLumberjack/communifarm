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

ENTITY_TEMPERATURE_TARGET = "number.communifarm_temperature_target"
ENTITY_HUMIDITY_TARGET = "number.communifarm_humidity_target"
ENTITY_ALLOWLISTED_SWITCH = "switch.communifarm_allowlisted_switch"
ENTITY_BATCH_STAGE = "sensor.communifarm_batch_stage"

PLATFORMS = ["sensor", "number", "switch"]

SERVICE_TRANSITION_BATCH = "transition_batch"

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
