"""Switch platform — allowlisted proxies for bound switch entities."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_LC_STIR_PLATE,
    ROLE_LC_STIR_PLATE,
    ROLE_SWITCH,
)
from .dashboard.provisioner import resolve_bindings
from .domain.culture import (
    MILESTONE_LC_STIR_STARTED,
    MILESTONE_LC_STIR_STOPPED,
)
from .domain.models import CommunifarmState
from .storage.culture_repository import CultureRepository

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Communifarm switch proxies."""
    state: CommunifarmState = hass.data[DOMAIN][entry.entry_id]["state"]
    entities: list[SwitchEntity] = []
    if state.binding_for(ROLE_SWITCH) is not None:
        entities.append(CommunifarmAllowlistedSwitch(entry.entry_id))
    if state.binding_for(ROLE_LC_STIR_PLATE) is not None:
        entities.append(CommunifarmLcStirPlateSwitch(entry.entry_id))
    if entities:
        async_add_entities(entities)


class _BoundSwitchProxy(SwitchEntity):
    """Shared proxy that forwards to a role-bound underlying switch."""

    _attr_has_entity_name = True
    _role: str

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    def _target_entity_id(self) -> str | None:
        state: CommunifarmState = self.hass.data[DOMAIN][self._entry_id]["state"]
        resolved = resolve_bindings(self.hass, state)
        return resolved.get(self._role)

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
        await self._async_after_toggle(True, entity_id)
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
        await self._async_after_toggle(False, entity_id)
        self.async_write_ha_state()

    async def _async_after_toggle(self, turned_on: bool, target_entity_id: str) -> None:
        """Optional hook after forwarding on/off."""
        return None


class CommunifarmAllowlistedSwitch(_BoundSwitchProxy):
    """Proxy switch that only forwards to the configured safe underlying entity."""

    _attr_name = "Allowlisted switch"
    _attr_unique_id = "communifarm_allowlisted_switch"
    _role = ROLE_SWITCH

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id)
        self.entity_id = "switch.communifarm_allowlisted_switch"


class CommunifarmLcStirPlateSwitch(_BoundSwitchProxy):
    """Bound LC magnetic stir plate — records CF media milestones when toggled."""

    _attr_name = "LC stir plate"
    _attr_unique_id = "communifarm_lc_stir_plate"
    _attr_icon = "mdi:rotate-3d-variant"
    _role = ROLE_LC_STIR_PLATE

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id)
        self.entity_id = ENTITY_LC_STIR_PLATE

    async def _async_after_toggle(self, turned_on: bool, target_entity_id: str) -> None:
        bucket = self.hass.data[DOMAIN][self._entry_id]
        media_batch_id = bucket.get("active_media_batch_id")
        repo: CultureRepository | None = bucket.get("culture_repository")
        if not media_batch_id or repo is None:
            _LOGGER.warning(
                "LC stir plate toggled but no active_media_batch_id — CF milestone skipped"
            )
            return
        event_type = (
            MILESTONE_LC_STIR_STARTED if turned_on else MILESTONE_LC_STIR_STOPPED
        )
        when = datetime.now(tz=UTC).isoformat()
        await repo.async_insert_media_milestone(
            media_batch_id=media_batch_id,
            event_type=event_type,
            recorded_at=when,
            detail={
                "source_entity_id": target_entity_id,
                "cf_entity_id": ENTITY_LC_STIR_PLATE,
                "bound_role": ROLE_LC_STIR_PLATE,
            },
        )
        _LOGGER.info(
            "Recorded %s for media %s via %s",
            event_type,
            media_batch_id,
            ENTITY_LC_STIR_PLATE,
        )
