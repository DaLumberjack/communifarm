"""Home Assistant adapter for ops scheduling tick, queue sensor, and notifications."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_OPS_UPDATED
from .domain.batch_milestones import BATCH_STATUS_COMPLETE
from .domain.climate import ROLE_LIGHT
from .domain.climate_control import ObservedState
from .domain.container import CONTAINER_STATUS_COMPLETE
from .domain.models import CommunifarmState
from .domain.ops_schedule import AlarmEvent, OpsQueue, OpsSubject, evaluate_ops
from .domain.production import (
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INCUBATING,
    STAGE_INOCULATED,
)

_LOGGER = logging.getLogger(__name__)

_ON_STATES = frozenset({"on", "true", "1"})


def _state(hass: HomeAssistant, entry_id: str) -> CommunifarmState:
    return hass.data[DOMAIN][entry_id]["state"]


def _publish(hass: HomeAssistant, entry_id: str, snapshot: dict[str, Any]) -> None:
    hass.data[DOMAIN][entry_id]["ops_snapshot"] = snapshot
    async_dispatcher_send(hass, SIGNAL_OPS_UPDATED, entry_id)


async def _async_notify_alarms(
    hass: HomeAssistant, alarms: list[AlarmEvent]
) -> None:
    for alarm in alarms:
        title = f"Communifarm {alarm.priority.upper()}: {alarm.code}"
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": alarm.message,
                "notification_id": f"communifarm_ops_{alarm.id}",
            },
            blocking=False,
        )


async def _async_light_observations(
    hass: HomeAssistant, entry_id: str, now: datetime
) -> dict[str, ObservedState]:
    """Read light facts after climate tick (same ``climate_light_since`` keys)."""
    bucket = hass.data[DOMAIN][entry_id]
    light_since: dict[str, str] = bucket.setdefault("climate_light_since", {})
    repo = bucket.get("climate_repository")
    if repo is None:
        return {}

    state = _state(hass, entry_id)
    bindings = await repo.async_list_bindings(state.site.id)
    by_node: dict[str, list] = {}
    for binding in bindings:
        if binding.role != ROLE_LIGHT or not binding.entity_id:
            continue
        by_node.setdefault(binding.node_id, []).append(binding)

    observed: dict[str, ObservedState] = {}
    for node_id, node_bindings in by_node.items():
        sinces: list[datetime] = []
        light_on = False
        for binding in node_bindings:
            ha_state = hass.states.get(binding.entity_id)
            if ha_state is not None and str(ha_state.state).lower() in _ON_STATES:
                light_on = True
                stamp = light_since.get(binding.entity_id)
                if stamp is None:
                    # Climate tick should have stamped; fall back if ops ran alone.
                    stamp = now.isoformat()
                    light_since[binding.entity_id] = stamp
                try:
                    sinces.append(datetime.fromisoformat(stamp))
                except ValueError:
                    pass
        observed[node_id] = ObservedState(
            light_on=light_on,
            light_on_since=min(sinces) if sinces else None,
        )
    return observed


async def _async_subjects(hass: HomeAssistant, entry_id: str) -> list[OpsSubject]:
    bucket = hass.data[DOMAIN][entry_id]
    cont_repo = bucket.get("container_repository")
    batch_repo = bucket.get("batch_repository")
    loc_repo = bucket.get("location_repository")
    if cont_repo is None or batch_repo is None:
        return []

    state = _state(hass, entry_id)
    areas: dict[str, Any] = {}
    zones: dict[str, Any] = {}
    if loc_repo is not None:
        await loc_repo.async_ensure_default_layout(state.site.id)
        areas = {a.id: a for a in await loc_repo.async_list_areas(state.site.id)}
        zones = {z.id: z for z in await loc_repo.async_list_zones(state.site.id)}

    batches = {b.id: b for b in await batch_repo.async_list_batches()}
    subjects: list[OpsSubject] = []
    containers = await cont_repo.async_list_active_placed()
    if not containers:
        # Include non-complete containers even without zone for stage dwell.
        all_for_site: list = []
        for batch in batches.values():
            if batch.status == BATCH_STATUS_COMPLETE:
                continue
            all_for_site.extend(await cont_repo.async_list_for_batch(batch.id))
        containers = [
            c for c in all_for_site if c.status != CONTAINER_STATUS_COMPLETE
        ]

    seen_batches: set[str] = set()
    for cont in containers:
        batch = batches.get(cont.batch_id)
        area_kind = None
        if cont.zone_id and cont.zone_id in zones:
            area = areas.get(zones[cont.zone_id].area_id)
            if area is not None:
                area_kind = area.area_kind
        subjects.append(
            OpsSubject(
                subject_id=cont.id,
                lifecycle_phase=cont.lifecycle_phase,
                phase_changed_at=cont.phase_changed_at,
                created_at=cont.created_at,
                expected_check_at=batch.expected_check_at if batch else None,
                area_kind=area_kind,
                zone_id=cont.zone_id,
            )
        )
        seen_batches.add(cont.batch_id)

    # Batches in production stages without containers still get projections.
    for batch in batches.values():
        if batch.id in seen_batches or batch.status == BATCH_STATUS_COMPLETE:
            continue
        if batch.lifecycle_phase in (
            STAGE_INOCULATED,
            STAGE_INCUBATING,
            STAGE_FRUITING,
            STAGE_HARVESTING,
        ):
            area_kind = None
            if batch.zone_id and batch.zone_id in zones:
                area = areas.get(zones[batch.zone_id].area_id)
                if area is not None:
                    area_kind = area.area_kind
            subjects.append(
                OpsSubject(
                    subject_id=batch.id,
                    lifecycle_phase=batch.lifecycle_phase,
                    phase_changed_at=batch.phase_changed_at,
                    created_at=batch.created_at,
                    expected_check_at=batch.expected_check_at,
                    area_kind=area_kind,
                    zone_id=batch.zone_id,
                )
            )
    return subjects


async def async_tick_ops(hass: HomeAssistant, entry_id: str) -> OpsQueue:
    """Evaluate ops queue, publish sensor snapshot, create notifications."""
    now = datetime.now(tz=UTC)
    subjects = await _async_subjects(hass, entry_id)
    lights = await _async_light_observations(hass, entry_id, now)
    queue = evaluate_ops(
        subjects=subjects,
        light_observations=lights,
        now=now,
    )
    snapshot = queue.to_dict()
    _publish(hass, entry_id, snapshot)
    if queue.alarms:
        await _async_notify_alarms(hass, queue.alarms)
        _LOGGER.debug(
            "Ops tick: %s alarms, %s projected moves",
            len(queue.alarms),
            len(queue.projected_moves),
        )
    return queue
