"""Number platform for Communifarm profile targets."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .domain.models import CommunifarmState
from .storage.repository import CommunifarmRepository


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Communifarm number entities."""
    state: CommunifarmState = hass.data[DOMAIN][entry.entry_id]["state"]
    repo: CommunifarmRepository = hass.data[DOMAIN][entry.entry_id]["repository"]
    async_add_entities(
        [
            CommunifarmTemperatureTarget(entry, state, repo),
            CommunifarmHumidityTarget(entry, state, repo),
        ]
    )


class _ProfileNumber(NumberEntity):
    _attr_has_entity_name = True
    # Slider is easier to nudge from the managed dashboard than a settings dig.
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        entry: ConfigEntry,
        state: CommunifarmState,
        repo: CommunifarmRepository,
    ) -> None:
        self._entry = entry
        self._state = state
        self._repo = repo

    def _runtime(self) -> CommunifarmState:
        return self.hass.data[DOMAIN][self._entry.entry_id]["state"]

    async def _async_persist(self) -> None:
        runtime = self._runtime()
        await self._repo.async_save(runtime)
        self.hass.config_entries.async_update_entry(
            self._entry, data={**self._entry.data, "state": runtime.to_dict()}
        )


class CommunifarmTemperatureTarget(_ProfileNumber):
    """Temperature target for the active profile."""

    _attr_name = "Temperature target"
    _attr_unique_id = "communifarm_temperature_target"
    _attr_icon = "mdi:thermometer"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = -40.0
    _attr_native_max_value = 80.0
    _attr_native_step = 0.5

    def __init__(
        self,
        entry: ConfigEntry,
        state: CommunifarmState,
        repo: CommunifarmRepository,
    ) -> None:
        super().__init__(entry, state, repo)
        self.entity_id = "number.communifarm_temperature_target"

    @property
    def native_value(self) -> float:
        return self._runtime().profile.temperature_target

    async def async_set_native_value(self, value: float) -> None:
        runtime = self._runtime()
        runtime.profile.temperature_target = float(value)
        runtime.profile.validate()
        await self._async_persist()
        self.async_write_ha_state()


class CommunifarmHumidityTarget(_ProfileNumber):
    """Humidity target for the active profile."""

    _attr_name = "Humidity target"
    _attr_unique_id = "communifarm_humidity_target"
    _attr_icon = "mdi:water-percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0

    def __init__(
        self,
        entry: ConfigEntry,
        state: CommunifarmState,
        repo: CommunifarmRepository,
    ) -> None:
        super().__init__(entry, state, repo)
        self.entity_id = "number.communifarm_humidity_target"

    @property
    def native_value(self) -> float:
        return self._runtime().profile.humidity_target

    async def async_set_native_value(self, value: float) -> None:
        runtime = self._runtime()
        runtime.profile.humidity_target = float(value)
        runtime.profile.validate()
        await self._async_persist()
        self.async_write_ha_state()
