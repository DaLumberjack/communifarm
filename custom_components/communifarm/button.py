"""Button platform — mix / batch / production milestone actions."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ENTITY_BTN_ACQUIRE_CULTURE,
    ENTITY_BTN_COMPLETE_NEW_BATCH,
    ENTITY_BTN_COMPLETELY_MIXED,
    ENTITY_BTN_CONFIRM_CONTAINER_HARVEST,
    ENTITY_BTN_CONFIRM_FINAL_CONTAINER_HARVEST,
    ENTITY_BTN_CREATE_VARIETY,
    ENTITY_BTN_DRY_WET_MIX,
    ENTITY_BTN_FIELD_CAPACITY,
    ENTITY_BTN_FINAL_HARVEST,
    ENTITY_BTN_HEAT_TREATED,
    ENTITY_BTN_INOCULATE,
    ENTITY_BTN_MOVE_FRUITING,
    ENTITY_BTN_MOVE_HARVEST,
    ENTITY_BTN_MOVE_INCUBATION,
    ENTITY_BTN_NFC_CHECKIN_HARVEST,
    ENTITY_BTN_PRODUCTION_START,
    ENTITY_BTN_RECORD_HARVEST,
    ENTITY_BTN_RECORD_SALE,
    ENTITY_BTN_RECORD_SALE_CLEANUP,
    ENTITY_BTN_RETIRE_VARIETY,
    ENTITY_BTN_SELECT_INOCULUM_NFC,
    ENTITY_BTN_SEPARATE_CONTAINERS,
    ENTITY_BTN_SET_CULTURE_STATUS,
    ENTITY_BTN_SETTLING,
    ENTITY_BTN_STORED_COOLING,
    ENTITY_BTN_WATER_ADDED,
)
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
from .domain.culture import CULTURE_STATUS_READY, FORM_LIQUID_CULTURE, SOURCE_PURCHASED
from .domain.nfc import ACTIVITY_HARVEST
from .domain.production import (
    CONTAINER_BAG,
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INCUBATING,
)
from .entity import CommunifarmEntity


@dataclass(frozen=True, slots=True)
class _ButtonSpec:
    """Identity for a button whose press behavior is shared."""

    name: str
    unique_id: str
    entity_id: str
    icon: str


class CommunifarmButton(CommunifarmEntity, ButtonEntity):
    """Button identity and entry bucket. Override ``async_press``."""


class CommunifarmMilestoneButton(CommunifarmButton):
    """Record one mix milestone. Several buttons share this press path."""

    def __init__(self, entry_id: str, spec: _ButtonSpec, event_type: str) -> None:
        super().__init__(
            entry_id,
            name=spec.name,
            unique_id=spec.unique_id,
            entity_id=spec.entity_id,
            icon=spec.icon,
        )
        self._event_type = event_type

    async def async_press(self) -> None:
        from . import batch_actions

        await batch_actions.async_record_milestone(
            self.hass, self._entry_id, self._event_type
        )


class CommunifarmAdvanceStageButton(CommunifarmButton):
    """Move the active batch to a production stage."""

    def __init__(self, entry_id: str, spec: _ButtonSpec, target_stage: str) -> None:
        super().__init__(
            entry_id,
            name=spec.name,
            unique_id=spec.unique_id,
            entity_id=spec.entity_id,
            icon=spec.icon,
        )
        self._target_stage = target_stage

    async def async_press(self) -> None:
        from . import production_actions

        await production_actions.async_advance_production_stage(
            self.hass, self._entry_id, target_stage=self._target_stage
        )


def _spec(name: str, unique_id: str, entity_id: str, icon: str) -> _ButtonSpec:
    return _ButtonSpec(name, unique_id, entity_id, icon)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entry_id = entry.entry_id
    async_add_entities(
        [
            CommunifarmMilestoneButton(
                entry_id,
                _spec(
                    "Water added",
                    "communifarm_water_added",
                    ENTITY_BTN_WATER_ADDED,
                    "mdi:water",
                ),
                MILESTONE_WATER_ADDED,
            ),
            CommunifarmMilestoneButton(
                entry_id,
                _spec(
                    "Started dry/wet mix",
                    "communifarm_dry_wet_mix_started",
                    ENTITY_BTN_DRY_WET_MIX,
                    "mdi:blender",
                ),
                MILESTONE_DRY_WET_MIX_STARTED,
            ),
            CommunifarmMilestoneButton(
                entry_id,
                _spec(
                    "Settling",
                    "communifarm_settling_started",
                    ENTITY_BTN_SETTLING,
                    "mdi:timer-sand",
                ),
                MILESTONE_SETTLING_STARTED,
            ),
            CommunifarmMilestoneButton(
                entry_id,
                _spec(
                    "Reached field capacity",
                    "communifarm_field_capacity_reached",
                    ENTITY_BTN_FIELD_CAPACITY,
                    "mdi:water-check",
                ),
                MILESTONE_FIELD_CAPACITY_REACHED,
            ),
            CommunifarmMilestoneButton(
                entry_id,
                _spec(
                    "Completely mixed",
                    "communifarm_completely_mixed",
                    ENTITY_BTN_COMPLETELY_MIXED,
                    "mdi:check-decagram",
                ),
                MILESTONE_COMPLETELY_MIXED,
            ),
            CommunifarmSeparateContainersButton(entry_id),
            CommunifarmHeatTreatedButton(entry_id),
            CommunifarmMilestoneButton(
                entry_id,
                _spec(
                    "Stored for cooling",
                    "communifarm_stored_for_cooling",
                    ENTITY_BTN_STORED_COOLING,
                    "mdi:snowflake-thermometer",
                ),
                MILESTONE_STORED_FOR_COOLING,
            ),
            CommunifarmMilestoneButton(
                entry_id,
                _spec(
                    "Production cycle start (stub)",
                    "communifarm_production_cycle_started",
                    ENTITY_BTN_PRODUCTION_START,
                    "mdi:sprout",
                ),
                MILESTONE_PRODUCTION_CYCLE_STARTED,
            ),
            CommunifarmCompleteAndNewBatchButton(entry_id),
            CommunifarmSelectInoculumFromNfcButton(entry_id),
            CommunifarmInoculateButton(entry_id),
            CommunifarmAdvanceStageButton(
                entry_id,
                _spec(
                    "Move to incubation",
                    "communifarm_move_to_incubation",
                    ENTITY_BTN_MOVE_INCUBATION,
                    "mdi:home-thermometer",
                ),
                STAGE_INCUBATING,
            ),
            CommunifarmAdvanceStageButton(
                entry_id,
                _spec(
                    "Move to fruiting",
                    "communifarm_move_to_fruiting",
                    ENTITY_BTN_MOVE_FRUITING,
                    "mdi:mushroom",
                ),
                STAGE_FRUITING,
            ),
            CommunifarmAdvanceStageButton(
                entry_id,
                _spec(
                    "Move to harvest",
                    "communifarm_move_to_harvest",
                    ENTITY_BTN_MOVE_HARVEST,
                    "mdi:basket",
                ),
                STAGE_HARVESTING,
            ),
            CommunifarmRecordHarvestButton(entry_id, is_final=False),
            CommunifarmRecordHarvestButton(entry_id, is_final=True),
            CommunifarmNfcCheckinHarvestButton(entry_id),
            CommunifarmConfirmContainerHarvestButton(entry_id, is_final=False),
            CommunifarmConfirmContainerHarvestButton(entry_id, is_final=True),
            CommunifarmCreateVarietyButton(entry_id),
            CommunifarmRetireVarietyButton(entry_id),
            CommunifarmAcquireCultureButton(entry_id),
            CommunifarmSetCultureStatusButton(entry_id),
            CommunifarmRecordSaleButton(entry_id),
            CommunifarmRecordSaleCleanupButton(entry_id),
        ]
    )


class CommunifarmSeparateContainersButton(CommunifarmButton):
    _attr_name = "Separate into containers"
    _attr_unique_id = "communifarm_separate_containers"
    _attr_icon = "mdi:package-variant-closed"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_SEPARATE_CONTAINERS)

    async def async_press(self) -> None:
        from . import batch_actions

        count = int(self.bucket().get("container_count", 1) or 1)
        await batch_actions.async_record_milestone(
            self.hass,
            self._entry_id,
            MILESTONE_CONTAINERS_SEPARATED,
            detail={"container_count": count},
        )


class CommunifarmHeatTreatedButton(CommunifarmButton):
    _attr_name = "Record heat treatment"
    _attr_unique_id = "communifarm_heat_treated"
    _attr_icon = "mdi:fire"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_HEAT_TREATED)

    async def async_press(self) -> None:
        from . import batch_actions

        method = self.bucket().get("heat_treatment", "pasteurized")
        await batch_actions.async_record_milestone(
            self.hass,
            self._entry_id,
            MILESTONE_HEAT_TREATED,
            detail={"method": method},
        )


class CommunifarmCompleteAndNewBatchButton(CommunifarmButton):
    _attr_name = "Complete batch & start new"
    _attr_unique_id = "communifarm_complete_and_new_batch"
    _attr_icon = "mdi:playlist-plus"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_COMPLETE_NEW_BATCH)

    async def async_press(self) -> None:
        from . import batch_actions

        await batch_actions.async_complete_and_new_batch(self.hass, self._entry_id)


class CommunifarmSelectInoculumFromNfcButton(CommunifarmButton):
    """Load active inoculum from input_text.esp32dev_last_nfc_uid (culture tag)."""

    _attr_name = "Select inoculum from NFC scan"
    _attr_unique_id = "communifarm_select_inoculum_from_nfc"
    _attr_icon = "mdi:nfc-variant"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_SELECT_INOCULUM_NFC)

    async def async_press(self) -> None:
        from . import culture_actions

        await culture_actions.async_select_inoculum_from_nfc_scan(
            self.hass, self._entry_id
        )


class CommunifarmInoculateButton(CommunifarmButton):
    _attr_name = "Inoculate batch"
    _attr_unique_id = "communifarm_inoculate_batch"
    _attr_icon = "mdi:needle"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_INOCULATE)

    async def async_press(self) -> None:
        from . import production_actions

        bucket = self.bucket()
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


class CommunifarmRecordHarvestButton(CommunifarmButton):
    def __init__(self, entry_id: str, *, is_final: bool) -> None:
        self._is_final = is_final
        if is_final:
            super().__init__(
                entry_id,
                name="Final harvest",
                unique_id="communifarm_final_harvest",
                entity_id=ENTITY_BTN_FINAL_HARVEST,
                icon="mdi:flag-checkered",
            )
        else:
            super().__init__(
                entry_id,
                name="Record harvest",
                unique_id="communifarm_record_harvest",
                entity_id=ENTITY_BTN_RECORD_HARVEST,
                icon="mdi:scale",
            )

    async def async_press(self) -> None:
        from . import production_actions

        mass = float(self.bucket().get("harvest_mass_g", 100.0) or 100.0)
        await production_actions.async_record_harvest(
            self.hass,
            self._entry_id,
            mass_g=mass,
            is_final=self._is_final,
        )


class CommunifarmNfcCheckinHarvestButton(CommunifarmButton):
    _attr_name = "NFC check-in harvest"
    _attr_unique_id = "communifarm_nfc_checkin_harvest"
    _attr_icon = "mdi:nfc-variant"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_NFC_CHECKIN_HARVEST)

    async def async_press(self) -> None:
        from . import nfc_actions

        await nfc_actions.async_check_in(
            self.hass, self._entry_id, activity=ACTIVITY_HARVEST
        )


class CommunifarmConfirmContainerHarvestButton(CommunifarmButton):
    def __init__(self, entry_id: str, *, is_final: bool) -> None:
        self._is_final = is_final
        if is_final:
            super().__init__(
                entry_id,
                name="Confirm final container harvest",
                unique_id="communifarm_confirm_final_container_harvest",
                entity_id=ENTITY_BTN_CONFIRM_FINAL_CONTAINER_HARVEST,
                icon="mdi:flag-checkered",
            )
        else:
            super().__init__(
                entry_id,
                name="Confirm container harvest",
                unique_id="communifarm_confirm_container_harvest",
                entity_id=ENTITY_BTN_CONFIRM_CONTAINER_HARVEST,
                icon="mdi:check-circle",
            )

    async def async_press(self) -> None:
        from . import production_actions

        mass = float(self.bucket().get("harvest_mass_g", 100.0) or 100.0)
        await production_actions.async_record_container_harvest(
            self.hass,
            self._entry_id,
            mass_g=mass,
            confirm=True,
            is_final=self._is_final,
            return_to_fruiting=not self._is_final,
        )


class CommunifarmCreateVarietyButton(CommunifarmButton):
    _attr_name = "Create variety"
    _attr_unique_id = "communifarm_create_variety"
    _attr_icon = "mdi:plus-box"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_CREATE_VARIETY)

    async def async_press(self) -> None:
        from . import culture_actions

        draft = str(self.bucket().get("variety_name_draft") or "").strip()
        if not draft:
            raise HomeAssistantError("Enter a name in New variety name first")
        await culture_actions.async_create_variety(
            self.hass, self._entry_id, name=draft
        )


class CommunifarmRetireVarietyButton(CommunifarmButton):
    _attr_name = "Retire custom variety"
    _attr_unique_id = "communifarm_retire_variety"
    _attr_icon = "mdi:archive"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_RETIRE_VARIETY)

    async def async_press(self) -> None:
        from . import culture_actions

        variety_id = self.bucket().get("catalog_variety_id")
        if not variety_id:
            raise HomeAssistantError("Pick a Catalog variety first")
        await culture_actions.async_retire_variety(
            self.hass, self._entry_id, variety_id=str(variety_id)
        )


class CommunifarmAcquireCultureButton(CommunifarmButton):
    _attr_name = "Acquire culture vessel"
    _attr_unique_id = "communifarm_acquire_culture"
    _attr_icon = "mdi:needle"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_ACQUIRE_CULTURE)

    async def async_press(self) -> None:
        from . import culture_actions

        bucket = self.bucket()
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


class CommunifarmSetCultureStatusButton(CommunifarmButton):
    _attr_name = "Set culture vessel status"
    _attr_unique_id = "communifarm_set_culture_status"
    _attr_icon = "mdi:check-decagram"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_SET_CULTURE_STATUS)

    async def async_press(self) -> None:
        from . import culture_actions

        status = str(self.bucket().get("culture_vessel_status") or CULTURE_STATUS_READY)
        await culture_actions.async_set_culture_status(
            self.hass, self._entry_id, status=status
        )


class CommunifarmRecordSaleButton(CommunifarmButton):
    """Confirm POS sale using dashboard draft fields (weigh-at-sale or oldest open pack)."""

    _attr_name = "Confirm sale"
    _attr_unique_id = "communifarm_record_sale"
    _attr_icon = "mdi:point-of-sale"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_RECORD_SALE)

    async def async_press(self) -> None:
        from . import sale_actions

        bucket = self.bucket()
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


class CommunifarmRecordSaleCleanupButton(CommunifarmButton):
    _attr_name = "Record sale cleanup"
    _attr_unique_id = "communifarm_record_sale_cleanup"
    _attr_icon = "mdi:broom"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BTN_RECORD_SALE_CLEANUP)

    async def async_press(self) -> None:
        from . import sale_actions

        await sale_actions.async_record_sale_cleanup(self.hass, self._entry_id)
