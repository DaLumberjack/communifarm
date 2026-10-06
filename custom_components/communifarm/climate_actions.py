"""Home Assistant adapter for climate layout, ticks, and entity commands."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_CLIMATE_UPDATED
from .dashboard.provisioner import async_provision_dashboard
from .domain.climate import (
    CLIMATE_ROLES,
    ROLE_FLOAT,
    ROLE_LIGHT,
    SENSOR_ROLES,
    ClimateBinding,
    ClimateNode,
    SensorSample,
    format_layout_preview,
    format_unseeded_summary,
)
from .domain.climate_control import (
    ControlIntent,
    ObservedState,
    decide_control,
    format_decision_summary,
)
from .domain.climate_drawing import drawing_devices, drawing_entity_id
from .domain.models import CommunifarmState
from .domain.validation import ValidationError
from .storage.climate_repository import ClimateRepository

_LOGGER = logging.getLogger(__name__)

_ON_STATES = frozenset({"on", "true", "1"})


def _repo(hass: HomeAssistant, entry_id: str) -> ClimateRepository:
    repo = hass.data[DOMAIN][entry_id].get("climate_repository")
    if repo is None:
        raise HomeAssistantError("Climate repository is not available")
    return repo


def _state(hass: HomeAssistant, entry_id: str) -> CommunifarmState:
    return hass.data[DOMAIN][entry_id]["state"]


def _publish(hass: HomeAssistant, entry_id: str, snapshot: dict[str, Any]) -> None:
    hass.data[DOMAIN][entry_id]["climate_snapshot"] = snapshot
    async_dispatcher_send(hass, SIGNAL_CLIMATE_UPDATED, entry_id)


async def async_ensure_climate_layout(
    hass: HomeAssistant, entry_id: str
) -> dict[str, Any]:
    """Seed the operator climate tree once. Later calls only fill missing links."""
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    nodes = await repo.async_ensure_operator_layout(
        state.site.id,
        general_room_id=state.environment.id,
        general_room_name=state.environment.name,
        general_temperature_target=state.profile.temperature_target,
        general_humidity_target=state.profile.humidity_target,
    )
    await _bind_drawing_devices(repo, nodes)
    summary = {
        "site_id": state.site.id,
        "node_count": len(nodes),
        "nodes": [
            {
                "id": node.id,
                "name": node.name,
                "kind": node.kind,
                "parent_id": node.parent_id,
                "control_enabled": node.control_enabled,
            }
            for node in nodes
        ],
    }
    _publish(
        hass,
        entry_id,
        {
            "summary": format_layout_preview(nodes),
            "node_count": len(nodes),
            "seeded": True,
        },
    )
    _LOGGER.info(
        "Climate layout ready for site %s: %s nodes", state.site.id, len(nodes)
    )
    await async_provision_dashboard(hass, state)
    await async_tick_climate(hass, entry_id)
    return summary


async def _bind_drawing_devices(repo: ClimateRepository, nodes: list[ClimateNode]) -> None:
    """Bind the sensors and machines that are already labeled on the schematic."""
    by_kind = {node.kind: node for node in nodes}
    for device in drawing_devices():
        node = by_kind.get(device.kind)
        if node is None:
            continue
        entity_id = drawing_entity_id(device)
        await repo.async_upsert_binding(
            ClimateBinding(
                node_id=node.id,
                role=device.role,
                entity_entry_id=entity_id,
                entity_id=entity_id,
            )
        )


async def async_bind_climate_role(
    hass: HomeAssistant,
    entry_id: str,
    *,
    node_id: str,
    role: str,
    entity_id: str,
    entity_entry_id: str | None = None,
    waste_heat_to_parent: bool = False,
) -> str:
    """Bind a sensor or machine. Registry id falls back to the entity id."""
    if role not in CLIMATE_ROLES:
        raise HomeAssistantError(f"unknown climate role: {role}")
    if not node_id or not str(node_id).strip():
        raise HomeAssistantError("node_id is required")
    if not entity_id or "." not in entity_id:
        raise HomeAssistantError("entity_id is required")
    repo = _repo(hass, entry_id)
    try:
        saved = await repo.async_upsert_binding(
            ClimateBinding(
                node_id=str(node_id).strip(),
                role=role,
                entity_entry_id=(entity_entry_id or entity_id).strip(),
                entity_id=entity_id.strip(),
                waste_heat_to_parent=waste_heat_to_parent,
            )
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    await async_provision_dashboard(hass, _state(hass, entry_id))
    return saved.id


async def async_tick_climate(hass: HomeAssistant, entry_id: str) -> int:
    """Read HA states, decide, command bound entities that are not already there."""
    bucket = hass.data[DOMAIN][entry_id]
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    nodes = await repo.async_list_nodes(state.site.id)
    if not nodes:
        _publish(
            hass,
            entry_id,
            {
                "summary": format_unseeded_summary(),
                "node_count": 0,
                "seeded": False,
            },
        )
        return 0

    bindings = await repo.async_list_bindings(state.site.id)
    bindings_by_node: dict[str, list[ClimateBinding]] = {}
    for binding in bindings:
        bindings_by_node.setdefault(binding.node_id, []).append(binding)

    now = datetime.now(tz=UTC)
    light_since: dict[str, str] = bucket.setdefault("climate_light_since", {})
    samples_by_node: dict[str, list] = {}
    observed_by_node: dict[str, ObservedState] = {}
    for node in nodes:
        node_bindings = bindings_by_node.get(node.id, [])
        samples_by_node[node.id] = [
            _sample(hass, binding)
            for binding in node_bindings
            if binding.role in SENSOR_ROLES and binding.entity_id
        ]
        observed_by_node[node.id] = _observed_lights(
            hass, node_bindings, light_since, now
        )

    decision = decide_control(
        nodes,
        samples_by_node,
        bindings_by_node,
        observed_by_node,
        now,
    )
    issued: list[ControlIntent] = []
    for intent in decision.intents:
        if await _apply_intent(hass, intent):
            issued.append(intent)
    if issued:
        await repo.async_insert_intents(issued, now.isoformat())
    _publish(
        hass,
        entry_id,
        {
            "summary": format_decision_summary(nodes, decision),
            "node_count": len(nodes),
            "seeded": True,
        },
    )
    return len(issued)


async def _apply_intent(hass: HomeAssistant, intent: ControlIntent) -> bool:
    if "." not in intent.entity_id:
        return False
    domain = intent.entity_id.split(".", 1)[0]
    desired = "on" if intent.turn_on else "off"
    current = hass.states.get(intent.entity_id)
    if current is not None and current.state == desired:
        return False
    service = "turn_on" if intent.turn_on else "turn_off"
    try:
        await hass.services.async_call(
            domain,
            service,
            {"entity_id": intent.entity_id},
            blocking=True,
        )
    except (HomeAssistantError, ValueError) as err:
        _LOGGER.warning(
            "Climate %s %s failed for %s: %s",
            service,
            intent.role,
            intent.entity_id,
            err,
        )
        return False
    return True


def _sample(hass: HomeAssistant, binding: ClimateBinding) -> SensorSample:
    assert binding.entity_id is not None
    state = hass.states.get(binding.entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return SensorSample(binding.role, None, stale=True, entity_id=binding.entity_id)
    if binding.role == ROLE_FLOAT and state.state in ("on", "off"):
        return SensorSample(
            binding.role,
            1.0 if state.state == "on" else 0.0,
            entity_id=binding.entity_id,
        )
    try:
        return SensorSample(
            binding.role, float(state.state), entity_id=binding.entity_id
        )
    except (TypeError, ValueError):
        return SensorSample(binding.role, None, stale=True, entity_id=binding.entity_id)


def _observed_lights(
    hass: HomeAssistant,
    bindings: list[ClimateBinding],
    light_since: dict[str, str],
    now: datetime,
) -> ObservedState:
    sinces: list[datetime] = []
    light_on = False
    for binding in bindings:
        if binding.role != ROLE_LIGHT or not binding.entity_id:
            continue
        state = hass.states.get(binding.entity_id)
        if state is not None and state.state in _ON_STATES:
            light_on = True
            stamp = light_since.get(binding.entity_id)
            if stamp is None:
                stamp = now.isoformat()
                light_since[binding.entity_id] = stamp
            sinces.append(datetime.fromisoformat(stamp))
        else:
            light_since.pop(binding.entity_id, None)
    since = min(sinces) if sinces else None
    return ObservedState(light_on=light_on, light_on_since=since)
