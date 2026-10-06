"""Sensors and machines inked on the operator schematic.

The drawing labels outdoor T, RH, and P, the general-room AC, heater, fresh-air
intake, float, and condensate pump, and five sensor dots in each tent. Harvest
and the storage rooms are names only, so they get no preset entity.
"""

from __future__ import annotations

from dataclasses import dataclass

from .climate import (
    KIND_CULTURE_PREP,
    KIND_FRUITING,
    KIND_GENERAL_ROOM,
    KIND_INCUBATION,
    KIND_INOCULATION,
    KIND_OUTDOOR,
    KIND_SPECS,
    ROLE_AC,
    ROLE_CONDENSATE_PUMP,
    ROLE_FLOAT,
    ROLE_FRESH_AIR_INTAKE,
    ROLE_HEATER,
    ROLE_HUMIDITY,
    ROLE_PRESSURE,
    ROLE_TEMPERATURE,
)

PLATFORM_SENSOR = "sensor"
PLATFORM_SWITCH = "switch"
PLATFORM_BINARY_SENSOR = "binary_sensor"

DOT_KINDS = (
    KIND_CULTURE_PREP,
    KIND_INOCULATION,
    KIND_INCUBATION,
    KIND_FRUITING,
)
DOT_SLOTS = 5

_ROLE_NAME = {
    ROLE_TEMPERATURE: "temperature",
    ROLE_HUMIDITY: "humidity",
    ROLE_PRESSURE: "pressure",
    ROLE_AC: "AC",
    ROLE_HEATER: "heater",
    ROLE_FRESH_AIR_INTAKE: "fresh air",
    ROLE_FLOAT: "float",
    ROLE_CONDENSATE_PUMP: "condensate pump",
}


@dataclass(frozen=True, slots=True)
class DrawingDevice:
    """One preset entity that sits on a mark already drawn on the schematic."""

    kind: str
    role: str
    slot: int
    platform: str
    initial: float | None = None


def drawing_devices() -> tuple[DrawingDevice, ...]:
    """Labeled outdoor sensors, general-room machines, and five probes per tent."""
    devices: list[DrawingDevice] = [
        DrawingDevice(KIND_OUTDOOR, ROLE_TEMPERATURE, 0, PLATFORM_SENSOR, 12.0),
        DrawingDevice(KIND_OUTDOOR, ROLE_HUMIDITY, 0, PLATFORM_SENSOR, 70.0),
        DrawingDevice(KIND_OUTDOOR, ROLE_PRESSURE, 0, PLATFORM_SENSOR, 1013.0),
        DrawingDevice(KIND_GENERAL_ROOM, ROLE_AC, 0, PLATFORM_SWITCH),
        DrawingDevice(KIND_GENERAL_ROOM, ROLE_HEATER, 0, PLATFORM_SWITCH),
        DrawingDevice(KIND_GENERAL_ROOM, ROLE_FRESH_AIR_INTAKE, 0, PLATFORM_SWITCH),
        DrawingDevice(KIND_GENERAL_ROOM, ROLE_FLOAT, 0, PLATFORM_BINARY_SENSOR),
        DrawingDevice(KIND_GENERAL_ROOM, ROLE_CONDENSATE_PUMP, 0, PLATFORM_SWITCH),
    ]
    for kind in DOT_KINDS:
        spec = KIND_SPECS[kind]
        for slot in range(DOT_SLOTS):
            devices.append(
                DrawingDevice(
                    kind, ROLE_TEMPERATURE, slot, PLATFORM_SENSOR, spec.temperature_target
                )
            )
            devices.append(
                DrawingDevice(
                    kind, ROLE_HUMIDITY, slot, PLATFORM_SENSOR, spec.humidity_target
                )
            )
    return tuple(devices)


def drawing_object_id(device: DrawingDevice) -> str:
    """Stable object id. Tent probes are numbered to match the five dots."""
    base = f"communifarm_{device.kind}_{device.role}"
    if device.kind in DOT_KINDS and device.role in {ROLE_TEMPERATURE, ROLE_HUMIDITY}:
        return f"{base}_{device.slot + 1}"
    return base


def drawing_entity_id(device: DrawingDevice) -> str:
    return f"{device.platform}.{drawing_object_id(device)}"


def drawing_name(device: DrawingDevice) -> str:
    title = KIND_SPECS[device.kind].name
    label = _ROLE_NAME[device.role]
    if device.kind in DOT_KINDS and device.role in {ROLE_TEMPERATURE, ROLE_HUMIDITY}:
        return f"{title} {label} {device.slot + 1}"
    return f"{title} {label}"
