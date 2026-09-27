"""Sensor platform for Communifarm."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_WEIGH_SESSION_UPDATED
from .domain.models import CommunifarmState
from .domain.recipe import build_weigh_session_progress
from .storage.weight_repository import WeightEventRepository


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Communifarm sensors."""
    state: CommunifarmState = hass.data[DOMAIN][entry.entry_id]["state"]
    async_add_entities(
        [
            CommunifarmBatchStageSensor(entry.entry_id, state),
            CommunifarmEnvironmentStatusSensor(entry.entry_id, state),
            CommunifarmBatchNfcUidSensor(entry.entry_id, state),
            CommunifarmWeighSessionSensor(entry.entry_id, state),
        ]
    )


class CommunifarmBatchStageSensor(SensorEntity):
    """Expose the current production batch stage."""

    _attr_has_entity_name = True
    _attr_name = "Batch stage"
    _attr_unique_id = "communifarm_batch_stage"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        self._entry_id = entry_id
        self._state = state
        self.entity_id = "sensor.communifarm_batch_stage"

    @property
    def native_value(self) -> str:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        return runtime.batch.stage

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        return {
            "batch_id": runtime.batch.id,
            "batch_nfc_uid": runtime.batch.nfc_uid,
            "batch_name": runtime.batch.name,
            "event_count": str(len(runtime.batch.events)),
        }


class CommunifarmEnvironmentStatusSensor(SensorEntity):
    """Simple environment health status for the dashboard."""

    _attr_has_entity_name = True
    _attr_name = "Environment status"
    _attr_unique_id = "communifarm_environment_status"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        self._entry_id = entry_id
        self._state = state
        self.entity_id = "sensor.communifarm_environment_status"

    @property
    def native_value(self) -> str:
        return "ok"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        return {
            "site": runtime.site.name,
            "environment": runtime.environment.name,
        }


class CommunifarmBatchNfcUidSensor(SensorEntity):
    """Batch UID written to NFC and followed until container split."""

    _attr_has_entity_name = True
    _attr_name = "Batch NFC UID"
    _attr_unique_id = "communifarm_batch_nfc_uid"
    _attr_icon = "mdi:nfc-variant"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        self._entry_id = entry_id
        self._state = state
        self.entity_id = "sensor.communifarm_batch_nfc_uid"

    @property
    def native_value(self) -> str:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        return runtime.batch.nfc_uid


class CommunifarmWeighSessionSensor(SensorEntity):
    """Publish current weigh-session progress from SQLite + scaled recipe."""

    _attr_has_entity_name = True
    _attr_name = "Weigh session"
    _attr_unique_id = "communifarm_weigh_session"
    _attr_icon = "mdi:clipboard-list"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        self._entry_id = entry_id
        self._state = state
        self.entity_id = "sensor.communifarm_weigh_session"
        self._progress_text = "Loading…"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh_from_db()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_WEIGH_SESSION_UPDATED,
                self._handle_session_updated,
            )
        )

    @callback
    def _handle_session_updated(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self.hass.async_create_task(self.async_refresh_from_db())

    async def async_refresh_from_db(self) -> None:
        runtime: CommunifarmState = self.hass.data[DOMAIN][self._entry_id]["state"]
        weight_repo: WeightEventRepository = self.hass.data[DOMAIN][self._entry_id][
            "weight_repository"
        ]
        events = await weight_repo.async_list_for_batch(runtime.batch.id)
        progress = build_weigh_session_progress(
            batch_id=runtime.batch.id,
            batch_nfc_uid=runtime.batch.nfc_uid,
            recipe_scale=runtime.recipe_scale,
            events=events,
        )
        self._progress_text = progress.progress_text()
        self._attrs = {
            "summary": progress.summary,
            "recipe_name": progress.recipe_name,
            "recipe_scale": progress.recipe_scale,
            "batch_id": progress.batch_id,
            "batch_nfc_uid": progress.batch_nfc_uid,
            "completed": progress.completed,
            "total": progress.total,
            "next_label": progress.next_label,
            "progress_text": self._progress_text,
            "lines": [line.to_attr_dict() for line in progress.lines],
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return str(self._attrs.get("summary", "0/0 lines recorded"))

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs
