"""Select platform — heat treatment method for the active batch."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .domain.batch_milestones import HEAT_PASTEURIZED, HEAT_STERILIZED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([CommunifarmHeatTreatmentSelect(entry.entry_id)])


class CommunifarmHeatTreatmentSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Heat treatment method"
    _attr_unique_id = "communifarm_heat_treatment"
    _attr_icon = "mdi:thermometer-lines"
    _attr_options = [HEAT_PASTEURIZED, HEAT_STERILIZED]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_heat_treatment"
        self._current = HEAT_PASTEURIZED

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["heat_treatment"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["heat_treatment"] = option
        self.async_write_ha_state()
