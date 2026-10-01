"""Button platform — mix / batch / production milestone actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .domain.batch_milestones import (
    MILESTONE_COMPLETELY_MIXED,
    MILESTONE_CONTAINERS_SEPARATED,
    MILESTONE_DRY_WET_MIX_STARTED,
    MILESTONE_FIELD_CAPACITY_REACHED,
    MILESTONE_HEAT_TREATED,
    MILESTONE_PRODUCTION_CYCLE_STARTED,
    MILESTONE_SETTLING_STARTED,
    MILESTONE_STORED_FOR_COOLING,
    MILESTONE_WATER_ADDED,
)
from .domain.production import (
    CONTAINER_BAG,
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INCUBATING,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            CommunifarmMilestoneButton(
                entry.entry_id,
                "Water added",
                "communifarm_water_added",
                "button.communifarm_water_added",
                MILESTONE_WATER_ADDED,
                "mdi:water",
            ),
            CommunifarmMilestoneButton(
                entry.entry_id,
                "Started dry/wet mix",
                "communifarm_dry_wet_mix_started",
                "button.communifarm_dry_wet_mix_started",
                MILESTONE_DRY_WET_MIX_STARTED,
                "mdi:blender",
            ),
            CommunifarmMilestoneButton(
                entry.entry_id,
                "Settling",
                "communifarm_settling_started",
                "button.communifarm_settling_started",
                MILESTONE_SETTLING_STARTED,
                "mdi:timer-sand",
            ),
            CommunifarmMilestoneButton(
                entry.entry_id,
                "Reached field capacity",
                "communifarm_field_capacity_reached",
                "button.communifarm_field_capacity_reached",
                MILESTONE_FIELD_CAPACITY_REACHED,
                "mdi:water-check",
            ),
            CommunifarmMilestoneButton(
                entry.entry_id,
                "Completely mixed",
                "communifarm_completely_mixed",
                "button.communifarm_completely_mixed",
                MILESTONE_COMPLETELY_MIXED,
                "mdi:check-decagram",
            ),
            CommunifarmSeparateContainersButton(entry.entry_id),
            CommunifarmHeatTreatedButton(entry.entry_id),
            CommunifarmMilestoneButton(
                entry.entry_id,
                "Stored for cooling",
                "communifarm_stored_for_cooling",
                "button.communifarm_stored_for_cooling",
                MILESTONE_STORED_FOR_COOLING,
                "mdi:snowflake-thermometer",
            ),
            CommunifarmMilestoneButton(
                entry.entry_id,
                "Production cycle start (stub)",
                "communifarm_production_cycle_started",
                "button.communifarm_production_cycle_started",
                MILESTONE_PRODUCTION_CYCLE_STARTED,
                "mdi:sprout",
            ),
            CommunifarmCompleteAndNewBatchButton(entry.entry_id),
            CommunifarmSelectInoculumFromNfcButton(entry.entry_id),
            CommunifarmInoculateButton(entry.entry_id),
            CommunifarmAdvanceStageButton(
                entry.entry_id,
                "Move to incubation",
                "communifarm_move_to_incubation",
                "button.communifarm_move_to_incubation",
                STAGE_INCUBATING,
                "mdi:home-thermometer",
            ),
            CommunifarmAdvanceStageButton(
                entry.entry_id,
                "Move to fruiting",
                "communifarm_move_to_fruiting",
                "button.communifarm_move_to_fruiting",
                STAGE_FRUITING,
                "mdi:mushroom",
            ),
            CommunifarmAdvanceStageButton(
                entry.entry_id,
                "Move to harvest",
                "communifarm_move_to_harvest",
                "button.communifarm_move_to_harvest",
                STAGE_HARVESTING,
                "mdi:basket",
            ),
            CommunifarmRecordHarvestButton(entry.entry_id, is_final=False),
            CommunifarmRecordHarvestButton(entry.entry_id, is_final=True),
            CommunifarmNfcCheckinHarvestButton(entry.entry_id),
            CommunifarmConfirmContainerHarvestButton(entry.entry_id, is_final=False),
            CommunifarmConfirmContainerHarvestButton(entry.entry_id, is_final=True),
            CommunifarmCreateVarietyButton(entry.entry_id),
            CommunifarmRetireVarietyButton(entry.entry_id),
            CommunifarmAcquireCultureButton(entry.entry_id),
            CommunifarmSetCultureStatusButton(entry.entry_id),
            CommunifarmRecordSaleButton(entry.entry_id),
            CommunifarmRecordSaleCleanupButton(entry.entry_id),
        ]
    )


class CommunifarmMilestoneButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        name: str,
        unique_id: str,
        entity_id: str,
        event_type: str,
        icon: str,
    ) -> None:
        self._entry_id = entry_id
        self._event_type = event_type
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self.entity_id = entity_id

    async def async_press(self) -> None:
        from . import batch_actions

        await batch_actions.async_record_milestone(
            self.hass, self._entry_id, self._event_type
        )


class CommunifarmSeparateContainersButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Separate into containers"
    _attr_unique_id = "communifarm_separate_containers"
    _attr_icon = "mdi:package-variant-closed"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_separate_containers"

    async def async_press(self) -> None:
        from . import batch_actions

        bucket = self.hass.data[DOMAIN][self._entry_id]
        count = int(bucket.get("container_count", 1) or 1)
        await batch_actions.async_record_milestone(
            self.hass,
            self._entry_id,
            MILESTONE_CONTAINERS_SEPARATED,
            detail={"container_count": count},
        )


class CommunifarmHeatTreatedButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Record heat treatment"
    _attr_unique_id = "communifarm_heat_treated"
    _attr_icon = "mdi:fire"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_heat_treated"

    async def async_press(self) -> None:
        from . import batch_actions

        bucket = self.hass.data[DOMAIN][self._entry_id]
        method = bucket.get("heat_treatment", "pasteurized")
        await batch_actions.async_record_milestone(
            self.hass,
            self._entry_id,
            MILESTONE_HEAT_TREATED,
            detail={"method": method},
        )


class CommunifarmCompleteAndNewBatchButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Complete batch & start new"
    _attr_unique_id = "communifarm_complete_and_new_batch"
    _attr_icon = "mdi:playlist-plus"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_complete_and_new_batch"

    async def async_press(self) -> None:
        from . import batch_actions

        await batch_actions.async_complete_and_new_batch(self.hass, self._entry_id)


class CommunifarmSelectInoculumFromNfcButton(ButtonEntity):
    """Load active inoculum from input_text.esp32dev_last_nfc_uid (culture tag)."""

    _attr_has_entity_name = True
    _attr_name = "Select inoculum from NFC scan"
    _attr_unique_id = "communifarm_select_inoculum_from_nfc"
    _attr_icon = "mdi:nfc-variant"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_select_inoculum_from_nfc"

    async def async_press(self) -> None:
        from . import culture_actions

        await culture_actions.async_select_inoculum_from_nfc_scan(
            self.hass, self._entry_id
        )


class CommunifarmInoculateButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Inoculate batch"
    _attr_unique_id = "communifarm_inoculate_batch"
    _attr_icon = "mdi:needle"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_inoculate_batch"

    async def async_press(self) -> None:
        from . import production_actions

        bucket = self.hass.data[DOMAIN][self._entry_id]
        culture_id = bucket.get("active_culture_id")
        if not culture_id:
            raise HomeAssistantError(
                "No active culture — call acquire_culture or inoculate_batch with culture_id first"
            )
        await production_actions.async_inoculate_batch(
            self.hass,
            self._entry_id,
            culture_id=culture_id,
            container_type=bucket.get("container_type") or CONTAINER_BAG,
            container_count=int(bucket.get("container_count", 1) or 1),
            substrate_g_per_container=float(
                bucket.get("substrate_g_per_container", 1000.0) or 1000.0
            ),
        )


class CommunifarmAdvanceStageButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        name: str,
        unique_id: str,
        entity_id: str,
        target_stage: str,
        icon: str,
    ) -> None:
        self._entry_id = entry_id
        self._target_stage = target_stage
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self.entity_id = entity_id

    async def async_press(self) -> None:
        from . import production_actions

        await production_actions.async_advance_production_stage(
            self.hass, self._entry_id, target_stage=self._target_stage
        )


class CommunifarmRecordHarvestButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry_id: str, *, is_final: bool) -> None:
        self._entry_id = entry_id
        self._is_final = is_final
        if is_final:
            self._attr_name = "Final harvest"
            self._attr_unique_id = "communifarm_final_harvest"
            self.entity_id = "button.communifarm_final_harvest"
            self._attr_icon = "mdi:flag-checkered"
        else:
            self._attr_name = "Record harvest"
            self._attr_unique_id = "communifarm_record_harvest"
            self.entity_id = "button.communifarm_record_harvest"
            self._attr_icon = "mdi:scale"

    async def async_press(self) -> None:
        from . import production_actions

        bucket = self.hass.data[DOMAIN][self._entry_id]
        mass = float(bucket.get("harvest_mass_g", 100.0) or 100.0)
        await production_actions.async_record_harvest(
            self.hass,
            self._entry_id,
            mass_g=mass,
            is_final=self._is_final,
        )


class CommunifarmNfcCheckinHarvestButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "NFC check-in harvest"
    _attr_unique_id = "communifarm_nfc_checkin_harvest"
    _attr_icon = "mdi:nfc-variant"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_nfc_checkin_harvest"

    async def async_press(self) -> None:
        from . import nfc_actions
        from .domain.nfc import ACTIVITY_HARVEST

        await nfc_actions.async_check_in(
            self.hass, self._entry_id, activity=ACTIVITY_HARVEST
        )


class CommunifarmConfirmContainerHarvestButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry_id: str, *, is_final: bool) -> None:
        self._entry_id = entry_id
        self._is_final = is_final
        if is_final:
            self._attr_name = "Confirm final container harvest"
            self._attr_unique_id = "communifarm_confirm_final_container_harvest"
            self.entity_id = "button.communifarm_confirm_final_container_harvest"
            self._attr_icon = "mdi:flag-checkered"
        else:
            self._attr_name = "Confirm container harvest"
            self._attr_unique_id = "communifarm_confirm_container_harvest"
            self.entity_id = "button.communifarm_confirm_container_harvest"
            self._attr_icon = "mdi:check-circle"

    async def async_press(self) -> None:
        from . import production_actions

        bucket = self.hass.data[DOMAIN][self._entry_id]
        mass = float(bucket.get("harvest_mass_g", 100.0) or 100.0)
        await production_actions.async_record_container_harvest(
            self.hass,
            self._entry_id,
            mass_g=mass,
            confirm=True,
            is_final=self._is_final,
            return_to_fruiting=not self._is_final,
        )


class CommunifarmCreateVarietyButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Create variety"
    _attr_unique_id = "communifarm_create_variety"
    _attr_icon = "mdi:plus-box"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_create_variety"

    async def async_press(self) -> None:
        from homeassistant.exceptions import HomeAssistantError

        from . import culture_actions

        draft = str(
            self.hass.data[DOMAIN][self._entry_id].get("variety_name_draft") or ""
        ).strip()
        if not draft:
            raise HomeAssistantError("Enter a name in New variety name first")
        await culture_actions.async_create_variety(
            self.hass, self._entry_id, name=draft
        )


class CommunifarmRetireVarietyButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Retire custom variety"
    _attr_unique_id = "communifarm_retire_variety"
    _attr_icon = "mdi:archive"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_retire_variety"

    async def async_press(self) -> None:
        from homeassistant.exceptions import HomeAssistantError

        from . import culture_actions

        variety_id = self.hass.data[DOMAIN][self._entry_id].get("catalog_variety_id")
        if not variety_id:
            raise HomeAssistantError("Pick a Catalog variety first")
        await culture_actions.async_retire_variety(
            self.hass, self._entry_id, variety_id=str(variety_id)
        )


class CommunifarmAcquireCultureButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Acquire culture vessel"
    _attr_unique_id = "communifarm_acquire_culture"
    _attr_icon = "mdi:needle"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_acquire_culture"

    async def async_press(self) -> None:
        from homeassistant.exceptions import HomeAssistantError

        from . import culture_actions
        from .domain.culture import FORM_LIQUID_CULTURE, SOURCE_PURCHASED

        bucket = self.hass.data[DOMAIN][self._entry_id]
        variety_id = bucket.get("catalog_variety_id")
        if not variety_id:
            raise HomeAssistantError("Pick a Catalog variety first")
        await culture_actions.async_acquire_culture(
            self.hass,
            self._entry_id,
            source_type=str(bucket.get("acquire_source") or SOURCE_PURCHASED),
            form=str(bucket.get("acquire_form") or FORM_LIQUID_CULTURE),
            variety_id=str(variety_id),
        )


class CommunifarmSetCultureStatusButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Set culture vessel status"
    _attr_unique_id = "communifarm_set_culture_status"
    _attr_icon = "mdi:check-decagram"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_set_culture_status"

    async def async_press(self) -> None:
        from . import culture_actions
        from .domain.culture import CULTURE_STATUS_READY

        bucket = self.hass.data[DOMAIN][self._entry_id]
        status = str(bucket.get("culture_vessel_status") or CULTURE_STATUS_READY)
        await culture_actions.async_set_culture_status(
            self.hass, self._entry_id, status=status
        )


class CommunifarmRecordSaleButton(ButtonEntity):
    """Confirm POS sale using dashboard draft fields (weigh-at-sale or oldest open pack)."""

    _attr_has_entity_name = True
    _attr_name = "Confirm sale"
    _attr_unique_id = "communifarm_record_sale"
    _attr_icon = "mdi:point-of-sale"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_record_sale"

    async def async_press(self) -> None:
        from . import sale_actions

        bucket = self.hass.data[DOMAIN][self._entry_id]
        container_repo = bucket["container_repository"]
        open_packs = await container_repo.async_list_open_sale_packs()
        sale_pack_id = open_packs[-1].id if open_packs else None
        mass = float(bucket.get("sale_mass_g", 100.0) or 100.0)
        amount = float(bucket.get("sale_line_amount", 10.0) or 10.0)
        await sale_actions.async_record_sale(
            self.hass,
            self._entry_id,
            venue_label=str(bucket.get("sale_venue_label") or "Farmers market"),
            buyer_label=str(bucket.get("sale_buyer_label") or "Walk-up"),
            payment_method=str(bucket.get("payment_method") or "cash"),
            line_amount=amount,
            confirm=True,
            sale_pack_id=sale_pack_id,
            mass_g=None if sale_pack_id else mass,
            product_label=None,
        )


class CommunifarmRecordSaleCleanupButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Record sale cleanup"
    _attr_unique_id = "communifarm_record_sale_cleanup"
    _attr_icon = "mdi:broom"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "button.communifarm_record_sale_cleanup"

    async def async_press(self) -> None:
        from . import sale_actions

        await sale_actions.async_record_sale_cleanup(self.hass, self._entry_id)
