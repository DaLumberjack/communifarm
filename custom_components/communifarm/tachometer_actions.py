"""Home Assistant adapter for manual vent tachometer logging."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_TACHOMETER_UPDATED
from .domain.models import CommunifarmState
from .domain.tachometer import reading_to_dict, vent_to_dict
from .domain.validation import ValidationError
from .storage.tachometer_repository import TachometerRepository

_LOGGER = logging.getLogger(__name__)


def _repo(hass: HomeAssistant, entry_id: str) -> TachometerRepository:
    repo = hass.data[DOMAIN][entry_id].get("tachometer_repository")
    if repo is None:
        raise HomeAssistantError("Tachometer repository is not available")
    return repo


def _state(hass: HomeAssistant, entry_id: str) -> CommunifarmState:
    return hass.data[DOMAIN][entry_id]["state"]


async def _publish(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    snapshot = await repo.async_snapshot(state.site.id)
    hass.data[DOMAIN][entry_id]["tachometer_snapshot"] = snapshot
    async_dispatcher_send(hass, SIGNAL_TACHOMETER_UPDATED, entry_id)
    return snapshot


async def async_upsert_air_vent(
    hass: HomeAssistant,
    entry_id: str,
    *,
    label: str,
    vent_role: str = "other",
    climate_node_id: str | None = None,
    notes: str | None = None,
    vent_id: str | None = None,
) -> dict[str, Any]:
    """Create or update a labeled vent for air-exchange logging."""
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    try:
        vent = await repo.async_upsert_vent(
            site_id=state.site.id,
            label=label,
            vent_role=vent_role,
            climate_node_id=climate_node_id,
            notes=notes,
            vent_id=vent_id,
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    snapshot = await _publish(hass, entry_id)
    return {"vent": vent_to_dict(vent), "snapshot": snapshot}


async def async_record_tachometer(
    hass: HomeAssistant,
    entry_id: str,
    *,
    value: float,
    unit: str = "rpm",
    vent_id: str | None = None,
    vent_label: str | None = None,
    recorded_at: str | None = None,
    notes: str | None = None,
    vent_role: str = "other",
    climate_node_id: str | None = None,
) -> dict[str, Any]:
    """Append a manual tachometer / airflow reading for a labeled vent."""
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    try:
        reading = await repo.async_record_reading(
            site_id=state.site.id,
            value=value,
            unit=unit,
            vent_id=vent_id,
            vent_label=vent_label,
            recorded_at=recorded_at,
            notes=notes,
            vent_role=vent_role,
            climate_node_id=climate_node_id,
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    snapshot = await _publish(hass, entry_id)
    _LOGGER.info(
        "Recorded tachometer %.2f %s for %s",
        reading.value,
        reading.unit,
        reading.vent_label,
    )
    return {"reading": reading_to_dict(reading), "snapshot": snapshot}


async def async_refresh_tachometer_snapshot(
    hass: HomeAssistant, entry_id: str
) -> dict[str, Any]:
    """Rebuild the dashboard snapshot without writing."""
    return await _publish(hass, entry_id)
