"""The Communifarm integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ALLOWED_BATCH_TRANSITIONS,
    DOMAIN,
    PLATFORMS,
    SERVICE_TRANSITION_BATCH,
)
from .dashboard.provisioner import async_provision_dashboard
from .domain.models import CommunifarmState
from .storage.repository import CommunifarmRepository

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

TRANSITION_SCHEMA = vol.Schema(
    {
        vol.Required("stage"): vol.In(
            {stage for stages in ALLOWED_BATCH_TRANSITIONS.values() for stage in stages}
            | set(ALLOWED_BATCH_TRANSITIONS)
        )
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Communifarm (config entry only)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Communifarm from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    repo = CommunifarmRepository(hass)

    state_data = entry.data.get("state")
    if state_data:
        state = CommunifarmState.from_dict(state_data)
        await repo.async_save(state)
    else:
        state = await repo.async_load()
        if state is None:
            _LOGGER.error("Communifarm config entry has no state")
            return False

    hass.data[DOMAIN][entry.entry_id] = {
        "repository": repo,
        "state": state,
    }

    dashboard_url = await async_provision_dashboard(hass, state)
    hass.data[DOMAIN][entry.entry_id]["dashboard_url"] = dashboard_url

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(p) for p in PLATFORMS]
    )

    async def async_transition_batch(call: ServiceCall) -> None:
        new_stage = call.data["stage"]
        stored = hass.data[DOMAIN][entry.entry_id]["state"]
        assert isinstance(stored, CommunifarmState)
        timestamp = datetime.now(tz=UTC).isoformat()
        stored.batch.transition(new_stage, timestamp)
        await repo.async_save(stored)
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "state": stored.to_dict()}
        )
        await hass.config_entries.async_reload(entry.entry_id)

    if not hass.services.has_service(DOMAIN, SERVICE_TRANSITION_BATCH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TRANSITION_BATCH,
            async_transition_batch,
            schema=TRANSITION_SCHEMA,
        )

    # Do not add_update_listener here: profile number saves update entry.data and
    # would reload the integration on every ±1°C/±1% nudge from the dashboard.
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Communifarm (call explicitly from options flow when added)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Communifarm config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform(p) for p in PLATFORMS]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not any(key != "dashboard_config" for key in hass.data.get(DOMAIN, {})):
            if hass.services.has_service(DOMAIN, SERVICE_TRANSITION_BATCH):
                hass.services.async_remove(DOMAIN, SERVICE_TRANSITION_BATCH)
    return unload_ok
