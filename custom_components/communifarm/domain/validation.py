"""Human-usable bounds and sensor-validity assessment (pure domain)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# --- Readability (UI), not storage capacity ---
MAX_NAME_LENGTH = 64
MAX_INGREDIENT_LABEL_LENGTH = 48
MAX_NFC_UID_LENGTH = 64

# --- Weigh station / bench scale ---
MASS_REJECT_BELOW_G = 0.0
BENCH_CAPACITY_G = 100_000.0  # 100 kg — warn, may still store for audit
UNSTABLE_STEP_G = 5_000.0  # sudden jump without tare
STUCK_EPSILON_G = 0.5  # same mass across different ingredients

# --- Recipe ---
ALLOWED_RECIPE_UNITS = frozenset({"g", "qts"})
CLOSE_BAND_PCT = 5.0

# --- Environment sensors (absolute hardware plausibility) ---
TEMP_SENSOR_MIN_C = -40.0
TEMP_SENSOR_MAX_C = 80.0
HUMIDITY_SENSOR_MIN = 0.0
HUMIDITY_SENSOR_MAX = 100.0

# --- Calibration reminder ---
CALIBRATION_REMINDER_EVERY_N = 50

WARNING_OVER_CAPACITY = "over_capacity"
WARNING_UNSTABLE_READING = "unstable_reading"
WARNING_STUCK_READING = "stuck_reading"
WARNING_TARE_SKIPPED = "tare_skipped"
WARNING_MISSING_NFC = "missing_nfc"
WARNING_UNKNOWN_INGREDIENT = "unknown_ingredient"
WARNING_UNKNOWN_UNIT = "unknown_unit"
WARNING_CALIBRATION_DUE = "calibration_due"
WARNING_TEMP_OUT_OF_RANGE = "temperature_out_of_range"
WARNING_HUMIDITY_OUT_OF_RANGE = "humidity_out_of_range"


class ValidationError(ValueError):
    """Hard reject: operator mistake or impossible reading."""


def _is_printable_single_line(value: str) -> bool:
    if not value or value.strip() != value:
        return False
    if any(ord(ch) < 32 for ch in value):
        return False
    return True


def validate_readable_name(value: str, *, field_name: str = "name") -> str:
    """Reject empty / control / over-long names (dashboard readability)."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty readable string")
    if len(value) > MAX_NAME_LENGTH:
        raise ValidationError(
            f"{field_name} must be at most {MAX_NAME_LENGTH} characters"
        )
    if not _is_printable_single_line(value):
        raise ValidationError(
            f"{field_name} must be a single printable line without leading/trailing space"
        )
    return value


def validate_ingredient_label(value: str | None, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValidationError("ingredient is required")
        return None
    if not value.strip():
        raise ValidationError("ingredient must be a non-empty readable string")
    if len(value) > MAX_INGREDIENT_LABEL_LENGTH:
        raise ValidationError(
            f"ingredient must be at most {MAX_INGREDIENT_LABEL_LENGTH} characters"
        )
    if any(ord(ch) < 32 for ch in value):
        raise ValidationError("ingredient must not contain control characters")
    return value


def validate_nfc_uid(value: str | None, *, required: bool = False) -> str | None:
    if value is None or value == "":
        if required:
            raise ValidationError("nfc_uid is required")
        return None
    if len(value) > MAX_NFC_UID_LENGTH:
        raise ValidationError(f"nfc_uid must be at most {MAX_NFC_UID_LENGTH} characters")
    if "\n" in value or "\r" in value or any(ord(ch) < 32 for ch in value):
        raise ValidationError("nfc_uid must be a single-line printable id")
    return value


def validate_recipe_unit(unit: str) -> str:
    if unit not in ALLOWED_RECIPE_UNITS:
        raise ValidationError(
            f"unknown unit {unit!r}; allowed: {sorted(ALLOWED_RECIPE_UNITS)}"
        )
    return unit


@dataclass(slots=True)
class MassAssessment:
    """Result of assessing a weigh-station mass reading."""

    mass_g: float
    accepted: bool
    reject_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


def assess_mass_g(
    mass_g: float,
    *,
    previous_mass_g: float | None = None,
    previous_ingredient_key: str | None = None,
    ingredient_key: str | None = None,
    tare_seen: bool = False,
    record_count_before: int = 0,
    capacity_g: float = BENCH_CAPACITY_G,
    unstable_step_g: float = UNSTABLE_STEP_G,
) -> MassAssessment:
    """Reject impossible mass; accept suspicious mass with warnings."""
    if not isinstance(mass_g, (int, float)) or isinstance(mass_g, bool):
        return MassAssessment(
            mass_g=float("nan"),
            accepted=False,
            reject_reason="mass_g must be a number",
        )
    value = float(mass_g)
    if math.isnan(value) or math.isinf(value):
        return MassAssessment(
            mass_g=value,
            accepted=False,
            reject_reason="mass_g must be a finite number",
        )
    if value < MASS_REJECT_BELOW_G:
        return MassAssessment(
            mass_g=value,
            accepted=False,
            reject_reason="mass_g must not be negative (check tare / calibration)",
        )

    warnings: list[str] = []
    if value > capacity_g:
        warnings.append(WARNING_OVER_CAPACITY)
    if (
        previous_mass_g is not None
        and not tare_seen
        and abs(value - previous_mass_g) > unstable_step_g
    ):
        warnings.append(WARNING_UNSTABLE_READING)
    if (
        previous_mass_g is not None
        and previous_ingredient_key
        and ingredient_key
        and previous_ingredient_key != ingredient_key
        and abs(value - previous_mass_g) <= STUCK_EPSILON_G
    ):
        warnings.append(WARNING_STUCK_READING)
    if record_count_before == 0 and not tare_seen:
        warnings.append(WARNING_TARE_SKIPPED)
    if (record_count_before + 1) % CALIBRATION_REMINDER_EVERY_N == 0:
        warnings.append(WARNING_CALIBRATION_DUE)

    return MassAssessment(mass_g=value, accepted=True, warnings=warnings)


@dataclass(slots=True)
class EnvironmentReadingAssessment:
    """Absolute-range check for bound temp/humidity sensors."""

    ok: bool
    warnings: list[str] = field(default_factory=list)
    temperature_c: float | None = None
    humidity_pct: float | None = None


def assess_environment_readings(
    temperature_c: float | None,
    humidity_pct: float | None,
) -> EnvironmentReadingAssessment:
    warnings: list[str] = []
    if temperature_c is not None:
        if math.isnan(temperature_c) or math.isinf(temperature_c):
            warnings.append(WARNING_TEMP_OUT_OF_RANGE)
        elif not (TEMP_SENSOR_MIN_C <= temperature_c <= TEMP_SENSOR_MAX_C):
            warnings.append(WARNING_TEMP_OUT_OF_RANGE)
    if humidity_pct is not None:
        if math.isnan(humidity_pct) or math.isinf(humidity_pct):
            warnings.append(WARNING_HUMIDITY_OUT_OF_RANGE)
        elif not (HUMIDITY_SENSOR_MIN <= humidity_pct <= HUMIDITY_SENSOR_MAX):
            warnings.append(WARNING_HUMIDITY_OUT_OF_RANGE)
    return EnvironmentReadingAssessment(
        ok=not warnings,
        warnings=warnings,
        temperature_c=temperature_c,
        humidity_pct=humidity_pct,
    )
