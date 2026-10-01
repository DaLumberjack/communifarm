"""Select platform — heat treatment + production container type."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_CULTURE_UPDATED
from .domain.batch_milestones import HEAT_PASTEURIZED, HEAT_STERILIZED
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
from .storage.culture_repository import CultureRepository


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            CommunifarmHeatTreatmentSelect(entry.entry_id),
            CommunifarmContainerTypeSelect(entry.entry_id),
            CommunifarmActiveInoculumSelect(entry.entry_id),
            CommunifarmCatalogVarietySelect(entry.entry_id),
            CommunifarmAcquireFormSelect(entry.entry_id),
            CommunifarmAcquireSourceSelect(entry.entry_id),
            CommunifarmCultureVesselStatusSelect(entry.entry_id),
            CommunifarmPaymentMethodSelect(entry.entry_id),
            CommunifarmSaleVenueSelect(entry.entry_id),
            CommunifarmSaleBuyerSelect(entry.entry_id),
        ]
    )


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


class CommunifarmContainerTypeSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Container type"
    _attr_unique_id = "communifarm_container_type"
    _attr_icon = "mdi:package-variant"
    _attr_options = [
        CONTAINER_BLOCK,
        CONTAINER_TUB,
        CONTAINER_BAG,
        CONTAINER_JAR,
        CONTAINER_OTHER,
    ]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_container_type"
        self._current = CONTAINER_BAG

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["container_type"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["container_type"] = option
        self.async_write_ha_state()


class CommunifarmActiveInoculumSelect(SelectEntity):
    """Culture lot used by the Production Inoculate batch button."""

    _attr_has_entity_name = True
    _attr_name = "Active inoculum"
    _attr_unique_id = "communifarm_active_inoculum"
    _attr_icon = "mdi:needle"
    # HA reads options during entity add (before async_added_to_hass).
    _attr_options = ["(no cultures yet)"]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_active_inoculum"
        self._option_to_id: dict[str, str] = {}
        self._current: str | None = None

    async def async_added_to_hass(self) -> None:
        await self._async_reload_options()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CULTURE_UPDATED, self._on_culture_updated
            )
        )

    @callback
    def _on_culture_updated(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self.hass.async_create_task(self._async_reload_options())

    async def _async_reload_options(self) -> None:
        repo: CultureRepository = self.hass.data[DOMAIN][self._entry_id][
            "culture_repository"
        ]
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

        active = self.hass.data[DOMAIN][self._entry_id].get("active_culture_id")
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


class CommunifarmCatalogVarietySelect(SelectEntity):
    """Pick a catalog variety for acquire / retire."""

    _attr_has_entity_name = True
    _attr_name = "Catalog variety"
    _attr_unique_id = "communifarm_catalog_variety"
    _attr_icon = "mdi:mushroom-outline"
    _attr_options = ["(no varieties yet)"]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_catalog_variety"
        self._option_to_id: dict[str, str] = {}
        self._current: str | None = None

    async def async_added_to_hass(self) -> None:
        await self._async_reload_options()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CULTURE_UPDATED, self._on_updated
            )
        )

    @callback
    def _on_updated(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self.hass.async_create_task(self._async_reload_options())

    async def _async_reload_options(self) -> None:
        repo: CultureRepository = self.hass.data[DOMAIN][self._entry_id][
            "culture_repository"
        ]
        varieties = await repo.async_list_varieties()
        self._option_to_id = {v.name: v.id for v in varieties}
        self._attr_options = list(self._option_to_id.keys()) or ["(no varieties yet)"]
        previous = self.hass.data[DOMAIN][self._entry_id].get("catalog_variety_id")
        self._current = None
        if previous:
            for label, vid in self._option_to_id.items():
                if vid == previous:
                    self._current = label
                    break
        if self._current is None and self._option_to_id:
            self._current = self._attr_options[0]
            self.hass.data[DOMAIN][self._entry_id]["catalog_variety_id"] = (
                self._option_to_id[self._current]
            )
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._option_to_id:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["catalog_variety_id"] = self._option_to_id[
            option
        ]
        self.async_write_ha_state()


class CommunifarmAcquireFormSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Acquire form"
    _attr_unique_id = "communifarm_acquire_form"
    _attr_icon = "mdi:flask"
    _attr_options = [
        FORM_LIQUID_CULTURE,
        FORM_GRAIN_SPAWN,
        FORM_AGAR,
        FORM_SPORES,
    ]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_acquire_form"
        self._current = FORM_LIQUID_CULTURE

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["acquire_form"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["acquire_form"] = option
        self.async_write_ha_state()


class CommunifarmAcquireSourceSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Acquire source"
    _attr_unique_id = "communifarm_acquire_source"
    _attr_icon = "mdi:handshake"
    _attr_options = [SOURCE_PURCHASED, SOURCE_ACQUAINTANCE, SOURCE_WILD]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_acquire_source"
        self._current = SOURCE_PURCHASED

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["acquire_source"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["acquire_source"] = option
        self.async_write_ha_state()


class CommunifarmCultureVesselStatusSelect(SelectEntity):
    """LC / grain vessel status for the active inoculum (or draft before apply)."""

    _attr_has_entity_name = True
    _attr_name = "Culture vessel status"
    _attr_unique_id = "communifarm_culture_vessel_status"
    _attr_icon = "mdi:state-machine"
    _attr_options = sorted(VESSEL_STATUSES)

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_culture_vessel_status"
        self._current = CULTURE_STATUS_READY

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["culture_vessel_status"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["culture_vessel_status"] = option
        self.async_write_ha_state()


class CommunifarmPaymentMethodSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Payment method"
    _attr_unique_id = "communifarm_payment_method"
    _attr_icon = "mdi:cash"
    _attr_options = [
        PAYMENT_CASH,
        PAYMENT_CHECK,
        PAYMENT_VENMO,
        PAYMENT_DIGITAL,
        PAYMENT_OTHER,
    ]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_payment_method"
        self._current = PAYMENT_CASH

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["payment_method"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["payment_method"] = option
        self.async_write_ha_state()


class CommunifarmSaleVenueSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Sale venue"
    _attr_unique_id = "communifarm_sale_venue"
    _attr_icon = "mdi:map-marker"
    _attr_options = [
        "Farmers market",
        "Farm stand",
        "CSA pickup",
        "Restaurant",
        "Delivery",
        "Other",
    ]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_sale_venue"
        self._current = "Farmers market"

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["sale_venue_label"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["sale_venue_label"] = option
        self.async_write_ha_state()


class CommunifarmSaleBuyerSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Sale buyer"
    _attr_unique_id = "communifarm_sale_buyer"
    _attr_icon = "mdi:account"
    _attr_options = [
        "Walk-up",
        "CSA member",
        "Restaurant",
        "Wholesale",
        "Other",
    ]

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "select.communifarm_sale_buyer"
        self._current = "Walk-up"

    async def async_added_to_hass(self) -> None:
        self.hass.data[DOMAIN][self._entry_id]["sale_buyer_label"] = self._current

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.hass.data[DOMAIN][self._entry_id]["sale_buyer_label"] = option
        self.async_write_ha_state()
