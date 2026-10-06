"""Placement areas and zones (pure domain — data-driven area kinds)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import new_id
from .production import (
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INCUBATING,
    STAGE_INOCULATED,
)
from .validation import ValidationError

SLOT_LEVEL = "level"
SLOT_SHELF = "shelf"
SLOT_KINDS = frozenset({SLOT_LEVEL, SLOT_SHELF})

AREA_FRUITING_TENT = "fruiting_tent"
AREA_INOCULATION_TENT = "inoculation_tent"
AREA_CULTURE_FRIDGE = "culture_fridge"
AREA_STILL_AIR_CABINET = "still_air_cabinet"
AREA_HARVEST_FRIDGE = "harvest_fridge"

AREA_KINDS = frozenset(
    {
        AREA_FRUITING_TENT,
        AREA_INOCULATION_TENT,
        AREA_CULTURE_FRIDGE,
        AREA_STILL_AIR_CABINET,
        AREA_HARVEST_FRIDGE,
    }
)

# Soft suggestions only — MVP does not hard-reject mismatched area_kind.
STAGE_SUGGESTED_AREA_KIND: dict[str, str] = {
    STAGE_INOCULATED: AREA_INOCULATION_TENT,
    STAGE_INCUBATING: AREA_INOCULATION_TENT,
    STAGE_FRUITING: AREA_FRUITING_TENT,
    STAGE_HARVESTING: AREA_FRUITING_TENT,
}

# Culture lot storage (agar / LC / spores) → culture fridge.
CULTURE_FORM_SUGGESTED_AREA_KIND: dict[str, str] = {
    "agar": AREA_CULTURE_FRIDGE,
    "liquid_culture": AREA_CULTURE_FRIDGE,
    "spores": AREA_CULTURE_FRIDGE,
    "grain_spawn": AREA_CULTURE_FRIDGE,
}

# Media prep / cooling in SAB; ready / in-use storage in culture fridge.
MEDIA_STATUS_SUGGESTED_AREA_KIND: dict[str, str] = {
    "planned": AREA_STILL_AIR_CABINET,
    "weighing": AREA_STILL_AIR_CABINET,
    "sterilizing": AREA_STILL_AIR_CABINET,
    "media_ready": AREA_CULTURE_FRIDGE,
    "in_use": AREA_CULTURE_FRIDGE,
}

# SAB work notes (transfers, plating) — soft hint only.
SAB_WORK_SUGGESTED_AREA_KIND = AREA_STILL_AIR_CABINET

# (name, area_kind, slot_kind, slot_count)
DEFAULT_LAYOUT: tuple[tuple[str, str, str, int], ...] = (
    ("Fruiting tent", AREA_FRUITING_TENT, SLOT_LEVEL, 5),
    ("Inoculation tent", AREA_INOCULATION_TENT, SLOT_LEVEL, 5),
    ("Culture fridge", AREA_CULTURE_FRIDGE, SLOT_SHELF, 5),
    ("Still air cabinet", AREA_STILL_AIR_CABINET, SLOT_SHELF, 3),
    ("Harvest fridge", AREA_HARVEST_FRIDGE, SLOT_SHELF, 6),
)


@dataclass(slots=True)
class PlacementArea:
    """Physical placement area (tent / fridge / cabinet) under a site."""

    site_id: str
    name: str
    area_kind: str
    slot_kind: str
    slot_count: int
    id: str = ""
    created_at: str | None = None
    notes: str | None = None
    climate_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("area")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Zone:
    """Level or shelf slot inside a placement area."""

    area_id: str
    site_id: str
    name: str
    slot_kind: str
    slot_index: int
    id: str = ""
    created_at: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("zone")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LocationLayout:
    """Default seeded areas + zones for a site."""

    areas: list[PlacementArea] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "areas": [a.to_dict() for a in self.areas],
            "zones": [z.to_dict() for z in self.zones],
        }


def validate_zone_index(slot_index: int, slot_count: int) -> int:
    """1-based slot index in [1, slot_count]."""
    try:
        idx = int(slot_index)
    except (TypeError, ValueError) as err:
        raise ValidationError("slot_index must be an integer") from err
    if idx < 1 or idx > slot_count:
        raise ValidationError(
            f"slot_index must be between 1 and {slot_count} (got {idx})"
        )
    return idx


def suggest_area_kind_for_production_stage(stage: str) -> str | None:
    """Soft mapping from production stage → suggested area_kind (or None)."""
    return STAGE_SUGGESTED_AREA_KIND.get(stage)


def suggest_area_kind_for_culture_form(form: str) -> str | None:
    """Soft mapping from culture form → suggested storage area_kind (or None)."""
    return CULTURE_FORM_SUGGESTED_AREA_KIND.get(form)


def suggest_area_kind_for_media_status(status: str) -> str | None:
    """Soft mapping from media status → suggested area_kind (or None)."""
    return MEDIA_STATUS_SUGGESTED_AREA_KIND.get(status)


def zone_display_name(slot_kind: str, slot_index: int) -> str:
    label = "Level" if slot_kind == SLOT_LEVEL else "Shelf"
    return f"{label} {slot_index}"


def build_default_layout(site_id: str) -> LocationLayout:
    """Build PlacementArea + Zone objects for the default site layout (not persisted)."""
    if not site_id or not str(site_id).strip():
        raise ValidationError("site_id is required")
    site = str(site_id).strip()
    areas: list[PlacementArea] = []
    zones: list[Zone] = []
    for name, area_kind, slot_kind, slot_count in DEFAULT_LAYOUT:
        if area_kind not in AREA_KINDS:
            raise ValidationError(f"unknown area_kind in DEFAULT_LAYOUT: {area_kind}")
        if slot_kind not in SLOT_KINDS:
            raise ValidationError(f"unknown slot_kind in DEFAULT_LAYOUT: {slot_kind}")
        if slot_count < 1:
            raise ValidationError(f"slot_count must be >= 1 for {name}")
        area = PlacementArea(
            site_id=site,
            name=name,
            area_kind=area_kind,
            slot_kind=slot_kind,
            slot_count=slot_count,
        )
        areas.append(area)
        for idx in range(1, slot_count + 1):
            zones.append(
                Zone(
                    area_id=area.id,
                    site_id=site,
                    name=zone_display_name(slot_kind, idx),
                    slot_kind=slot_kind,
                    slot_index=idx,
                )
            )
    return LocationLayout(areas=areas, zones=zones)
