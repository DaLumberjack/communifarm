"""Sensor platform for Communifarm."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .domain.models import CommunifarmState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Communifarm sensors."""
    state: CommunifarmState = hass.data[DOMAIN][entry.entry_id]["state"]
    async_add_entities(
        [
            CommunifarmBatchStageSensor(entry.entry_id, state),
            CommunifarmEnvironmentStatusSensor(entry.entry_id, state),
        ]
    )


class CommunifarmBatchStageSensor(SensorEntity):
    """Expose the current production batch stage."""

    _attr_has_entity_name = True
    _attr_name = "Batch stage"
    _attr_unique_id = "communifarm_batch_stage"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        self._entry_id = entry_id
        self._state = state
        self.entity_id = "sensor.communifarm_batch_stage"

    @property
    def native_value(self) -> str:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        return runtime.batch.stage

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        return {
            "batch_id": runtime.batch.id,
            "batch_name": runtime.batch.name,
            "event_count": str(len(runtime.batch.events)),
        }


class CommunifarmEnvironmentStatusSensor(SensorEntity):
    """Simple environment health status for the dashboard."""

    _attr_has_entity_name = True
    _attr_name = "Environment status"
    _attr_unique_id = "communifarm_environment_status"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        self._entry_id = entry_id
        self._state = state
        self.entity_id = "sensor.communifarm_environment_status"

    @property
    def native_value(self) -> str:
        return "ok"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        return {
            "site": runtime.site.name,
            "environment": runtime.environment.name,
        }
