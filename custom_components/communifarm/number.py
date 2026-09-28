"""Number platform for Communifarm profile targets."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_BATCH_UPDATED, SIGNAL_WEIGH_SESSION_UPDATED
from .domain.models import CommunifarmState
from .domain.recipe import clamp_recipe_scale
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
            CommunifarmRecipeScale(entry, state, repo),
            CommunifarmContainerCount(entry.entry_id),
            CommunifarmSubstrateGPerContainer(entry.entry_id),
            CommunifarmHarvestMassG(entry.entry_id),
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


class CommunifarmRecipeScale(_ProfileNumber):
    """Scale Wood Lover (and future) recipes by 0.1×–10× for container size."""

    _attr_name = "Recipe scale"
    _attr_unique_id = "communifarm_recipe_scale"
    _attr_icon = "mdi:multiplication"
    _attr_native_min_value = 0.1
    _attr_native_max_value = 10.0
    _attr_native_step = 0.1

    def __init__(
        self,
        entry: ConfigEntry,
        state: CommunifarmState,
        repo: CommunifarmRepository,
    ) -> None:
        super().__init__(entry, state, repo)
        self.entity_id = "number.communifarm_recipe_scale"

    @property
    def native_value(self) -> float:
        return self._runtime().recipe_scale

    async def async_set_native_value(self, value: float) -> None:
        runtime = self._runtime()
        runtime.recipe_scale = clamp_recipe_scale(value)
        runtime.validate()
        await self._async_persist()
        batch_repo = self.hass.data[DOMAIN][self._entry.entry_id].get("batch_repository")
        if batch_repo is not None:
            await batch_repo.async_set_recipe_scale(
                runtime.batch.id, runtime.recipe_scale
            )
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, SIGNAL_WEIGH_SESSION_UPDATED, self._entry.entry_id
        )
        async_dispatcher_send(
            self.hass, SIGNAL_BATCH_UPDATED, self._entry.entry_id
        )


class CommunifarmContainerCount(NumberEntity):
    """How many containers this mix will be split into (Batches tab)."""

    _attr_has_entity_name = True
    _attr_name = "Container count"
    _attr_unique_id = "communifarm_container_count"
    _attr_icon = "mdi:package-variant"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "number.communifarm_container_count"
        self._value = 1.0

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["container_count"] = int(self._value)

    @property
    def native_value(self) -> float:
        return float(self.hass.data[DOMAIN][self._entry_id].get("container_count", 1))

    async def async_set_native_value(self, value: float) -> None:
        count = max(1, int(value))
        self.hass.data[DOMAIN][self._entry_id]["container_count"] = count
        self.async_write_ha_state()


class CommunifarmSubstrateGPerContainer(NumberEntity):
    """Substrate mass (g) per production container (Production tab)."""

    _attr_has_entity_name = True
    _attr_name = "Substrate g per container"
    _attr_unique_id = "communifarm_substrate_g_per_container"
    _attr_icon = "mdi:weight-gram"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1.0
    _attr_native_max_value = 50000.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "g"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "number.communifarm_substrate_g_per_container"
        self._value = 1000.0

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["substrate_g_per_container"] = self._value

    @property
    def native_value(self) -> float:
        return float(
            self.hass.data[DOMAIN][self._entry_id].get(
                "substrate_g_per_container", self._value
            )
        )

    async def async_set_native_value(self, value: float) -> None:
        self._value = max(1.0, float(value))
        self.hass.data[DOMAIN][self._entry_id][
            "substrate_g_per_container"
        ] = self._value
        self.async_write_ha_state()


class CommunifarmHarvestMassG(NumberEntity):
    """Harvest flush mass (g) for the next record/final harvest press."""

    _attr_has_entity_name = True
    _attr_name = "Harvest mass"
    _attr_unique_id = "communifarm_harvest_mass_g"
    _attr_icon = "mdi:scale"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0.1
    _attr_native_max_value = 100000.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "g"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "number.communifarm_harvest_mass_g"
        self._value = 100.0

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["harvest_mass_g"] = self._value

    @property
    def native_value(self) -> float:
        return float(
            self.hass.data[DOMAIN][self._entry_id].get("harvest_mass_g", self._value)
        )

    async def async_set_native_value(self, value: float) -> None:
        self._value = max(0.1, float(value))
        self.hass.data[DOMAIN][self._entry_id]["harvest_mass_g"] = self._value
        self.async_write_ha_state()
