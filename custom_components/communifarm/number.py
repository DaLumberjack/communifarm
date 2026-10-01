"""Number platform for Communifarm profile targets and dashboard drafts."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_CONTAINER_COUNT,
    ENTITY_HARVEST_MASS_G,
    ENTITY_HUMIDITY_TARGET,
    ENTITY_RECIPE_SCALE,
    ENTITY_SALE_LINE_AMOUNT,
    ENTITY_SALE_MASS_G,
    ENTITY_SUBSTRATE_G,
    ENTITY_TEMPERATURE_TARGET,
    SIGNAL_BATCH_UPDATED,
    SIGNAL_WEIGH_SESSION_UPDATED,
)
from .domain.models import CommunifarmState
from .domain.recipe import clamp_recipe_scale
from .entity import CommunifarmEntity
from .storage.repository import CommunifarmRepository


@dataclass(frozen=True, slots=True)
class _NumberSpec:
    """Draft number stored on one bucket key."""

    name: str
    unique_id: str
    entity_id: str
    icon: str
    bucket_key: str
    default: float
    native_min: float
    native_max: float
    native_step: float
    floor: float
    mode: NumberMode = NumberMode.BOX
    unit: str | None = None
    as_int: bool = False


class CommunifarmNumber(CommunifarmEntity, NumberEntity):
    """Number identity and entry bucket."""


class CommunifarmProfileNumber(CommunifarmNumber):
    """Profile target persisted to the Communifarm store."""

    # Slider is easier to nudge from the managed dashboard than a settings dig.
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        entry: ConfigEntry,
        state: CommunifarmState,
        repo: CommunifarmRepository,
        *,
        entity_id: str,
    ) -> None:
        super().__init__(entry.entry_id, entity_id=entity_id)
        self._entry = entry
        self._state = state
        self._repo = repo

    async def _async_persist(self) -> None:
        runtime = self.runtime_state()
        await self._repo.async_save(runtime)
        self.hass.config_entries.async_update_entry(
            self._entry, data={**self._entry.data, "state": runtime.to_dict()}
        )


class CommunifarmBucketNumber(CommunifarmNumber):
    """Read and write one numeric draft on the entry bucket."""

    def __init__(self, entry_id: str, spec: _NumberSpec) -> None:
        super().__init__(
            entry_id,
            name=spec.name,
            unique_id=spec.unique_id,
            entity_id=spec.entity_id,
            icon=spec.icon,
        )
        self._spec = spec
        self._value = spec.default
        self._attr_mode = spec.mode
        self._attr_native_min_value = spec.native_min
        self._attr_native_max_value = spec.native_max
        self._attr_native_step = spec.native_step
        if spec.unit is not None:
            self._attr_native_unit_of_measurement = spec.unit

    async def async_added_to_hass(self) -> None:
        stored: int | float = int(self._value) if self._spec.as_int else self._value
        self.bucket()[self._spec.bucket_key] = stored

    @property
    def native_value(self) -> float:
        return float(self.bucket().get(self._spec.bucket_key, self._value))

    async def async_set_native_value(self, value: float) -> None:
        clamped = max(self._spec.floor, float(value))
        if self._spec.as_int:
            stored = int(clamped)
            self._value = float(stored)
            self.bucket()[self._spec.bucket_key] = stored
        else:
            self._value = clamped
            self.bucket()[self._spec.bucket_key] = self._value
        self.async_write_ha_state()


def _draft(
    name: str,
    unique_id: str,
    entity_id: str,
    icon: str,
    bucket_key: str,
    default: float,
    native_min: float,
    native_max: float,
    native_step: float,
    floor: float,
    *,
    unit: str | None = None,
    as_int: bool = False,
) -> _NumberSpec:
    return _NumberSpec(
        name,
        unique_id,
        entity_id,
        icon,
        bucket_key,
        default,
        native_min,
        native_max,
        native_step,
        floor,
        unit=unit,
        as_int=as_int,
    )


_DRAFT_NUMBERS: tuple[_NumberSpec, ...] = (
    _draft(
        "Container count",
        "communifarm_container_count",
        ENTITY_CONTAINER_COUNT,
        "mdi:package-variant",
        "container_count",
        1.0,
        1.0,
        100.0,
        1.0,
        1.0,
        as_int=True,
    ),
    _draft(
        "Substrate g per container",
        "communifarm_substrate_g_per_container",
        ENTITY_SUBSTRATE_G,
        "mdi:weight-gram",
        "substrate_g_per_container",
        1000.0,
        1.0,
        50000.0,
        1.0,
        1.0,
        unit="g",
    ),
    _draft(
        "Harvest mass",
        "communifarm_harvest_mass_g",
        ENTITY_HARVEST_MASS_G,
        "mdi:scale",
        "harvest_mass_g",
        100.0,
        0.1,
        100000.0,
        0.1,
        0.1,
        unit="g",
    ),
    _draft(
        "Sale mass",
        "communifarm_sale_mass_g",
        ENTITY_SALE_MASS_G,
        "mdi:scale-balance",
        "sale_mass_g",
        100.0,
        0.1,
        50000.0,
        0.1,
        0.1,
        unit="g",
    ),
    _draft(
        "Sale line amount",
        "communifarm_sale_line_amount",
        ENTITY_SALE_LINE_AMOUNT,
        "mdi:currency-usd",
        "sale_line_amount",
        10.0,
        0.0,
        1000000.0,
        0.01,
        0.0,
        unit="USD",
    ),
)


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
            *[CommunifarmBucketNumber(entry.entry_id, spec) for spec in _DRAFT_NUMBERS],
        ]
    )


class CommunifarmTemperatureTarget(CommunifarmProfileNumber):
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
        super().__init__(entry, state, repo, entity_id=ENTITY_TEMPERATURE_TARGET)

    @property
    def native_value(self) -> float:
        return self.runtime_state().profile.temperature_target

    async def async_set_native_value(self, value: float) -> None:
        runtime = self.runtime_state()
        runtime.profile.temperature_target = float(value)
        runtime.profile.validate()
        await self._async_persist()
        self.async_write_ha_state()


class CommunifarmHumidityTarget(CommunifarmProfileNumber):
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
        super().__init__(entry, state, repo, entity_id=ENTITY_HUMIDITY_TARGET)

    @property
    def native_value(self) -> float:
        return self.runtime_state().profile.humidity_target

    async def async_set_native_value(self, value: float) -> None:
        runtime = self.runtime_state()
        runtime.profile.humidity_target = float(value)
        runtime.profile.validate()
        await self._async_persist()
        self.async_write_ha_state()


class CommunifarmRecipeScale(CommunifarmProfileNumber):
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
        super().__init__(entry, state, repo, entity_id=ENTITY_RECIPE_SCALE)

    @property
    def native_value(self) -> float:
        return self.runtime_state().recipe_scale

    async def async_set_native_value(self, value: float) -> None:
        runtime = self.runtime_state()
        runtime.recipe_scale = clamp_recipe_scale(value)
        runtime.validate()
        await self._async_persist()
        batch_repo = self.bucket().get("batch_repository")
        if batch_repo is not None:
            await batch_repo.async_set_recipe_scale(
                runtime.batch.id, runtime.recipe_scale
            )
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, SIGNAL_WEIGH_SESSION_UPDATED, self._entry.entry_id
        )
        async_dispatcher_send(self.hass, SIGNAL_BATCH_UPDATED, self._entry.entry_id)
