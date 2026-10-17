"""Select platform — heat treatment, production, culture, and sale drafts."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ENTITY_ACQUIRE_FORM,
    ENTITY_ACQUIRE_SOURCE,
    ENTITY_ACTIVE_INOCULUM,
    ENTITY_CATALOG_VARIETY,
    ENTITY_CLIMATE_SETTINGS_NODE,
    ENTITY_CLIMATE_SETTINGS_ROW,
    ENTITY_CONTAINER_TYPE,
    ENTITY_CULTURE_VESSEL_STATUS,
    ENTITY_HEAT_TREATMENT,
    ENTITY_PAYMENT_METHOD,
    ENTITY_SALE_BUYER,
    ENTITY_SALE_VENUE,
    SIGNAL_CLIMATE_SETTINGS_UPDATED,
    SIGNAL_CULTURE_UPDATED,
)
from .domain.batch_milestones import HEAT_PASTEURIZED, HEAT_STERILIZED
from .domain.climate_settings import SCOPE_NODE, SCOPE_ROW
from .domain.culture import (
    CULTURE_STATUS_READY,
    FORM_AGAR,
    FORM_GRAIN_SPAWN,
    FORM_LIQUID_CULTURE,
    FORM_SPORES,
    INOCULUM_READY_STATUSES,
    SOURCE_ACQUAINTANCE,
    SOURCE_PURCHASED,
    SOURCE_WILD,
    VESSEL_STATUSES,
)
from .domain.production import (
    CONTAINER_BAG,
    CONTAINER_BLOCK,
    CONTAINER_JAR,
    CONTAINER_OTHER,
    CONTAINER_TUB,
)
from .domain.sale import (
    PAYMENT_CASH,
    PAYMENT_CHECK,
    PAYMENT_DIGITAL,
    PAYMENT_OTHER,
    PAYMENT_VENMO,
)
from .entity import CommunifarmEntity
from .settings_access import async_require_automation_settings_access
from .storage.culture_repository import CultureRepository


@dataclass(frozen=True, slots=True)
class _SelectSpec:
    """Select that stores the chosen option on one bucket key."""

    name: str
    unique_id: str
    entity_id: str
    icon: str
    options: tuple[str, ...]
    bucket_key: str
    default: str


class CommunifarmSelect(CommunifarmEntity, SelectEntity):
    """Select identity and entry bucket."""


class CommunifarmBucketSelect(CommunifarmSelect):
    """Write the current option into ``hass.data`` under one key."""

    def __init__(self, entry_id: str, spec: _SelectSpec) -> None:
        super().__init__(
            entry_id,
            name=spec.name,
            unique_id=spec.unique_id,
            entity_id=spec.entity_id,
            icon=spec.icon,
        )
        self._bucket_key = spec.bucket_key
        self._current = spec.default
        self._attr_options = list(spec.options)

    async def async_added_to_hass(self) -> None:
        self.bucket()[self._bucket_key] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.bucket()[self._bucket_key] = option
        self.async_write_ha_state()


def _spec(
    name: str,
    unique_id: str,
    entity_id: str,
    icon: str,
    options: tuple[str, ...],
    bucket_key: str,
    default: str,
) -> _SelectSpec:
    return _SelectSpec(name, unique_id, entity_id, icon, options, bucket_key, default)


_BUCKET_SELECTS: tuple[_SelectSpec, ...] = (
    _spec(
        "Heat treatment method",
        "communifarm_heat_treatment",
        ENTITY_HEAT_TREATMENT,
        "mdi:thermometer-lines",
        (HEAT_PASTEURIZED, HEAT_STERILIZED),
        "heat_treatment",
        HEAT_PASTEURIZED,
    ),
    _spec(
        "Container type",
        "communifarm_container_type",
        ENTITY_CONTAINER_TYPE,
        "mdi:package-variant",
        (CONTAINER_BLOCK, CONTAINER_TUB, CONTAINER_BAG, CONTAINER_JAR, CONTAINER_OTHER),
        "container_type",
        CONTAINER_BAG,
    ),
    _spec(
        "Acquire form",
        "communifarm_acquire_form",
        ENTITY_ACQUIRE_FORM,
        "mdi:flask",
        (FORM_LIQUID_CULTURE, FORM_GRAIN_SPAWN, FORM_AGAR, FORM_SPORES),
        "acquire_form",
        FORM_LIQUID_CULTURE,
    ),
    _spec(
        "Acquire source",
        "communifarm_acquire_source",
        ENTITY_ACQUIRE_SOURCE,
        "mdi:handshake",
        (SOURCE_PURCHASED, SOURCE_ACQUAINTANCE, SOURCE_WILD),
        "acquire_source",
        SOURCE_PURCHASED,
    ),
    _spec(
        "Culture vessel status",
        "communifarm_culture_vessel_status",
        ENTITY_CULTURE_VESSEL_STATUS,
        "mdi:state-machine",
        tuple(sorted(VESSEL_STATUSES)),
        "culture_vessel_status",
        CULTURE_STATUS_READY,
    ),
    _spec(
        "Payment method",
        "communifarm_payment_method",
        ENTITY_PAYMENT_METHOD,
        "mdi:cash",
        (PAYMENT_CASH, PAYMENT_CHECK, PAYMENT_VENMO, PAYMENT_DIGITAL, PAYMENT_OTHER),
        "payment_method",
        PAYMENT_CASH,
    ),
    _spec(
        "Sale venue",
        "communifarm_sale_venue",
        ENTITY_SALE_VENUE,
        "mdi:map-marker",
        (
            "Farmers market",
            "Farm stand",
            "CSA pickup",
            "Restaurant",
            "Delivery",
            "Other",
        ),
        "sale_venue_label",
        "Farmers market",
    ),
    _spec(
        "Sale buyer",
        "communifarm_sale_buyer",
        ENTITY_SALE_BUYER,
        "mdi:account",
        ("Walk-up", "CSA member", "Restaurant", "Wholesale", "Other"),
        "sale_buyer_label",
        "Walk-up",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entry_id = entry.entry_id
    async_add_entities(
        [
            CommunifarmBucketSelect(entry_id, _BUCKET_SELECTS[0]),
            CommunifarmBucketSelect(entry_id, _BUCKET_SELECTS[1]),
            CommunifarmActiveInoculumSelect(entry_id),
            CommunifarmCatalogVarietySelect(entry_id),
            CommunifarmClimateScopeSelect(
                entry_id,
                scope=SCOPE_NODE,
                name="Climate settings room",
                entity_id=ENTITY_CLIMATE_SETTINGS_NODE,
            ),
            CommunifarmClimateScopeSelect(
                entry_id,
                scope=SCOPE_ROW,
                name="Climate settings row",
                entity_id=ENTITY_CLIMATE_SETTINGS_ROW,
            ),
            *[CommunifarmBucketSelect(entry_id, spec) for spec in _BUCKET_SELECTS[2:]],
        ]
    )


class CommunifarmClimateScopeSelect(CommunifarmSelect):
    """Choose which persisted room or row the settings entities edit."""

    _attr_icon = "mdi:map-marker-radius"
    _attr_options = ["(loading)"]

    def __init__(
        self, entry_id: str, *, scope: str, name: str, entity_id: str
    ) -> None:
        super().__init__(
            entry_id,
            name=name,
            unique_id=f"communifarm_climate_settings_{scope}",
            entity_id=entity_id,
        )
        self._scope = scope
        self._option_to_id: dict[str, str] = {}
        self._current: str | None = None

    async def async_added_to_hass(self) -> None:
        if "climate_settings_values" not in self.bucket():
            from . import climate_actions

            await climate_actions.async_refresh_climate_settings_editor(
                self.hass, self._entry_id
            )
        await self._async_reload_options()
        self.listen_entry_signals(
            SIGNAL_CLIMATE_SETTINGS_UPDATED, method="_async_reload_options"
        )

    async def _async_reload_options(self) -> None:
        options_key = f"climate_settings_{self._scope}_options"
        selected_key = f"climate_settings_{self._scope}_id"
        self._option_to_id = dict(self.bucket().get(options_key, {}))
        self._attr_options = list(self._option_to_id) or ["(none available)"]
        selected_id = self.bucket().get(selected_key)
        self._current = next(
            (
                label
                for label, scope_id in self._option_to_id.items()
                if scope_id == selected_id
            ),
            None,
        )
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        scope_id = self._option_to_id.get(option)
        if scope_id is None:
            return
        await async_require_automation_settings_access(self.hass, self._context)
        from . import climate_actions

        await climate_actions.async_select_climate_settings_scope(
            self.hass, self._entry_id, self._scope, scope_id
        )


class CommunifarmActiveInoculumSelect(CommunifarmSelect):
    """Culture lot used by the Production Inoculate batch button."""

    _attr_name = "Active inoculum"
    _attr_unique_id = "communifarm_active_inoculum"
    _attr_icon = "mdi:needle"
    # HA reads options during entity add (before async_added_to_hass).
    _attr_options = ["(no cultures yet)"]

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_ACTIVE_INOCULUM)
        self._option_to_id: dict[str, str] = {}
        self._current: str | None = None

    async def async_added_to_hass(self) -> None:
        await self._async_reload_options()
        self.listen_entry_signals(SIGNAL_CULTURE_UPDATED, method="_async_reload_options")

    async def _async_reload_options(self) -> None:
        repo: CultureRepository = self.bucket()["culture_repository"]
        cultures = await repo.async_list_cultures()
        self._option_to_id = {}
        for lot in cultures:
            if lot.status not in INOCULUM_READY_STATUSES:
                continue
            label = lot.display_label()
            if label in self._option_to_id:
                label = f"{label}*"
            self._option_to_id[label] = lot.id
        self._attr_options = list(self._option_to_id.keys()) or ["(no ready cultures)"]

        active = self.bucket().get("active_culture_id")
        self._current = None
        if active:
            for label, cid in self._option_to_id.items():
                if cid == active:
                    self._current = label
                    break
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._option_to_id:
            return
        from . import culture_actions

        await culture_actions.async_set_active_inoculum(
            self.hass, self._entry_id, self._option_to_id[option]
        )
        self._current = option
        self.async_write_ha_state()


class CommunifarmCatalogVarietySelect(CommunifarmSelect):
    """Pick a catalog variety for acquire / retire."""

    _attr_name = "Catalog variety"
    _attr_unique_id = "communifarm_catalog_variety"
    _attr_icon = "mdi:mushroom-outline"
    _attr_options = ["(no varieties yet)"]

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_CATALOG_VARIETY)
        self._option_to_id: dict[str, str] = {}
        self._current: str | None = None

    async def async_added_to_hass(self) -> None:
        await self._async_reload_options()
        self.listen_entry_signals(SIGNAL_CULTURE_UPDATED, method="_async_reload_options")

    async def _async_reload_options(self) -> None:
        repo: CultureRepository = self.bucket()["culture_repository"]
        varieties = await repo.async_list_varieties()
        self._option_to_id = {v.name: v.id for v in varieties}
        self._attr_options = list(self._option_to_id.keys()) or ["(no varieties yet)"]
        previous = self.bucket().get("catalog_variety_id")
        self._current = None
        if previous:
            for label, vid in self._option_to_id.items():
                if vid == previous:
                    self._current = label
                    break
        if self._current is None and self._option_to_id:
            self._current = self._attr_options[0]
            self.bucket()["catalog_variety_id"] = self._option_to_id[self._current]
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._option_to_id:
            return
        self._current = option
        self.bucket()["catalog_variety_id"] = self._option_to_id[option]
        self.async_write_ha_state()
