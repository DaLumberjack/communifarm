"""Fixed operator floor plan for picture-elements overlays.

Coordinates are a schematic of one site, not a scale drawing. A later editor
can replace `_ROOMS` and the anchor tables. Lovelace percentages are derived
from the same numbers the SVG uses, so the dots stay on the rooms.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from .climate import (
    KIND_CULTURE_PREP,
    KIND_FRUITING,
    KIND_GENERAL_ROOM,
    KIND_HARVEST,
    KIND_INCUBATION,
    KIND_INOCULATION,
    KIND_OUTDOOR,
    KIND_READY_TO_SELL,
    KIND_STORAGE,
    KIND_STORAGE_CONSUMABLES,
    KIND_STORAGE_HARD_GOODS,
    ROLE_AC,
    ROLE_CIRCULATION_FAN,
    ROLE_CO2_PPM,
    ROLE_CONDENSATE_PUMP,
    ROLE_DEHUMIDIFIER,
    ROLE_EXHAUST_FAN,
    ROLE_FLOAT,
    ROLE_FRESH_AIR_INTAKE,
    ROLE_HEATER,
    ROLE_HUMIDIFIER,
    ROLE_HUMIDITY,
    ROLE_INTAKE_FAN,
    ROLE_LIGHT,
    ROLE_PRESSURE,
    ROLE_TEMPERATURE,
    ClimateBinding,
    ClimateNode,
)

VIEW_W = 120.0
VIEW_H = 78.0

SENSOR_ROLES = frozenset(
    {ROLE_TEMPERATURE, ROLE_HUMIDITY, ROLE_PRESSURE, ROLE_CO2_PPM, ROLE_FLOAT}
)
ACTUATOR_ROLES = frozenset(
    {
        ROLE_CIRCULATION_FAN,
        ROLE_INTAKE_FAN,
        ROLE_EXHAUST_FAN,
        ROLE_FRESH_AIR_INTAKE,
        ROLE_AC,
        ROLE_HEATER,
        ROLE_HUMIDIFIER,
        ROLE_DEHUMIDIFIER,
        ROLE_LIGHT,
        ROLE_CONDENSATE_PUMP,
    }
)

ROLE_LABEL = {
    ROLE_TEMPERATURE: "T",
    ROLE_HUMIDITY: "RH",
    ROLE_PRESSURE: "P",
    ROLE_CO2_PPM: "CO2",
    ROLE_FLOAT: "Float",
    ROLE_CIRCULATION_FAN: "Circ",
    ROLE_INTAKE_FAN: "In",
    ROLE_EXHAUST_FAN: "Ex",
    ROLE_FRESH_AIR_INTAKE: "Fresh",
    ROLE_AC: "AC",
    ROLE_HEATER: "Heat",
    ROLE_HUMIDIFIER: "Hum",
    ROLE_DEHUMIDIFIER: "Dehum",
    ROLE_LIGHT: "Light",
    ROLE_CONDENSATE_PUMP: "Pump",
}


@dataclass(frozen=True, slots=True)
class RoomFrame:
    kind: str
    title: str
    x: float
    y: float
    w: float
    h: float
    fill: str


@dataclass(frozen=True, slots=True)
class OverlayPoint:
    """One bound entity placed on the schematic."""

    kind: str
    node_name: str
    role: str
    entity_id: str
    slot: int
    left: str
    top: str
    temperature_target: float | None
    humidity_target: float | None
    co2_ppm_target: float | None
    temp_deadband: float
    humidity_deadband: float

    @property
    def is_sensor(self) -> bool:
        return self.role in SENSOR_ROLES


# Operator preset geometry. Edit this table when the floor plan changes.
_ROOMS: tuple[RoomFrame, ...] = (
    RoomFrame(KIND_OUTDOOR, "Outdoors", 2, 1, 116, 8, "#5d7f9a"),
    RoomFrame(KIND_GENERAL_ROOM, "General room", 2, 11, 116, 65, "#4e5c56"),
    RoomFrame(KIND_CULTURE_PREP, "Culture prep", 20, 16, 22, 26, "#2f6f4e"),
    RoomFrame(KIND_INOCULATION, "Inoculation", 44, 16, 22, 26, "#2f6f4e"),
    RoomFrame(KIND_INCUBATION, "Incubation", 68, 16, 22, 26, "#2f6f4e"),
    RoomFrame(KIND_FRUITING, "Fruiting", 92, 16, 24, 26, "#3d8f55"),
    RoomFrame(KIND_HARVEST, "Harvest", 20, 46, 18, 16, "#6b5b4a"),
    RoomFrame(KIND_READY_TO_SELL, "Ready to sell", 40, 46, 18, 16, "#6b5b4a"),
    RoomFrame(KIND_STORAGE_HARD_GOODS, "Hard goods", 60, 46, 18, 16, "#5a5348"),
    RoomFrame(KIND_STORAGE_CONSUMABLES, "Consumables", 80, 46, 16, 16, "#5a5348"),
    RoomFrame(KIND_STORAGE, "Storage", 98, 46, 18, 16, "#5a5348"),
)

_ROOM_BY_KIND = {room.kind: room for room in _ROOMS}


def room_frames() -> tuple[RoomFrame, ...]:
    return _ROOMS


def percent_left(x: float) -> str:
    return f"{x / VIEW_W * 100:.1f}%"


def percent_top(y: float) -> str:
    return f"{y / VIEW_H * 100:.1f}%"


def sensor_xy(kind: str, slot: int, *, humidity: bool = False) -> tuple[float, float] | None:
    """Up to five sensor dots inside a room. Slot 0 is the center."""
    room = _ROOM_BY_KIND.get(kind)
    if room is None or kind in {KIND_OUTDOOR, KIND_GENERAL_ROOM}:
        return None
    extras = max(0, slot - 4)
    slot = min(slot, 4)
    cx = room.x + room.w * 0.5
    cy = room.y + room.h * 0.42
    offsets = (
        (0.0, 0.0),
        (-0.22, -0.18),
        (0.22, -0.18),
        (-0.22, 0.16),
        (0.22, 0.16),
    )
    dx, dy = offsets[slot]
    # Wider than the old 0.22 grid so a desktop state-label fits between dots.
    x = cx + dx * room.w * 1.35 + extras * 1.2
    y = cy + dy * room.h + (3.2 if humidity else 0.0)
    return x, y


def machine_xy(kind: str, role: str) -> tuple[float, float] | None:
    """Fixed machine marks for the operator preset."""
    if kind == KIND_GENERAL_ROOM:
        column = {
            ROLE_AC: 0,
            ROLE_HEATER: 1,
            ROLE_FRESH_AIR_INTAKE: 2,
            ROLE_FLOAT: 3,
            ROLE_CONDENSATE_PUMP: 4,
        }
        index = column.get(role)
        if index is None:
            return None
        return 8.0, 18.0 + index * 8.0
    if kind == KIND_OUTDOOR:
        spots = {
            ROLE_TEMPERATURE: 18.0,
            ROLE_HUMIDITY: 36.0,
            ROLE_PRESSURE: 54.0,
        }
        x = spots.get(role)
        if x is None:
            return None
        return x, 5.0
    room = _ROOM_BY_KIND.get(kind)
    if room is None:
        return None
    along = {
        ROLE_CIRCULATION_FAN: 0.22,
        ROLE_INTAKE_FAN: 0.42,
        ROLE_EXHAUST_FAN: 0.62,
        ROLE_FRESH_AIR_INTAKE: 0.22,
        ROLE_HUMIDIFIER: 0.78,
        ROLE_DEHUMIDIFIER: 0.78,
        ROLE_LIGHT: 0.5,
        ROLE_CO2_PPM: 0.5,
    }
    frac = along.get(role)
    if frac is None:
        return None
    y = room.y + room.h * (0.22 if role in {ROLE_LIGHT, ROLE_CO2_PPM} else 0.82)
    if role == ROLE_DEHUMIDIFIER:
        y = room.y + room.h * 0.68
    return room.x + room.w * frac, y


def overlay_prefix(point: OverlayPoint) -> str:
    """Short mark for a picture-elements label. The room name is already inked.

    Tent probes show the reading only. A ``T2`` prefix plus the unit was wider
    than the gap between dots.
    """
    if point.role in {ROLE_TEMPERATURE, ROLE_HUMIDITY} and point.kind not in {
        KIND_OUTDOOR,
        KIND_GENERAL_ROOM,
    }:
        return ""
    label = ROLE_LABEL.get(point.role, point.role)
    return f"{label} "


def overlay_points(
    nodes: list[ClimateNode], bindings: list[ClimateBinding]
) -> list[OverlayPoint]:
    """Place bound entities on the preset. Unbound roles produce no overlay.

    Numbered probes sort by entity id so temperature_1 stays on the center dot
    even when the database returns bindings in id order.
    """
    by_id = {node.id: node for node in nodes}
    counts: dict[tuple[str, str], int] = {}
    points: list[OverlayPoint] = []
    ordered = sorted(
        bindings,
        key=lambda binding: (binding.node_id, binding.role, binding.entity_id or ""),
    )
    for binding in ordered:
        if not binding.entity_id:
            continue
        node = by_id.get(binding.node_id)
        if node is None:
            continue
        key = (node.kind, binding.role)
        slot = counts.get(key, 0)
        counts[key] = slot + 1
        xy = _xy_for(node.kind, binding.role, slot)
        if xy is None:
            continue
        x, y = xy
        points.append(
            OverlayPoint(
                kind=node.kind,
                node_name=node.name,
                role=binding.role,
                entity_id=binding.entity_id,
                slot=slot,
                left=percent_left(x),
                top=percent_top(y),
                temperature_target=node.temperature_target,
                humidity_target=node.humidity_target,
                co2_ppm_target=node.co2_ppm_target,
                temp_deadband=node.temp_deadband,
                humidity_deadband=node.humidity_deadband,
            )
        )
    return points


def render_operator_layout_svg() -> str:
    """PLC-style schematic. Room ink only — live values are Lovelace overlays."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W:g} {VIEW_H:g}" '
            'width="1200" height="780">'
        ),
        '<rect width="100%" height="100%" fill="#3a3f44"/>',
        (
            '<text x="78" y="5.6" fill="#e7f2f8" font-size="2.4" '
            'font-family="sans-serif">Communifarm CEA</text>'
        ),
    ]
    # Fresh-air and condensate lines, drawn under the room cards.
    parts.append(
        '<line x1="8" y1="34" x2="116" y2="34" stroke="#e2c044" stroke-width="0.6"/>'
    )
    parts.append(
        '<line x1="8" y1="50" x2="16" y2="50" stroke="#4aa3d8" stroke-width="0.8"/>'
    )
    for room in _ROOMS:
        if room.kind == KIND_OUTDOOR:
            continue
        parts.append(
            f'<rect x="{room.x}" y="{room.y}" width="{room.w}" height="{room.h}" '
            f'rx="1.2" fill="{room.fill}" stroke="#d7dde2" stroke-width="0.35"/>'
        )
        parts.append(
            f'<text x="{room.x + 1.2}" y="{room.y + 3.2}" fill="#f4f7f5" '
            f'font-size="2.2" font-family="sans-serif">{escape(room.title)}</text>'
        )
        if room.kind not in {KIND_GENERAL_ROOM, KIND_OUTDOOR} and room.h >= 20:
            for slot in range(5):
                xy = sensor_xy(room.kind, slot)
                if xy is None:
                    continue
                x, y = xy
                parts.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.7" fill="none" '
                    'stroke="#d7dde2" stroke-width="0.25"/>'
                )
    outdoor = _ROOM_BY_KIND[KIND_OUTDOOR]
    parts.append(
        f'<rect x="{outdoor.x}" y="{outdoor.y}" width="{outdoor.w}" height="{outdoor.h}" '
        f'rx="1.2" fill="{outdoor.fill}" stroke="#d7dde2" stroke-width="0.35"/>'
    )
    parts.append(
        f'<text x="{outdoor.x + 1.2}" y="{outdoor.y + 3.2}" fill="#f4f7f5" '
        'font-size="2.2" font-family="sans-serif">Outdoors</text>'
    )
    for role, x in ((ROLE_TEMPERATURE, 18.0), (ROLE_HUMIDITY, 36.0), (ROLE_PRESSURE, 54.0)):
        parts.append(
            f'<text x="{x}" y="6.2" fill="#e7f2f8" font-size="1.8" '
            f'font-family="sans-serif">{ROLE_LABEL[role]}</text>'
        )
    for role, y in (
        (ROLE_AC, 18.0),
        (ROLE_HEATER, 26.0),
        (ROLE_FRESH_AIR_INTAKE, 34.0),
        (ROLE_FLOAT, 42.0),
        (ROLE_CONDENSATE_PUMP, 50.0),
    ):
        parts.append(
            f'<rect x="4.2" y="{y - 1.6}" width="7.2" height="3.2" rx="0.4" '
            'fill="#2c3338" stroke="#e2c044" stroke-width="0.25"/>'
        )
        parts.append(
            f'<text x="4.6" y="{y + 0.7}" fill="#f4e7b0" font-size="1.6" '
            f'font-family="sans-serif">{ROLE_LABEL[role]}</text>'
        )
    parts.append(
        '<text x="4" y="76.5" fill="#b7c0c6" font-size="1.7" font-family="sans-serif">'
        "Preset schematic. Live sensors sit on the dots. Not a scale drawing."
        "</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _xy_for(kind: str, role: str, slot: int) -> tuple[float, float] | None:
    if role == ROLE_HUMIDITY and kind not in {KIND_OUTDOOR, KIND_GENERAL_ROOM}:
        return sensor_xy(kind, slot, humidity=True)
    if role == ROLE_TEMPERATURE and kind not in {KIND_OUTDOOR, KIND_GENERAL_ROOM}:
        return sensor_xy(kind, slot)
    if role == ROLE_TEMPERATURE and kind == KIND_GENERAL_ROOM:
        return 8.0, 62.0
    if role == ROLE_HUMIDITY and kind == KIND_GENERAL_ROOM:
        return 14.0, 62.0
    return machine_xy(kind, role)
