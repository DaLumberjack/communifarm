"""Pure climate decisions. No Home Assistant imports and no GPIO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from .climate import (
    ENCLOSURE_OUTDOOR,
    KIND_OUTDOOR,
    LIGHT_GRACE_MINUTES,
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
    SOURCE_NONE,
    ClimateBinding,
    ClimateNode,
    EffectiveReading,
    SensorSample,
    resolve_effective_readings,
    resolved_photoperiod,
)

_FANS = (
    ROLE_CIRCULATION_FAN,
    ROLE_INTAKE_FAN,
    ROLE_EXHAUST_FAN,
    ROLE_FRESH_AIR_INTAKE,
)


@dataclass(slots=True)
class ObservedState:
    """What the adapter last saw. Domain code does not read entity state."""

    light_on: bool = False
    light_on_since: datetime | None = None


@dataclass(slots=True)
class ControlIntent:
    """One on/off command for a bound entity."""

    node_id: str
    role: str
    entity_id: str
    turn_on: bool
    reason: str


@dataclass(slots=True)
class ControlDecision:
    readings: dict[str, dict[str, EffectiveReading]]
    intents: list[ControlIntent]


def light_should_be_on(node: ClimateNode, now: datetime) -> bool:
    """On/off photoperiod from midnight. No spectrum control."""
    hours_on, hours_off = resolved_photoperiod(node)
    if hours_on <= 0:
        return False
    cycle_min = int(round((hours_on + hours_off) * 60))
    if cycle_min <= 0:
        return False
    minute_of_day = now.hour * 60 + now.minute
    return (minute_of_day % cycle_min) < int(round(hours_on * 60))


def decide_control(
    nodes: list[ClimateNode],
    samples_by_node: dict[str, list[SensorSample]],
    bindings_by_node: dict[str, list[ClimateBinding]],
    observed_by_node: dict[str, ObservedState],
    now: datetime,
) -> ControlDecision:
    """Return intents for bound actuators only. Uncontrolled nodes stay quiet."""
    readings = resolve_effective_readings(nodes, samples_by_node)
    by_id = {node.id: node for node in nodes}
    desired_light = {node.id: light_should_be_on(node, now) for node in nodes}
    intents: list[ControlIntent] = []
    for node in nodes:
        if not node.control_enabled:
            continue
        intents.extend(
            _decide_node(
                node,
                nodes,
                by_id,
                readings,
                samples_by_node.get(node.id, []),
                bindings_by_node,
                observed_by_node,
                desired_light,
                now,
            )
        )
    return ControlDecision(readings=readings, intents=intents)


def format_decision_summary(
    nodes: list[ClimateNode], decision: ControlDecision
) -> str:
    """Markdown bullets: one room, its reading, and any machine that is on."""
    if not nodes:
        return "- No climate nodes."
    by_node: dict[str, list[ControlIntent]] = {}
    for intent in decision.intents:
        by_node.setdefault(intent.node_id, []).append(intent)
    lines: list[str] = []
    for node in nodes:
        readings = decision.readings.get(node.id, {})
        bits = [
            _fmt_metric("temp", readings.get(ROLE_TEMPERATURE), "°C"),
            _fmt_metric("RH", readings.get(ROLE_HUMIDITY), "%"),
        ]
        pressure = readings.get(ROLE_PRESSURE)
        if pressure is not None and pressure.source != SOURCE_NONE:
            bits.append(_fmt_metric("pressure", pressure, ""))
        co2 = readings.get(ROLE_CO2_PPM)
        if co2 is not None and co2.source != SOURCE_NONE:
            bits.append(_fmt_metric("CO2", co2, "ppm"))
        commands = by_node.get(node.id, [])
        ons = [
            f"{intent.role.replace('_', ' ')} on ({intent.reason})"
            for intent in commands
            if intent.turn_on
        ]
        if not node.control_enabled:
            tail = "Control off."
        elif ons:
            tail = "; ".join(ons) + "."
        else:
            tail = "Holding."
        lines.append(f"- **{node.name}** — {', '.join(bits)}. {tail}")
    return "\n".join(lines)


def _fmt_metric(label: str, reading: EffectiveReading | None, unit: str) -> str:
    if reading is None or reading.value is None or reading.source == SOURCE_NONE:
        return f"no {label}"
    number = f"{reading.value:.1f}" if unit == "°C" else f"{reading.value:.0f}"
    suffix = unit if unit == "%" else (f" {unit}" if unit else "")
    if unit == "°C":
        suffix = "°C"
    return f"{number}{suffix} {reading.source}"


def _decide_node(
    node: ClimateNode,
    nodes: list[ClimateNode],
    by_id: dict[str, ClimateNode],
    readings: dict[str, dict[str, EffectiveReading]],
    samples: list[SensorSample],
    bindings_by_node: dict[str, list[ClimateBinding]],
    observed_by_node: dict[str, ObservedState],
    desired_light: dict[str, bool],
    now: datetime,
) -> list[ControlIntent]:
    bindings = bindings_by_node.get(node.id, [])
    observed = observed_by_node.get(node.id, ObservedState())
    node_readings = readings[node.id]
    temp = _value(node_readings, ROLE_TEMPERATURE)
    hum = _value(node_readings, ROLE_HUMIDITY)
    ppm = _value(node_readings, ROLE_CO2_PPM)
    source_temp, source_hum = _parent_air(node, readings)
    out_temp, out_hum = _outdoor_air(node, by_id, readings)

    target_t = node.temperature_target
    target_h = node.humidity_target
    band_t = node.temp_deadband
    band_h = node.humidity_deadband
    too_hot = (
        temp is not None and target_t is not None and temp > target_t + band_t
    )
    too_cold = (
        temp is not None and target_t is not None and temp < target_t - band_t
    )
    too_dry = (
        hum is not None and target_h is not None and hum < target_h - band_h
    )
    too_wet = (
        hum is not None and target_h is not None and hum > target_h + band_h
    )

    cmds: dict[str, tuple[bool, str]] = {}
    missing_climate = temp is None and hum is None
    for role in _FANS:
        cmds[role] = (False, "no reading" if missing_climate else "in band")
    cmds[ROLE_HEATER] = (
        False,
        "no reading" if temp is None or target_t is None else "in band",
    )
    cmds[ROLE_AC] = (
        False,
        "no reading" if temp is None or target_t is None else "in band",
    )
    cmds[ROLE_HUMIDIFIER] = (
        False,
        "no reading" if hum is None or target_h is None else "in band",
    )
    cmds[ROLE_DEHUMIDIFIER] = (
        False,
        "no reading" if hum is None or target_h is None else "in band",
    )

    if too_hot:
        cmds[ROLE_HEATER] = (False, "too hot")
        parent_can_cool = _air_can_reach(temp, source_temp, target_t, hot=True)
        outdoor_can_cool = _air_can_reach(temp, out_temp, target_t, hot=True)
        if parent_can_cool or outdoor_can_cool:
            _set_on(cmds, ROLE_EXHAUST_FAN, "too hot; parent air can cool")
            _set_on(cmds, ROLE_INTAKE_FAN, "too hot; parent air can cool")
            cmds[ROLE_AC] = (False, "too hot; parent air can cool")
        else:
            _note_off(cmds, ROLE_EXHAUST_FAN, "too hot; external air will not help")
            _note_off(cmds, ROLE_INTAKE_FAN, "too hot; external air will not help")
            _set_on(cmds, ROLE_AC, "too hot; external air will not help")
    elif too_cold:
        cmds[ROLE_AC] = (False, "too cold")
        _set_on(cmds, ROLE_HEATER, "too cold")

    if too_wet:
        if _has_binding(bindings, ROLE_DEHUMIDIFIER):
            _set_on(cmds, ROLE_DEHUMIDIFIER, "too humid; dehumidifier")
        elif _air_can_reach(hum, source_hum, target_h, hot=True) or _air_can_reach(
            hum, out_hum, target_h, hot=True
        ):
            _set_on(cmds, ROLE_EXHAUST_FAN, "too humid; external air can dry")
            _set_on(cmds, ROLE_INTAKE_FAN, "too humid; external air can dry")
        else:
            _note_off(cmds, ROLE_EXHAUST_FAN, "too humid; external air will not help")
            _note_off(cmds, ROLE_INTAKE_FAN, "too humid; external air will not help")
    elif too_dry:
        if _in_light_grace(observed, now):
            _note_off(cmds, ROLE_HUMIDIFIER, "too dry; light grace")
        else:
            _set_on(cmds, ROLE_HUMIDIFIER, "too dry")

    if too_hot or too_cold or too_dry or too_wet:
        _set_on(cmds, ROLE_CIRCULATION_FAN, "out of band")

    if (
        ppm is not None
        and node.co2_ppm_target is not None
        and ppm > node.co2_ppm_target
    ):
        _set_on(cmds, ROLE_INTAKE_FAN, "co2 above target")

    if _fresh_air_helps(
        temp, out_temp, target_t, band_t, hum, out_hum, target_h, band_h
    ):
        _set_on(cmds, ROLE_FRESH_AIR_INTAKE, "fresh air helps")
    elif (too_hot or too_cold or too_dry or too_wet) and (
        out_temp is not None or out_hum is not None
    ):
        _note_off(cmds, ROLE_FRESH_AIR_INTAKE, "external air will not help")

    has_light = _has_binding(bindings, ROLE_LIGHT)
    lights_on = (has_light and (observed.light_on or desired_light[node.id])) or (
        _child_waste_heat(
            node, nodes, bindings_by_node, observed_by_node, desired_light
        )
    )
    if lights_on:
        cmds[ROLE_HEATER] = (False, "heater suppressed; lights on")

    if cmds[ROLE_HEATER][0] and cmds[ROLE_AC][0]:
        cmds[ROLE_HEATER] = (False, "heater and ac both requested")
        cmds[ROLE_AC] = (False, "heater and ac both requested")

    float_active = _float_active(samples)
    if float_active is True:
        cmds[ROLE_CONDENSATE_PUMP] = (True, "float active")
    else:
        cmds[ROLE_CONDENSATE_PUMP] = (False, "float clear or missing")

    if desired_light[node.id]:
        cmds[ROLE_LIGHT] = (True, "photoperiod on")
    else:
        cmds[ROLE_LIGHT] = (False, "photoperiod off")

    return _emit(node.id, bindings, cmds)


def _emit(
    node_id: str,
    bindings: list[ClimateBinding],
    cmds: dict[str, tuple[bool, str]],
) -> list[ControlIntent]:
    intents: list[ControlIntent] = []
    for role, (turn_on, reason) in cmds.items():
        for binding in bindings:
            if binding.role != role or not binding.entity_id:
                continue
            intents.append(
                ControlIntent(
                    node_id=node_id,
                    role=role,
                    entity_id=binding.entity_id,
                    turn_on=turn_on,
                    reason=reason,
                )
            )
    return intents


def _set_on(cmds: dict[str, tuple[bool, str]], role: str, reason: str) -> None:
    prev = cmds.get(role)
    if prev and prev[0]:
        cmds[role] = (True, f"{prev[1]}; {reason}")
    else:
        cmds[role] = (True, reason)


def _note_off(cmds: dict[str, tuple[bool, str]], role: str, reason: str) -> None:
    prev = cmds.get(role)
    if prev and prev[0]:
        return
    cmds[role] = (False, reason)


def _has_binding(bindings: list[ClimateBinding], role: str) -> bool:
    return any(binding.role == role and binding.entity_id for binding in bindings)


def _value(
    readings: dict[str, EffectiveReading], metric: str
) -> float | None:
    reading = readings.get(metric)
    if reading is None:
        return None
    return reading.value


def _parent_air(
    node: ClimateNode,
    readings: dict[str, dict[str, EffectiveReading]],
) -> tuple[float | None, float | None]:
    if not node.parent_id or node.parent_id not in readings:
        return None, None
    parent = readings[node.parent_id]
    return _value(parent, ROLE_TEMPERATURE), _value(parent, ROLE_HUMIDITY)


def _outdoor_air(
    node: ClimateNode,
    by_id: dict[str, ClimateNode],
    readings: dict[str, dict[str, EffectiveReading]],
) -> tuple[float | None, float | None]:
    current: ClimateNode | None = node
    seen: set[str] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        if current.kind == KIND_OUTDOOR or current.enclosure == ENCLOSURE_OUTDOOR:
            outdoor = readings.get(current.id, {})
            return _value(outdoor, ROLE_TEMPERATURE), _value(outdoor, ROLE_HUMIDITY)
        if not current.parent_id:
            return None, None
        current = by_id.get(current.parent_id)
    return None, None


def _air_can_reach(
    local: float | None,
    source: float | None,
    target: float | None,
    *,
    hot: bool,
) -> bool:
    """True when source air moves the metric to target, not merely toward it."""
    if local is None or source is None or target is None:
        return False
    if hot:
        return source < local and source <= target
    return source > local and source >= target


def _fresh_air_helps(
    temp: float | None,
    out_temp: float | None,
    target_t: float | None,
    band_t: float,
    hum: float | None,
    out_hum: float | None,
    target_h: float | None,
    band_h: float,
) -> bool:
    """On only when every out-of-band metric is helped by outdoor air."""
    checks: list[bool] = []
    if temp is not None and target_t is not None and temp > target_t + band_t:
        checks.append(_air_can_reach(temp, out_temp, target_t, hot=True))
    elif temp is not None and target_t is not None and temp < target_t - band_t:
        checks.append(_air_can_reach(temp, out_temp, target_t, hot=False))
    if hum is not None and target_h is not None and hum > target_h + band_h:
        checks.append(_air_can_reach(hum, out_hum, target_h, hot=True))
    elif hum is not None and target_h is not None and hum < target_h - band_h:
        checks.append(_air_can_reach(hum, out_hum, target_h, hot=False))
    return bool(checks) and all(checks)


def _float_active(samples: list[SensorSample]) -> bool | None:
    values = [
        float(sample.value)
        for sample in samples
        if sample.role == ROLE_FLOAT and not sample.stale and sample.value is not None
    ]
    if not values:
        return None
    return float(median(values)) >= 0.5


def _in_light_grace(observed: ObservedState, now: datetime) -> bool:
    """Hold the humidifier only after the light is actually on."""
    if not observed.light_on or observed.light_on_since is None:
        return False
    return now - observed.light_on_since < timedelta(minutes=LIGHT_GRACE_MINUTES)


def _child_waste_heat(
    node: ClimateNode,
    nodes: list[ClimateNode],
    bindings_by_node: dict[str, list[ClimateBinding]],
    observed_by_node: dict[str, ObservedState],
    desired_light: dict[str, bool],
) -> bool:
    """True when a child light dumps driver heat into this room."""
    for child in nodes:
        if child.parent_id != node.id:
            continue
        waste_lights = [
            binding
            for binding in bindings_by_node.get(child.id, [])
            if binding.role == ROLE_LIGHT
            and binding.waste_heat_to_parent
            and binding.entity_id
        ]
        if not waste_lights:
            continue
        child_observed = observed_by_node.get(child.id, ObservedState())
        if child_observed.light_on or desired_light.get(child.id, False):
            return True
    return False
