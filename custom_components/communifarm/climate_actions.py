"""Home Assistant adapter for climate layout, ticks, and entity commands."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_CLIMATE_SETTINGS_UPDATED, SIGNAL_CLIMATE_UPDATED
from .dashboard.provisioner import async_provision_dashboard
from .domain.climate import (
    CLIMATE_ROLES,
    ROLE_CULTURE_ACTIVITY,
    ROLE_FLOAT,
    ROLE_LIGHT,
    ROLE_OCCUPANCY,
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
    RowControlContext,
    decide_control,
    format_decision_summary,
    resolved_row_fan_cycle,
)
from .domain.climate_drawing import drawing_devices, drawing_entity_id
from .domain.climate_settings import (
    NODE_SETTING_SPECS,
    SCOPE_NODE,
    SCOPE_ROW,
    SETTING_ROW_FAN_OFF_MINUTES,
    SETTING_ROW_FAN_ON_MINUTES,
)
from .domain.models import CommunifarmState
from .domain.validation import ValidationError
from .settings_access import async_require_automation_settings_access
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
    await async_refresh_climate_settings_editor(hass, entry_id)
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
    zone_id: str | None = None,
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
                zone_id=zone_id.strip() if zone_id else None,
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
    presence_last_seen: dict[str, str] = bucket.setdefault(
        "climate_presence_last_seen", {}
    )
    samples_by_node: dict[str, list] = {}
    observed_by_node: dict[str, ObservedState] = {}
    for node in nodes:
        node_bindings = bindings_by_node.get(node.id, [])
        samples_by_node[node.id] = [
            _sample(hass, binding)
            for binding in node_bindings
            if binding.role in SENSOR_ROLES and binding.entity_id
        ]
        observed_by_node[node.id] = _observed_state(
            hass,
            node.id,
            node_bindings,
            light_since,
            presence_last_seen,
            now,
        )

    row_contexts = await _build_row_contexts(hass, entry_id, nodes)
    decision = decide_control(
        nodes,
        samples_by_node,
        bindings_by_node,
        observed_by_node,
        now,
        row_contexts,
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
    if binding.role in {ROLE_FLOAT, ROLE_OCCUPANCY, ROLE_CULTURE_ACTIVITY} and state.state in (
        "on",
        "off",
    ):
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


def _observed_state(
    hass: HomeAssistant,
    node_id: str,
    bindings: list[ClimateBinding],
    light_since: dict[str, str],
    presence_last_seen: dict[str, str],
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
    occupied = any(
        binding.role == ROLE_OCCUPANCY
        and binding.entity_id
        and (state := hass.states.get(binding.entity_id)) is not None
        and state.state in _ON_STATES
        for binding in bindings
    )
    if occupied:
        presence_last_seen[node_id] = now.isoformat()
    stamp = presence_last_seen.get(node_id)
    last_occupied_at = datetime.fromisoformat(stamp) if stamp else None
    return ObservedState(
        light_on=light_on,
        light_on_since=since,
        occupied=occupied,
        last_occupied_at=last_occupied_at,
    )


async def _build_row_contexts(
    hass: HomeAssistant,
    entry_id: str,
    nodes: list[ClimateNode],
) -> list[RowControlContext]:
    """Resolve zone → climate and batch → culture → variety for row fans."""
    bucket = hass.data[DOMAIN][entry_id]
    batch_repo = bucket.get("batch_repository")
    location_repo = bucket.get("location_repository")
    culture_repo = bucket.get("culture_repository")
    if batch_repo is None or location_repo is None or culture_repo is None:
        return []

    state = _state(hass, entry_id)
    areas = await location_repo.async_list_areas(state.site.id)
    zones = await location_repo.async_list_zones(state.site.id)
    area_by_id = {area.id: area for area in areas}
    zone_to_node = {
        zone.id: area_by_id[zone.area_id].climate_id
        for zone in zones
        if zone.area_id in area_by_id and area_by_id[zone.area_id].climate_id
    }
    valid_nodes = {node.id for node in nodes}
    contexts: list[RowControlContext] = []
    for batch in await batch_repo.async_list_batches():
        if batch.status != "active" or not batch.zone_id:
            continue
        node_id = zone_to_node.get(batch.zone_id)
        if not node_id or node_id not in valid_nodes:
            continue
        variety_slug = None
        if batch.culture_id:
            culture = await culture_repo.async_get_culture(batch.culture_id)
            if culture is not None and culture.variety_id:
                variety = await culture_repo.async_get_variety(culture.variety_id)
                variety_slug = variety.slug if variety is not None else None
        overrides = await _repo(hass, entry_id).async_get_setting_overrides(
            SCOPE_ROW, batch.zone_id
        )
        contexts.append(
            RowControlContext(
                node_id=node_id,
                zone_id=batch.zone_id,
                lifecycle_phase=batch.lifecycle_phase,
                variety_slug=variety_slug,
                fan_on_minutes=overrides.get(SETTING_ROW_FAN_ON_MINUTES),
                fan_off_minutes=overrides.get(SETTING_ROW_FAN_OFF_MINUTES),
            )
        )
    return contexts


async def async_refresh_climate_settings_editor(
    hass: HomeAssistant, entry_id: str
) -> None:
    """Refresh static editor entities from effective defaults plus overrides."""
    bucket = hass.data[DOMAIN][entry_id]
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    nodes = await repo.async_list_nodes(state.site.id)
    controlled = [node for node in nodes if node.control_enabled]
    node_options = {
        f"{node.name} ({node.kind.replace('_', ' ')})": node.id
        for node in controlled
    }
    selected_node = bucket.get("climate_settings_node_id")
    if selected_node not in node_options.values():
        selected_node = controlled[0].id if controlled else None
        bucket["climate_settings_node_id"] = selected_node

    location_repo = bucket["location_repository"]
    areas = await location_repo.async_list_areas(state.site.id)
    zones = await location_repo.async_list_zones(state.site.id)
    area_by_id = {area.id: area for area in areas}
    controlled_ids = {node.id for node in controlled}
    row_options = {
        f"{area_by_id[zone.area_id].name} / {zone.name}": zone.id
        for zone in zones
        if zone.area_id in area_by_id
        and area_by_id[zone.area_id].climate_id in controlled_ids
    }
    selected_row = bucket.get("climate_settings_row_id")
    if selected_row not in row_options.values():
        selected_row = next(iter(row_options.values()), None)
        bucket["climate_settings_row_id"] = selected_row

    values: dict[str, float] = {}
    selected = next((node for node in nodes if node.id == selected_node), None)
    node_overrides = (
        await repo.async_get_setting_overrides(SCOPE_NODE, selected_node)
        if selected_node
        else {}
    )
    if selected is not None:
        for spec in NODE_SETTING_SPECS:
            raw = getattr(selected, spec.key)
            values[spec.key] = 0.0 if raw is None else float(raw)

    row_context = next(
        (
            context
            for context in await _build_row_contexts(hass, entry_id, nodes)
            if context.zone_id == selected_row
        ),
        None,
    )
    row_overrides = (
        await repo.async_get_setting_overrides(SCOPE_ROW, selected_row)
        if selected_row
        else {}
    )
    if row_context is None:
        row_context = RowControlContext(
            "",
            selected_row or "",
            "fruiting",
            fan_on_minutes=row_overrides.get(SETTING_ROW_FAN_ON_MINUTES),
            fan_off_minutes=row_overrides.get(SETTING_ROW_FAN_OFF_MINUTES),
        )
    fan_on, fan_off = resolved_row_fan_cycle(row_context)
    values[SETTING_ROW_FAN_ON_MINUTES] = fan_on
    values[SETTING_ROW_FAN_OFF_MINUTES] = fan_off

    bucket["climate_settings_node_options"] = node_options
    bucket["climate_settings_row_options"] = row_options
    bucket["climate_settings_values"] = values
    bucket["climate_settings_override_keys"] = {
        SCOPE_NODE: set(node_overrides),
        SCOPE_ROW: set(row_overrides),
    }
    async_dispatcher_send(hass, SIGNAL_CLIMATE_SETTINGS_UPDATED, entry_id)


async def async_select_climate_settings_scope(
    hass: HomeAssistant, entry_id: str, scope: str, scope_id: str
) -> None:
    bucket = hass.data[DOMAIN][entry_id]
    key = "climate_settings_node_id" if scope == SCOPE_NODE else "climate_settings_row_id"
    bucket[key] = scope_id
    await async_refresh_climate_settings_editor(hass, entry_id)


async def async_set_climate_setting(
    hass: HomeAssistant,
    entry_id: str,
    *,
    scope: str,
    setting_key: str,
    value: float,
    context: Context | None,
) -> None:
    await async_require_automation_settings_access(hass, context)
    bucket = hass.data[DOMAIN][entry_id]
    id_key = "climate_settings_node_id" if scope == SCOPE_NODE else "climate_settings_row_id"
    scope_id = bucket.get(id_key)
    if not scope_id:
        raise HomeAssistantError(f"No {scope} selected")
    await _repo(hass, entry_id).async_set_setting_override(
        scope, scope_id, setting_key, value
    )
    await async_refresh_climate_settings_editor(hass, entry_id)
    await async_tick_climate(hass, entry_id)


async def async_reset_climate_settings(
    hass: HomeAssistant,
    entry_id: str,
    *,
    scope: str,
    context: Context | None,
) -> None:
    await async_require_automation_settings_access(hass, context)
    bucket = hass.data[DOMAIN][entry_id]
    id_key = "climate_settings_node_id" if scope == SCOPE_NODE else "climate_settings_row_id"
    scope_id = bucket.get(id_key)
    if not scope_id:
        raise HomeAssistantError(f"No {scope} selected")
    await _repo(hass, entry_id).async_clear_setting_overrides(scope, scope_id)
    await async_refresh_climate_settings_editor(hass, entry_id)
    await async_tick_climate(hass, entry_id)
