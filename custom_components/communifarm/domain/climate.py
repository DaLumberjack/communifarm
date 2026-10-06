"""Climate tree: parent rooms, child tents, optional sensors (no Home Assistant)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .location import (
    AREA_CULTURE_FRIDGE,
    AREA_FRUITING_TENT,
    AREA_HARVEST_FRIDGE,
    AREA_INOCULATION_TENT,
    AREA_STILL_AIR_CABINET,
)
from .models import new_id
from .validation import (
    HUMIDITY_SENSOR_MAX,
    HUMIDITY_SENSOR_MIN,
    TEMP_SENSOR_MAX_C,
    TEMP_SENSOR_MIN_C,
    ValidationError,
    validate_readable_name,
)

ENCLOSURE_INDOOR = "indoor"
ENCLOSURE_OUTDOOR = "outdoor"
ENCLOSURES = frozenset({ENCLOSURE_INDOOR, ENCLOSURE_OUTDOOR})

SOURCE_LOCAL = "local"
SOURCE_INHERITED = "inherited"
SOURCE_NONE = "none"

KIND_OUTDOOR = "outdoor"
KIND_GENERAL_ROOM = "general_room"
KIND_CULTURE_PREP = "culture_prep"
KIND_INOCULATION = "inoculation"
KIND_INCUBATION = "incubation"
KIND_FRUITING = "fruiting"
KIND_HARVEST = "harvest"
KIND_READY_TO_SELL = "ready_to_sell"
KIND_STORAGE_HARD_GOODS = "storage_hard_goods"
KIND_STORAGE_CONSUMABLES = "storage_consumables"
KIND_STORAGE = "storage"

CLIMATE_KINDS = frozenset(
    {
        KIND_OUTDOOR,
        KIND_GENERAL_ROOM,
        KIND_CULTURE_PREP,
        KIND_INOCULATION,
        KIND_INCUBATION,
        KIND_FRUITING,
        KIND_HARVEST,
        KIND_READY_TO_SELL,
        KIND_STORAGE_HARD_GOODS,
        KIND_STORAGE_CONSUMABLES,
        KIND_STORAGE,
    }
)

ROLE_TEMPERATURE = "temperature"
ROLE_HUMIDITY = "humidity"
ROLE_PRESSURE = "pressure"
ROLE_CO2_PPM = "co2_ppm"
ROLE_CIRCULATION_FAN = "circulation_fan"
ROLE_INTAKE_FAN = "intake_fan"
ROLE_EXHAUST_FAN = "exhaust_fan"
ROLE_FRESH_AIR_INTAKE = "fresh_air_intake"
ROLE_AC = "ac"
ROLE_HEATER = "heater"
ROLE_HUMIDIFIER = "humidifier"
ROLE_DEHUMIDIFIER = "dehumidifier"
ROLE_LIGHT = "light"
ROLE_FLOAT = "float"
ROLE_CONDENSATE_PUMP = "condensate_pump"

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
CLIMATE_ROLES = frozenset(SENSOR_ROLES | ACTUATOR_ROLES)

READING_METRICS = (ROLE_TEMPERATURE, ROLE_HUMIDITY, ROLE_PRESSURE, ROLE_CO2_PPM)

PHOTOPERIOD_FRUITING = "fruiting"
PHOTOPERIOD_DARK = "dark"
PHOTOPERIOD_GREENS = "greens"
PHOTOPERIOD_HOURS: dict[str, tuple[float, float]] = {
    PHOTOPERIOD_FRUITING: (12.0, 12.0),
    PHOTOPERIOD_DARK: (0.0, 24.0),
    PHOTOPERIOD_GREENS: (16.0, 8.0),
}

DEFAULT_TEMP_DEADBAND_C = 1.0
DEFAULT_HUMIDITY_DEADBAND = 5.0
DEFAULT_CO2_PPM_TARGET = 1000.0
LIGHT_GRACE_MINUTES = 15

# Placement shelves are not climate nodes. This only links a shelf to a climate.
PLACEMENT_AREA_CLIMATE_KIND: dict[str, str] = {
    AREA_FRUITING_TENT: KIND_FRUITING,
    AREA_INOCULATION_TENT: KIND_INOCULATION,
    AREA_CULTURE_FRIDGE: KIND_CULTURE_PREP,
    AREA_STILL_AIR_CABINET: KIND_CULTURE_PREP,
    AREA_HARVEST_FRIDGE: KIND_HARVEST,
}

TENT_ROLES = (
    ROLE_TEMPERATURE,
    ROLE_HUMIDITY,
    ROLE_CIRCULATION_FAN,
    ROLE_INTAKE_FAN,
    ROLE_EXHAUST_FAN,
)


@dataclass(frozen=True, slots=True)
class ClimateKindSpec:
    """Data for one operator-layout kind. Not a fungi-only code branch."""

    kind: str
    name: str
    enclosure: str
    control_enabled: bool
    parent_kind: str | None
    temperature_target: float | None
    humidity_target: float | None
    co2_ppm_target: float | None
    photoperiod_preset: str | None
    expected_roles: tuple[str, ...]


OPERATOR_SPECS: tuple[ClimateKindSpec, ...] = (
    ClimateKindSpec(
        KIND_OUTDOOR,
        "Outdoors",
        ENCLOSURE_OUTDOOR,
        False,
        None,
        None,
        None,
        None,
        None,
        (ROLE_TEMPERATURE, ROLE_HUMIDITY, ROLE_PRESSURE),
    ),
    ClimateKindSpec(
        KIND_GENERAL_ROOM,
        "General room",
        ENCLOSURE_INDOOR,
        True,
        KIND_OUTDOOR,
        22.0,
        55.0,
        None,
        None,
        (
            ROLE_TEMPERATURE,
            ROLE_HUMIDITY,
            ROLE_AC,
            ROLE_HEATER,
            ROLE_FRESH_AIR_INTAKE,
            ROLE_FLOAT,
            ROLE_CONDENSATE_PUMP,
        ),
    ),
    ClimateKindSpec(
        KIND_CULTURE_PREP,
        "Culture prep",
        ENCLOSURE_INDOOR,
        True,
        KIND_GENERAL_ROOM,
        22.0,
        50.0,
        None,
        PHOTOPERIOD_DARK,
        TENT_ROLES,
    ),
    ClimateKindSpec(
        KIND_INOCULATION,
        "Inoculation",
        ENCLOSURE_INDOOR,
        True,
        KIND_GENERAL_ROOM,
        22.0,
        50.0,
        DEFAULT_CO2_PPM_TARGET,
        PHOTOPERIOD_DARK,
        TENT_ROLES + (ROLE_CO2_PPM,),
    ),
    ClimateKindSpec(
        KIND_INCUBATION,
        "Incubation",
        ENCLOSURE_INDOOR,
        True,
        KIND_GENERAL_ROOM,
        22.0,
        75.0,
        DEFAULT_CO2_PPM_TARGET,
        PHOTOPERIOD_DARK,
        TENT_ROLES + (ROLE_FRESH_AIR_INTAKE, ROLE_CO2_PPM),
    ),
    ClimateKindSpec(
        KIND_FRUITING,
        "Fruiting",
        ENCLOSURE_INDOOR,
        True,
        KIND_GENERAL_ROOM,
        20.0,
        90.0,
        None,
        PHOTOPERIOD_FRUITING,
        TENT_ROLES + (ROLE_HUMIDIFIER, ROLE_DEHUMIDIFIER, ROLE_LIGHT),
    ),
    ClimateKindSpec(
        KIND_HARVEST,
        "Harvest",
        ENCLOSURE_INDOOR,
        False,
        KIND_GENERAL_ROOM,
        15.0,
        85.0,
        None,
        None,
        (ROLE_TEMPERATURE, ROLE_HUMIDITY),
    ),
    ClimateKindSpec(
        KIND_READY_TO_SELL,
        "Ready to sell",
        ENCLOSURE_INDOOR,
        False,
        KIND_GENERAL_ROOM,
        4.0,
        80.0,
        None,
        None,
        (ROLE_TEMPERATURE, ROLE_HUMIDITY),
    ),
    ClimateKindSpec(
        KIND_STORAGE_HARD_GOODS,
        "Hard goods storage",
        ENCLOSURE_INDOOR,
        False,
        KIND_GENERAL_ROOM,
        None,
        None,
        None,
        None,
        (),
    ),
    ClimateKindSpec(
        KIND_STORAGE_CONSUMABLES,
        "Consumable storage",
        ENCLOSURE_INDOOR,
        False,
        KIND_GENERAL_ROOM,
        18.0,
        50.0,
        None,
        None,
        (ROLE_TEMPERATURE, ROLE_HUMIDITY),
    ),
    ClimateKindSpec(
        KIND_STORAGE,
        "General storage",
        ENCLOSURE_INDOOR,
        False,
        KIND_GENERAL_ROOM,
        18.0,
        50.0,
        None,
        None,
        (ROLE_TEMPERATURE, ROLE_HUMIDITY),
    ),
)

KIND_SPECS: dict[str, ClimateKindSpec] = {spec.kind: spec for spec in OPERATOR_SPECS}


@dataclass(slots=True)
class ClimateNode:
    """One climate volume. Indoor children may inherit a parent reading."""

    site_id: str
    name: str
    kind: str
    enclosure: str
    control_enabled: bool
    id: str = ""
    parent_id: str | None = None
    temperature_target: float | None = None
    humidity_target: float | None = None
    co2_ppm_target: float | None = None
    temp_deadband: float = DEFAULT_TEMP_DEADBAND_C
    humidity_deadband: float = DEFAULT_HUMIDITY_DEADBAND
    photoperiod_preset: str | None = None
    light_hours_on: float | None = None
    light_hours_off: float | None = None
    created_at: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("climate")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClimateBinding:
    """Role bound to a Home Assistant entity registry id. Many sensors per node."""

    node_id: str
    role: str
    entity_entry_id: str
    entity_id: str | None = None
    id: str = ""
    waste_heat_to_parent: bool = False
    created_at: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("cbind")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SensorSample:
    """One live reading. Stale or missing values are not zeros."""

    role: str
    value: float | None
    stale: bool = False
    entity_id: str | None = None


@dataclass(slots=True)
class EffectiveReading:
    """Median of local sensors, else the parent's effective value."""

    metric: str
    value: float | None
    source: str
    sample_count: int = 0


