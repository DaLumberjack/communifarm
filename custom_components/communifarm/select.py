"""Select platform — heat treatment, production, culture, and sale drafts."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_ACQUIRE_FORM,
    ENTITY_ACQUIRE_SOURCE,
    ENTITY_ACTIVE_INOCULUM,
    ENTITY_CATALOG_VARIETY,
    ENTITY_CONTAINER_TYPE,
    ENTITY_CULTURE_VESSEL_STATUS,
    ENTITY_HEAT_TREATMENT,
    ENTITY_INTAKE_AMOUNT_UNIT,
    ENTITY_INTAKE_PAYMENT,
    ENTITY_INTAKE_PROCESS_MODE,
    ENTITY_INTAKE_RECEIPT,
    ENTITY_INTAKE_TAG_UID,
    ENTITY_INTAKE_TRACKED,
    ENTITY_INTAKE_ZONE,
    ENTITY_NFC_SCAN_MODE,
    ENTITY_NFC_WRITE_LABEL,
    ENTITY_NFC_WRITE_OBJECT_TYPE,
    ENTITY_PAYMENT_METHOD,
    ENTITY_RELOCATE_ZONE,
    ENTITY_SALE_BUYER,
    ENTITY_SALE_VENUE,
    SIGNAL_CULTURE_UPDATED,
    SIGNAL_NFC_CHECKIN_UPDATED,
)
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
from .domain.inventory import (
    AMOUNT_UNITS,
    INTAKE_PROCESS_COMBINED,
    INTAKE_PROCESS_MARK_TAGS,
    INTAKE_PROCESS_PURCHASE,
    OBJECT_BATCH,
    OBJECT_CONTAINER,
    OBJECT_CULTURE,
    OBJECT_EMPLOYEE,
    OBJECT_INVENTORY,
    OBJECT_LOCATION,
    OBJECT_MACHINE,
    PAYMENT_ACCOUNT,
    PAYMENT_CASH,
    SCAN_MODE_NORMAL,
    SCAN_MODE_REGISTER_BLOCK,
    inventory_write_choices,
)
from .domain.production import (
    CONTAINER_BAG,
    CONTAINER_BLOCK,
    CONTAINER_JAR,
    CONTAINER_OTHER,
    CONTAINER_TUB,
)
from .domain.sale import (
    PAYMENT_CHECK,
    PAYMENT_DIGITAL,
    PAYMENT_OTHER,
    PAYMENT_VENMO,
)
from .entity import CommunifarmEntity
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
    _spec(
        "Intake tag type",
        "communifarm_nfc_write_object_type",
        ENTITY_NFC_WRITE_OBJECT_TYPE,
        "mdi:nfc",
        (
            OBJECT_INVENTORY,
            OBJECT_LOCATION,
            OBJECT_CONTAINER,
            OBJECT_BATCH,
            OBJECT_CULTURE,
            OBJECT_MACHINE,
            OBJECT_EMPLOYEE,
        ),
        "nfc_write_object_type",
        OBJECT_INVENTORY,
    ),
    _spec(
        "Intake asset / ingredient label",
        "communifarm_nfc_write_label",
        ENTITY_NFC_WRITE_LABEL,
        "mdi:tag-text",
        tuple(inventory_write_choices()),
        "nfc_write_label",
        "hardwood pellets",
    ),
    _spec(
        "NFC scan mode",
        "communifarm_nfc_scan_mode",
        ENTITY_NFC_SCAN_MODE,
        "mdi:nfc-variant",
        (SCAN_MODE_NORMAL, SCAN_MODE_REGISTER_BLOCK),
        "nfc_scan_mode",
        SCAN_MODE_NORMAL,
    ),
    _spec(
        "Intake process mode",
        "communifarm_intake_process_mode",
        ENTITY_INTAKE_PROCESS_MODE,
        "mdi:view-dashboard-variant",
        (
            INTAKE_PROCESS_COMBINED,
            INTAKE_PROCESS_MARK_TAGS,
            INTAKE_PROCESS_PURCHASE,
        ),
        "intake_process_mode",
        INTAKE_PROCESS_COMBINED,
    ),
    _spec(
        "Intake amount unit",
        "communifarm_intake_amount_unit",
        ENTITY_INTAKE_AMOUNT_UNIT,
        "mdi:weight",
        AMOUNT_UNITS,
        "intake_amount_unit",
        "g",
    ),
    _spec(
        "Intake payment location",
        "communifarm_intake_payment_location",
        ENTITY_INTAKE_PAYMENT,
        "mdi:cash-register",
        (PAYMENT_ACCOUNT, PAYMENT_CASH),
        "intake_payment_location",
        PAYMENT_CASH,
    ),
    _spec(
        "Intake tracked",
        "communifarm_intake_tracked",
        ENTITY_INTAKE_TRACKED,
        "mdi:clipboard-check",
        ("yes", "no"),
        "intake_tracked",
        "yes",
    ),
    _spec(
        "Intake receipt tracked",
        "communifarm_intake_receipt_tracked",
        ENTITY_INTAKE_RECEIPT,
        "mdi:receipt",
        ("yes", "no"),
        "intake_receipt_tracked",
        "no",
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
            CommunifarmZoneSelect(
                entry_id,
                name="Intake location zone",
                unique_id="communifarm_intake_zone",
                entity_id=ENTITY_INTAKE_ZONE,
                bucket_key="intake_zone_label",
            ),
            CommunifarmZoneSelect(
                entry_id,
                name="Relocate to Storage (post-sterile)",
                unique_id="communifarm_relocate_zone",
                entity_id=ENTITY_RELOCATE_ZONE,
                bucket_key="relocate_zone_label",
                area_kind="storage",
            ),
            CommunifarmTagSourceSelect(entry_id),
            *[CommunifarmBucketSelect(entry_id, spec) for spec in _BUCKET_SELECTS[2:]],
        ]
    )


class CommunifarmTagSourceSelect(CommunifarmSelect):
    """Choose last scanned UID or a chip from the shipment / CF tag pool."""

    _attr_name = "Tag source (scan or DB)"
    _attr_unique_id = "communifarm_intake_tag_uid"
    _attr_icon = "mdi:nfc"
    _attr_options = ["(last scanned)"]

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_INTAKE_TAG_UID)
        self._current = "(last scanned)"

    async def async_added_to_hass(self) -> None:
        await self.async_refresh_options()
        self.listen_entry_signals(SIGNAL_NFC_CHECKIN_UPDATED, method="async_refresh_options")

    async def async_refresh_options(self) -> None:
        from . import inventory_actions
        from .domain.inventory import TAG_SOURCE_LAST_SCANNED

        if self._entry_id not in self.hass.data.get(DOMAIN, {}):
            return
        try:
            options = await inventory_actions.async_list_tag_source_options(
                self.hass, self._entry_id
            )
        except (OSError, RuntimeError, sqlite3.ProgrammingError):
            # Unload / closed shared SQLite during eager dispatcher refresh.
            return
        self._attr_options = options
        # Prefer a choice already set on the bucket (e.g. after seed shipment).
        bucket_choice = self.bucket().get("intake_tag_uid_choice")
        if isinstance(bucket_choice, str) and bucket_choice in options:
            self._current = bucket_choice
        elif self._current not in options:
            self._current = TAG_SOURCE_LAST_SCANNED
            self.bucket()["intake_tag_uid_choice"] = self._current
        else:
            self.bucket()["intake_tag_uid_choice"] = self._current
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.bucket()["intake_tag_uid_choice"] = option
        self.async_write_ha_state()


class CommunifarmZoneSelect(CommunifarmSelect):
    """Dynamic 'Area / Zone' options from the placement layout."""

    _attr_icon = "mdi:map-marker"
    _attr_options = ["(loading zones…)"]

    def __init__(
        self,
        entry_id: str,
        *,
        name: str,
        unique_id: str,
        entity_id: str,
        bucket_key: str,
        area_kind: str | None = None,
    ) -> None:
        super().__init__(
            entry_id,
            name=name,
            unique_id=unique_id,
            entity_id=entity_id,
            icon="mdi:map-marker",
        )
        self._bucket_key = bucket_key
        self._area_kind = area_kind
        self._current = "(loading zones…)"

    async def async_added_to_hass(self) -> None:
        from . import inventory_actions

        labels = await inventory_actions.async_list_zone_option_labels(
            self.hass, self._entry_id, area_kind=self._area_kind
        )
        self._attr_options = labels
        self._current = labels[0]
        self.bucket()[self._bucket_key] = self._current
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._current = option
        self.bucket()[self._bucket_key] = option
        self.async_write_ha_state()


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
