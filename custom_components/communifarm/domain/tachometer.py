"""Manual fan tachometer / air-exchange vent measurements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .validation import ValidationError

VENT_ROLE_INTAKE = "intake"
VENT_ROLE_EXHAUST = "exhaust"
VENT_ROLE_CIRCULATION = "circulation"
VENT_ROLE_OTHER = "other"

VENT_ROLES = frozenset(
    {
        VENT_ROLE_INTAKE,
        VENT_ROLE_EXHAUST,
        VENT_ROLE_CIRCULATION,
        VENT_ROLE_OTHER,
    }
)

UNIT_RPM = "rpm"
UNIT_CFM = "cfm"
UNIT_FPM = "fpm"
TACH_UNITS = frozenset({UNIT_RPM, UNIT_CFM, UNIT_FPM})

SOURCE_MANUAL = "manual"


@dataclass(slots=True)
class AirVent:
    """Labeled vent used for air-exchange / tachometer logging."""

    id: str
    site_id: str
    label: str
    vent_role: str
    climate_node_id: str | None = None
    notes: str | None = None
    created_at: str | None = None
    retired_at: str | None = None


@dataclass(slots=True)
class TachometerReading:
    """One timestamped tach / airflow sample for a vent."""

    id: str
    vent_id: str
    site_id: str
    value: float
    unit: str
    recorded_at: str
    source: str = SOURCE_MANUAL
    notes: str | None = None
    created_at: str | None = None
    vent_label: str | None = None


def normalize_vent_label(label: str) -> str:
    cleaned = " ".join(str(label or "").strip().split())
    if not cleaned:
        raise ValidationError("Vent label is required")
    if len(cleaned) > 64:
        raise ValidationError("Vent label must be 64 characters or fewer")
    return cleaned


def validate_vent_role(role: str) -> str:
    cleaned = str(role or "").strip().lower()
    if cleaned not in VENT_ROLES:
        raise ValidationError(
            f"vent_role must be one of: {', '.join(sorted(VENT_ROLES))}"
        )
    return cleaned


def validate_tach_unit(unit: str) -> str:
    cleaned = str(unit or "").strip().lower()
    if cleaned not in TACH_UNITS:
        raise ValidationError(
            f"unit must be one of: {', '.join(sorted(TACH_UNITS))}"
        )
    return cleaned


def validate_tach_value(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise ValidationError("Tachometer value must be a number") from err
    if number < 0:
        raise ValidationError("Tachometer value cannot be negative")
    if number > 1_000_000:
        raise ValidationError("Tachometer value is unrealistically large")
    return number


def reading_to_dict(reading: TachometerReading) -> dict[str, Any]:
    return {
        "id": reading.id,
        "vent_id": reading.vent_id,
        "vent_label": reading.vent_label,
        "site_id": reading.site_id,
        "value": reading.value,
        "unit": reading.unit,
        "recorded_at": reading.recorded_at,
        "source": reading.source,
        "notes": reading.notes,
    }


def vent_to_dict(vent: AirVent) -> dict[str, Any]:
    return {
        "id": vent.id,
        "site_id": vent.site_id,
        "label": vent.label,
        "vent_role": vent.vent_role,
        "climate_node_id": vent.climate_node_id,
        "notes": vent.notes,
        "created_at": vent.created_at,
        "retired_at": vent.retired_at,
    }