def validate_climate_node(node: ClimateNode) -> None:
    """Reject impossible targets and outdoor nodes that claim a parent."""
    if node.kind not in CLIMATE_KINDS:
        raise ValidationError(f"unknown climate kind: {node.kind}")
    if node.enclosure not in ENCLOSURES:
        raise ValidationError(f"unknown enclosure: {node.enclosure}")
    if node.enclosure == ENCLOSURE_OUTDOOR and node.parent_id:
        raise ValidationError("outdoor climate cannot have a parent")
    validate_readable_name(node.name, field_name="climate.name")
    _check_target(
        node.temperature_target,
        TEMP_SENSOR_MIN_C,
        TEMP_SENSOR_MAX_C,
        "temperature_target",
    )
    _check_target(
        node.humidity_target,
        HUMIDITY_SENSOR_MIN,
        HUMIDITY_SENSOR_MAX,
        "humidity_target",
    )
    if node.co2_ppm_target is not None and not (0.0 <= node.co2_ppm_target <= 10000.0):
        raise ValidationError("co2_ppm_target out of range")
    if not (0.0 < node.temp_deadband <= 20.0):
        raise ValidationError("temp_deadband must be between 0 and 20 °C")
    if not (0.0 < node.humidity_deadband <= 50.0):
        raise ValidationError("humidity_deadband must be between 0 and 50 %")
    if node.photoperiod_preset and node.photoperiod_preset not in PHOTOPERIOD_HOURS:
        raise ValidationError(f"unknown photoperiod preset: {node.photoperiod_preset}")


