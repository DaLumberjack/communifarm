"""Select platform — heat treatment + production container type."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .domain.batch_milestones import HEAT_PASTEURIZED, HEAT_STERILIZED
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            CommunifarmHeatTreatmentSelect(entry.entry_id),
            CommunifarmContainerTypeSelect(entry.entry_id),
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
