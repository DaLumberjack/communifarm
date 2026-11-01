"""Production placement inventory — bags/boxes by area kind (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .location import (
    AREA_COLD_STORAGE,
    AREA_FRUITING_TENT,
    AREA_INOCULATION_TENT,
    AREA_STORAGE,
)

# Dashboard Production sections (1A) — one markdown sensor each.
PLACEMENT_DASHBOARD_KINDS: tuple[tuple[str, str, str], ...] = (
    (AREA_STORAGE, "Storage", "mdi:warehouse"),
    (AREA_COLD_STORAGE, "Cold storage", "mdi:snowflake"),
    (AREA_FRUITING_TENT, "Fruiting tent", "mdi:tent"),
    (AREA_INOCULATION_TENT, "Inoculation tent", "mdi:greenhouse"),
)


@dataclass(slots=True, frozen=True)
class PlacementContainerRow:
    """One active bag/box shown on a placement inventory card."""

    area_kind: str
    area_name: str
    zone_name: str
    zone_id: str
    batch_id: str
    batch_name: str
    container_index: int
    container_type: str
    lifecycle_phase: str
    nfc_uid: str
    container_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "area_kind": self.area_kind,
            "area_name": self.area_name,
            "zone_name": self.zone_name,
            "zone_id": self.zone_id,
            "batch_id": self.batch_id,
            "batch_name": self.batch_name,
            "container_index": self.container_index,
            "container_type": self.container_type,
            "lifecycle_phase": self.lifecycle_phase,
            "nfc_uid": self.nfc_uid,
            "container_id": self.container_id,
        }


def format_placement_inventory_markdown(
    area_title: str,
    rows: list[PlacementContainerRow],
) -> str:
    """Markdown table for one area section (empty → explicit empty state)."""
    if not rows:
        return f"_No bags/boxes in {area_title}._"
    lines = [
        f"**{len(rows)}** unit(s) in {area_title}",
        "",
        "| Zone | Batch | Unit | Stage | NFC |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        nfc = row.nfc_uid or "—"
        unit = f"{row.container_type} #{row.container_index}"
        lines.append(
            f"| {row.zone_name} | {row.batch_name} | {unit} | "
            f"{row.lifecycle_phase} | `{nfc}` |"
        )
    return "\n".join(lines)


def filter_rows_for_area_kind(
    rows: list[PlacementContainerRow], area_kind: str
) -> list[PlacementContainerRow]:
    return [r for r in rows if r.area_kind == area_kind]