def resolved_photoperiod(node: ClimateNode) -> tuple[float, float]:
    """Hours on, hours off. Node overrides win over the kind preset."""
    if node.light_hours_on is not None and node.light_hours_off is not None:
        return float(node.light_hours_on), float(node.light_hours_off)
    if node.photoperiod_preset:
        return PHOTOPERIOD_HOURS[node.photoperiod_preset]
    return (0.0, 24.0)


def build_operator_layout(
    site_id: str,
    *,
    general_room_id: str,
    general_room_name: str,
    general_temperature_target: float,
    general_humidity_target: float,
) -> list[ClimateNode]:
    """Operator preset. General room reuses the onboarding environment id."""
    if not site_id or not str(site_id).strip():
        raise ValidationError("site_id is required")
    if not general_room_id or not str(general_room_id).strip():
        raise ValidationError("general_room_id is required")
    validate_readable_name(general_room_name, field_name="environment.name")

    built: dict[str, ClimateNode] = {}
    for spec in OPERATOR_SPECS:
        hours_on, hours_off = (
            PHOTOPERIOD_HOURS[spec.photoperiod_preset]
            if spec.photoperiod_preset
            else (None, None)
        )
        if spec.kind == KIND_GENERAL_ROOM:
            node = ClimateNode(
                id=str(general_room_id).strip(),
                site_id=str(site_id).strip(),
                name=general_room_name,
                kind=spec.kind,
                enclosure=spec.enclosure,
                control_enabled=spec.control_enabled,
                temperature_target=general_temperature_target,
                humidity_target=general_humidity_target,
                co2_ppm_target=spec.co2_ppm_target,
                photoperiod_preset=spec.photoperiod_preset,
                light_hours_on=hours_on,
                light_hours_off=hours_off,
            )
        else:
            node = ClimateNode(
                site_id=str(site_id).strip(),
                name=spec.name,
                kind=spec.kind,
                enclosure=spec.enclosure,
                control_enabled=spec.control_enabled,
                temperature_target=spec.temperature_target,
                humidity_target=spec.humidity_target,
                co2_ppm_target=spec.co2_ppm_target,
                photoperiod_preset=spec.photoperiod_preset,
                light_hours_on=hours_on,
                light_hours_off=hours_off,
            )
        built[spec.kind] = node

    ordered: list[ClimateNode] = []
    for spec in OPERATOR_SPECS:
        node = built[spec.kind]
        if spec.parent_kind:
            node.parent_id = built[spec.parent_kind].id
        validate_climate_node(node)
        ordered.append(node)
    return ordered


