"""Button platform — mix / batch milestone actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
