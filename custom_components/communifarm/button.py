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