def resolve_effective_readings(
    nodes: list[ClimateNode],
    samples_by_node: dict[str, list[SensorSample]],
) -> dict[str, dict[str, EffectiveReading]]:
    """Local median, else inherit from the indoor node's parent. Outdoor never inherits."""
    from statistics import median

    by_id = {node.id: node for node in nodes}
    cache: dict[tuple[str, str], EffectiveReading] = {}

    def local_values(node_id: str, metric: str) -> list[float]:
        values: list[float] = []
        for sample in samples_by_node.get(node_id, []):
            if sample.role != metric or sample.stale or sample.value is None:
                continue
            values.append(float(sample.value))
        return values

    def one(node_id: str, metric: str, stack: tuple[str, ...]) -> EffectiveReading:
        key = (node_id, metric)
        cached = cache.get(key)
        if cached is not None:
            return cached
        node = by_id[node_id]
        values = local_values(node_id, metric)
        if values:
            reading = EffectiveReading(
                metric, float(median(values)), SOURCE_LOCAL, len(values)
            )
            cache[key] = reading
            return reading
        can_inherit = (
            node.enclosure == ENCLOSURE_INDOOR
            and bool(node.parent_id)
            and node.parent_id in by_id
            and node_id not in stack
        )
        if not can_inherit:
            reading = EffectiveReading(metric, None, SOURCE_NONE, 0)
            cache[key] = reading
            return reading
        assert node.parent_id is not None
        parent = one(node.parent_id, metric, stack + (node_id,))
        if parent.value is None:
            reading = EffectiveReading(metric, None, SOURCE_NONE, 0)
        else:
            reading = EffectiveReading(
                metric, parent.value, SOURCE_INHERITED, parent.sample_count
            )
        cache[key] = reading
        return reading

    return {
        node.id: {metric: one(node.id, metric, ()) for metric in READING_METRICS}
        for node in nodes
    }


def format_unseeded_summary() -> str:
    return (
        "- No climate tree yet.\n"
        "- Setup seeds the rooms. Storage stays uncontrolled until a machine is bound."
    )


def format_layout_preview(nodes: list[ClimateNode]) -> str:
    lines = ["Climate layout seeded. Readings appear after the next control tick."]
    by_id = {node.id: node for node in nodes}
    for node in nodes:
        parent = by_id.get(node.parent_id or "")
        parent_name = parent.name if parent else "none"
        control = "control on" if node.control_enabled else "control off"
        lines.append(
            f"- {node.name} ({node.kind}, {node.enclosure}, {control}, parent {parent_name})"
        )
    return "\n".join(lines)


def _check_target(
    value: float | None, low: float, high: float, field_name: str
) -> None:
    if value is None:
        return
    if not (low <= float(value) <= high):
        raise ValidationError(f"{field_name} out of range")
