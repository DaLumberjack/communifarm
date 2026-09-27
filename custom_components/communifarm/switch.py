"""Switch platform — allowlisted proxy for a bound switch entity."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ROLE_SWITCH
from .dashboard.provisioner import resolve_bindings
from .domain.models import CommunifarmState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Communifarm switch proxies."""
    state: CommunifarmState = hass.data[DOMAIN][entry.entry_id]["state"]
    if state.binding_for(ROLE_SWITCH) is None:
        return
    async_add_entities([CommunifarmAllowlistedSwitch(entry.entry_id)])


class CommunifarmAllowlistedSwitch(SwitchEntity):
    """Proxy switch that only forwards to the configured safe underlying entity."""

    _attr_has_entity_name = True
    _attr_name = "Allowlisted switch"
    _attr_unique_id = "communifarm_allowlisted_switch"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "switch.communifarm_allowlisted_switch"

    def _target_entity_id(self) -> str | None:
        state: CommunifarmState = self.hass.data[DOMAIN][self._entry_id]["state"]
        resolved = resolve_bindings(self.hass, state)
        return resolved.get(ROLE_SWITCH)

    @property
    def available(self) -> bool:
        entity_id = self._target_entity_id()
        if not entity_id:
            return False
        return self.hass.states.get(entity_id) is not None

    @property
    def is_on(self) -> bool | None:
        entity_id = self._target_entity_id()
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        return state.state == STATE_ON

    async def async_turn_on(self, **kwargs) -> None:
        entity_id = self._target_entity_id()
        if not entity_id:
            return
        await self.hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": entity_id},
            blocking=True,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        entity_id = self._target_entity_id()
        if not entity_id:
            return
        await self.hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )
        self.async_write_ha_state()
