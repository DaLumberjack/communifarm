"""Editable climate settings layered over repository-owned defaults."""

from __future__ import annotations

from dataclasses import dataclass

from .validation import ValidationError

SCOPE_NODE = "node"
SCOPE_ROW = "row"
SETTING_SCOPES = frozenset({SCOPE_NODE, SCOPE_ROW})

SETTING_TEMPERATURE_TARGET = "temperature_target"
SETTING_HUMIDITY_TARGET = "humidity_target"
SETTING_TEMP_DEADBAND = "temp_deadband"
SETTING_HUMIDITY_DEADBAND = "humidity_deadband"
SETTING_CO2_PPM_TARGET = "co2_ppm_target"
SETTING_LIGHT_HOURS_ON = "light_hours_on"
SETTING_LIGHT_HOURS_OFF = "light_hours_off"
SETTING_OCCUPANCY_HOLD_MINUTES = "occupancy_hold_minutes"
SETTING_ROW_FAN_ON_MINUTES = "row_fan_on_minutes"
SETTING_ROW_FAN_OFF_MINUTES = "row_fan_off_minutes"


@dataclass(frozen=True, slots=True)
class ClimateSettingSpec:
    key: str
    scope: str
    name: str
    minimum: float
    maximum: float
    step: float
    unit: str | None = None


NODE_SETTING_SPECS: tuple[ClimateSettingSpec, ...] = (
    ClimateSettingSpec(
        SETTING_TEMPERATURE_TARGET, SCOPE_NODE, "Temperature target", -20, 50, 0.5, "°C"
    ),
    ClimateSettingSpec(
        SETTING_HUMIDITY_TARGET, SCOPE_NODE, "Humidity target", 0, 100, 1, "%"
    ),
    ClimateSettingSpec(
        SETTING_TEMP_DEADBAND, SCOPE_NODE, "Temperature deadband", 0.1, 20, 0.1, "°C"
    ),
    ClimateSettingSpec(
        SETTING_HUMIDITY_DEADBAND, SCOPE_NODE, "Humidity deadband", 0.5, 50, 0.5, "%"
    ),
    ClimateSettingSpec(
        SETTING_CO2_PPM_TARGET, SCOPE_NODE, "CO2 target", 0, 10000, 50, "ppm"
    ),
    ClimateSettingSpec(
        SETTING_LIGHT_HOURS_ON, SCOPE_NODE, "Light hours on", 0, 24, 0.5, "h"
    ),
    ClimateSettingSpec(
        SETTING_LIGHT_HOURS_OFF, SCOPE_NODE, "Light hours off", 0, 24, 0.5, "h"
    ),
    ClimateSettingSpec(
        SETTING_OCCUPANCY_HOLD_MINUTES,
        SCOPE_NODE,
        "Occupancy light hold",
        0,
        120,
        1,
        "min",
    ),
)

ROW_SETTING_SPECS: tuple[ClimateSettingSpec, ...] = (
    ClimateSettingSpec(
        SETTING_ROW_FAN_ON_MINUTES, SCOPE_ROW, "Row fan on time", 1, 120, 1, "min"
    ),
    ClimateSettingSpec(
        SETTING_ROW_FAN_OFF_MINUTES, SCOPE_ROW, "Row fan off time", 1, 120, 1, "min"
    ),
)

SETTING_SPECS = {
    spec.key: spec for spec in (*NODE_SETTING_SPECS, *ROW_SETTING_SPECS)
}


def validate_setting(scope: str, key: str, value: float) -> float:
    """Validate an override independently from storage and HA entities."""
    spec = SETTING_SPECS.get(key)
    if spec is None or spec.scope != scope:
        raise ValidationError(f"unsupported {scope} climate setting: {key}")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValidationError(f"{key} must be finite")
    if not spec.minimum <= number <= spec.maximum:
        raise ValidationError(
            f"{key} must be between {spec.minimum:g} and {spec.maximum:g}"
        )
    return number
