"""Text platform — variety name draft for catalog CRUD."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([CommunifarmVarietyNameText(entry.entry_id)])


class CommunifarmVarietyNameText(TextEntity):
    _attr_has_entity_name = True
    _attr_name = "New variety name"
    _attr_unique_id = "communifarm_variety_name"
    _attr_icon = "mdi:mushroom"
    _attr_native_min = 0
    _attr_native_max = 64
    _attr_mode = "text"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "text.communifarm_variety_name"
        self._value = ""

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["variety_name_draft"] = self._value

    @property
    def native_value(self) -> str | None:
        return self._value

    async def async_set_value(self, value: str) -> None:
        self._value = value or ""
        self.hass.data[DOMAIN][self._entry_id]["variety_name_draft"] = self._value
        self.async_write_ha_state()
