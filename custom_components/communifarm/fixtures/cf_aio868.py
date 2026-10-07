"""Entity ID contract for cf-lab-aio868 KinCony AIO machine-controller mock."""

from __future__ import annotations

ENTITY_AIO_INTAKE = "switch.cf_lab_aio868_intake"
ENTITY_AIO_EXHAUST = "switch.cf_lab_aio868_exhaust"
ENTITY_AIO_CIRCULATION = "switch.cf_lab_aio868_circulation"
ENTITY_AIO_HUMIDIFIER = "switch.cf_lab_aio868_humidifier"
ENTITY_AIO_HEATER = "switch.cf_lab_aio868_heater"
ENTITY_AIO_PUMP = "switch.cf_lab_aio868_pump"
ENTITY_AIO_VALVE = "switch.cf_lab_aio868_valve"
ENTITY_AIO_FALLBACK = "switch.cf_lab_aio868_fallback_enabled"
ENTITY_AIO_CONTROL_STATE = "sensor.cf_lab_aio868_control_state"
ENTITY_AIO_SAFE_ACTUATION = "binary_sensor.cf_lab_aio868_safe_actuation_allowlist"

CF_AIO868_PUBLIC_ENTITIES: tuple[str, ...] = (
    ENTITY_AIO_INTAKE,
    ENTITY_AIO_EXHAUST,
    ENTITY_AIO_CIRCULATION,
    ENTITY_AIO_HUMIDIFIER,
    ENTITY_AIO_HEATER,
    ENTITY_AIO_PUMP,
    ENTITY_AIO_VALVE,
    ENTITY_AIO_FALLBACK,
    ENTITY_AIO_CONTROL_STATE,
    ENTITY_AIO_SAFE_ACTUATION,
)

CF_AIO868_MACHINE_SWITCHES: tuple[str, ...] = (
    ENTITY_AIO_INTAKE,
    ENTITY_AIO_EXHAUST,
    ENTITY_AIO_CIRCULATION,
    ENTITY_AIO_HUMIDIFIER,
    ENTITY_AIO_HEATER,
    ENTITY_AIO_PUMP,
    ENTITY_AIO_VALVE,
)
