"""Binary sensor platform — preset float on the climate schematic."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .climate_entities import drawing_binary_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the float drawn on the general room."""
    del hass
    entities: list[BinarySensorEntity] = drawing_binary_entities(entry.entry_id)
    if entities:
        async_add_entities(entities)
