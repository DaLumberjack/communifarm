"""Placement layout and batch location application helpers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_BATCH_UPDATED, SIGNAL_WEIGH_SESSION_UPDATED
from .domain.location import suggest_area_kind_for_production_stage
from .domain.models import CommunifarmState
from .storage.batch_repository import BatchRepository
from .storage.location_repository import LocationRepository

_LOGGER = logging.getLogger(__name__)


def _batch_repo(hass: HomeAssistant, entry_id: str) -> BatchRepository:
    repo = hass.data[DOMAIN][entry_id].get("batch_repository")
    if repo is None:
        raise HomeAssistantError("Batch repository is not available")
    return repo


def _location_repo(hass: HomeAssistant, entry_id: str) -> LocationRepository:
    repo = hass.data[DOMAIN][entry_id].get("location_repository")
    if repo is None:
        raise HomeAssistantError("Location repository is not available")
    return repo


def _state(hass: HomeAssistant, entry_id: str) -> CommunifarmState:
    return hass.data[DOMAIN][entry_id]["state"]


def _notify_batch(hass: HomeAssistant, entry_id: str) -> None:
    async_dispatcher_send(hass, SIGNAL_BATCH_UPDATED, entry_id)
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)


async def async_ensure_default_layout(
    hass: HomeAssistant, entry_id: str
) -> dict[str, Any]:
    state = _state(hass, entry_id)
    loc_repo = _location_repo(hass, entry_id)
    areas, zones = await loc_repo.async_ensure_default_layout(state.site.id)
    summary = {
        "site_id": state.site.id,
        "area_count": len(areas),
        "zone_count": len(zones),
        "areas": [
            {
                "id": a.id,
                "name": a.name,
                "area_kind": a.area_kind,
                "slot_kind": a.slot_kind,
                "slot_count": a.slot_count,
            }
            for a in areas
        ],
    }
    _LOGGER.info(
        "Placement layout ready for site %s: %s areas / %s zones",
        state.site.id,
        len(areas),
        len(zones),
    )
    return summary


async def async_set_batch_location(
    hass: HomeAssistant,
    entry_id: str,
    *,
    zone_id: str,
    batch_id: str | None = None,
) -> str:
    state = _state(hass, entry_id)
    batch_repo = _batch_repo(hass, entry_id)
    loc_repo = _location_repo(hass, entry_id)

    if not zone_id or not str(zone_id).strip():
        raise HomeAssistantError("zone_id is required")
    zone = await loc_repo.async_get_zone(str(zone_id).strip())
    if zone is None:
        raise HomeAssistantError(f"unknown zone_id: {zone_id}")

    resolved_batch = batch_id or state.batch.id
    batch = await batch_repo.async_get_batch(resolved_batch)
    if batch is None:
        raise HomeAssistantError(f"unknown batch_id: {resolved_batch}")

    area = await loc_repo.async_get_area(zone.area_id)
    suggested = suggest_area_kind_for_production_stage(batch.lifecycle_phase)
    warning: str | None = None
    if (
        suggested
        and area is not None
        and area.area_kind != suggested
    ):
        warning = (
            f"soft warning: stage {batch.lifecycle_phase} usually uses "
            f"{suggested}; zone is in {area.area_kind}"
        )
        _LOGGER.warning("%s (batch %s zone %s)", warning, batch.id, zone.id)

    await batch_repo.async_set_zone(batch.id, zone.id)
    _LOGGER.info(
        "Batch %s placed in zone %s (%s / %s)",
        batch.id,
        zone.id,
        area.name if area else zone.area_id,
        zone.name,
    )
    _notify_batch(hass, entry_id)
    return zone.id


async def async_list_locations(
    hass: HomeAssistant, entry_id: str
) -> dict[str, Any]:
    state = _state(hass, entry_id)
    loc_repo = _location_repo(hass, entry_id)
    areas, zones = await loc_repo.async_ensure_default_layout(state.site.id)
    by_area: dict[str, list[dict[str, Any]]] = {a.id: [] for a in areas}
    for zone in zones:
        by_area.setdefault(zone.area_id, []).append(
            {
                "id": zone.id,
                "name": zone.name,
                "slot_kind": zone.slot_kind,
                "slot_index": zone.slot_index,
            }
        )
    return {
        "site_id": state.site.id,
        "areas": [
            {
                "id": a.id,
                "name": a.name,
                "area_kind": a.area_kind,
                "slot_kind": a.slot_kind,
                "slot_count": a.slot_count,
                "zones": by_area.get(a.id, []),
            }
            for a in areas
        ],
        "zone_count": len(zones),
    }


async def async_resolve_location_attrs(
    hass: HomeAssistant,
    entry_id: str,
    *,
    zone_id: str | None,
    lifecycle_phase: str,
) -> dict[str, Any]:
    """Attrs for production status sensor: zone + area + soft stage hint."""
    attrs: dict[str, Any] = {
        "zone_id": zone_id,
        "area_id": None,
        "area_name": None,
        "area_kind": None,
        "zone_name": None,
        "suggested_area_kind": suggest_area_kind_for_production_stage(lifecycle_phase),
        "location_warning": None,
    }
    if not zone_id:
        return attrs
    loc_repo = hass.data[DOMAIN][entry_id].get("location_repository")
    if loc_repo is None:
        return attrs
    zone = await loc_repo.async_get_zone(zone_id)
    if zone is None:
        attrs["location_warning"] = f"unknown zone_id: {zone_id}"
        return attrs
    area = await loc_repo.async_get_area(zone.area_id)
    attrs["zone_name"] = zone.name
    attrs["area_id"] = zone.area_id
    if area is not None:
        attrs["area_name"] = area.name
        attrs["area_kind"] = area.area_kind
        suggested = attrs["suggested_area_kind"]
        if suggested and area.area_kind != suggested:
            attrs["location_warning"] = (
                f"stage {lifecycle_phase} usually uses {suggested}; "
                f"batch is in {area.area_kind}"
            )
    return attrs
