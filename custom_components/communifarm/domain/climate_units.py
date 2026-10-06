"""Authored metric and imperial ranges for gauges.

Control math stays in Celsius. Lovelace gauge min/max are whatever unit Home
Assistant is displaying, so both numbers live here. Update this table in git
and every install picks up the new window the next time the dashboard is
provisioned.
"""

from __future__ import annotations

from dataclasses import dataclass

from .climate import (
    KIND_CULTURE_PREP,
    KIND_FRUITING,
    KIND_GENERAL_ROOM,
    KIND_HARVEST,
    KIND_INCUBATION,
    KIND_INOCULATION,
    KIND_OUTDOOR,
    KIND_READY_TO_SELL,
    ROLE_CO2_PPM,
    ROLE_HUMIDITY,
    ROLE_PRESSURE,
    ROLE_TEMPERATURE,
)

UNIT_METRIC = "metric"
UNIT_US = "us_customary"


@dataclass(frozen=True, slots=True)
class UnitPair:
    """One authored quantity. Not a runtime conversion."""

    metric: float
    imperial: float


def pick(pair: UnitPair, system: str) -> float:
    if system == UNIT_US:
        return pair.imperial
    return pair.metric


def unit_system_for_temperature_symbol(symbol: str) -> str:
    """Map Home Assistant's temperature symbol. Anything else stays metric."""
    if symbol in {"°F", "F"}:
        return UNIT_US
    return UNIT_METRIC


# Operator targets. 22°C is stored as 72°F, matching the growing-conditions note,
# not the unrounded 71.6°F a converter would print.
PRESET_TEMPERATURE: dict[str, UnitPair] = {
    KIND_GENERAL_ROOM: UnitPair(22.0, 72.0),
    KIND_CULTURE_PREP: UnitPair(22.0, 72.0),
    KIND_INOCULATION: UnitPair(22.0, 72.0),
    KIND_INCUBATION: UnitPair(22.0, 72.0),
    KIND_FRUITING: UnitPair(20.0, 68.0),
    KIND_HARVEST: UnitPair(15.0, 59.0),
    KIND_READY_TO_SELL: UnitPair(4.0, 39.0),
}

# Indoor gauges sit close to the target so a small drift moves the needle.
# Outdoor windows are wider; an outdoor grower can still change them later.
INDOOR_TEMP_HALF = UnitPair(4.0, 7.0)
OUTDOOR_TEMP_MIN = UnitPair(-15.0, 5.0)
OUTDOOR_TEMP_MAX = UnitPair(45.0, 113.0)
TEMP_DEADBAND = UnitPair(1.0, 2.0)

INDOOR_HUMIDITY_HALF = 12.0
OUTDOOR_HUMIDITY_MIN = 20.0
OUTDOOR_HUMIDITY_MAX = 100.0
HUMIDITY_DEADBAND = 5.0

CO2_HALF = 400.0
PRESSURE_MIN = UnitPair(980.0, 14.2)
PRESSURE_MAX = UnitPair(1050.0, 15.2)


def authored_fahrenheit(celsius: float) -> float | None:
    """Imperial companion for a shipped Celsius target. Unknown targets have none."""
    for pair in PRESET_TEMPERATURE.values():
        if abs(pair.metric - celsius) < 0.05:
            return pair.imperial
    return None


def gauge_bounds(
    *,
    kind: str,
    role: str,
    temperature_target: float | None,
    humidity_target: float | None,
    co2_ppm_target: float | None,
    system: str,
) -> tuple[float, float, float | None, float] | None:
    """Return min, max, target, deadband in the active unit system.

    The target is the authored imperial number when the Celsius target is one
    we ship. A custom Celsius target with no row here does not invent a °F center.
    """
    outdoor = kind == KIND_OUTDOOR
    if role == ROLE_TEMPERATURE:
        band = pick(TEMP_DEADBAND, system)
        if outdoor:
            return (
                pick(OUTDOOR_TEMP_MIN, system),
                pick(OUTDOOR_TEMP_MAX, system),
                None,
                band,
            )
        center = _temperature_center(kind, temperature_target, system)
        if center is None:
            return None
        half = pick(INDOOR_TEMP_HALF, system)
        return center - half, center + half, center, band
    if role == ROLE_HUMIDITY:
        if outdoor:
            return OUTDOOR_HUMIDITY_MIN, OUTDOOR_HUMIDITY_MAX, humidity_target, HUMIDITY_DEADBAND
        if humidity_target is None:
            return None
        low = max(OUTDOOR_HUMIDITY_MIN, humidity_target - INDOOR_HUMIDITY_HALF)
        high = min(OUTDOOR_HUMIDITY_MAX, humidity_target + INDOOR_HUMIDITY_HALF)
        return low, high, humidity_target, HUMIDITY_DEADBAND
    if role == ROLE_CO2_PPM:
        if co2_ppm_target is None:
            return None
        return (
            max(400.0, co2_ppm_target - CO2_HALF),
            co2_ppm_target + CO2_HALF,
            co2_ppm_target,
            200.0,
        )
    if role == ROLE_PRESSURE and outdoor:
        return (
            pick(PRESSURE_MIN, system),
            pick(PRESSURE_MAX, system),
            None,
            0.0,
        )
    return None


def _temperature_center(kind: str, metric_target: float | None, system: str) -> float | None:
    if metric_target is None:
        preset = PRESET_TEMPERATURE.get(kind)
        if preset is None:
            return None
        return pick(preset, system)
    if system == UNIT_METRIC:
        return float(metric_target)
    authored = authored_fahrenheit(metric_target)
    if authored is not None:
        return authored
    preset = PRESET_TEMPERATURE.get(kind)
    if preset is not None and abs(preset.metric - metric_target) < 0.05:
        return preset.imperial
    return None
