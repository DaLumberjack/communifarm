"""Sensor platform for Communifarm."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ROLE_HUMIDITY, ROLE_TEMPERATURE, SIGNAL_WEIGH_SESSION_UPDATED
from .domain.models import CommunifarmState
from .domain.recipe import build_weigh_session_progress
from .domain.validation import assess_environment_readings
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


def _parse_float_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


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
    """Environment health from bound sensors (absolute range checks)."""

    _attr_has_entity_name = True
    _attr_name = "Environment status"
    _attr_unique_id = "communifarm_environment_status"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        self._entry_id = entry_id
        self._state = state
        self.entity_id = "sensor.communifarm_environment_status"

    def _assessment(self):
        runtime: CommunifarmState = self.hass.data[DOMAIN][self._entry_id]["state"]
        temp_binding = runtime.binding_for(ROLE_TEMPERATURE)
        hum_binding = runtime.binding_for(ROLE_HUMIDITY)
        temp = _parse_float_state(
            self.hass, temp_binding.entity_id if temp_binding else None
        )
        hum = _parse_float_state(
            self.hass, hum_binding.entity_id if hum_binding else None
        )
        return assess_environment_readings(temp, hum)

    @property
    def native_value(self) -> str:
        assessment = self._assessment()
        return "ok" if assessment.ok else "degraded"

    @property
    def extra_state_attributes(self) -> dict:
        runtime = self.hass.data[DOMAIN][self._entry_id]["state"]
        assessment = self._assessment()
        return {
            "site": runtime.site.name,
            "environment": runtime.environment.name,
            "warnings": list(assessment.warnings),
            "temperature_c": assessment.temperature_c,
            "humidity_pct": assessment.humidity_pct,
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
        session = self.hass.data[DOMAIN][self._entry_id].get("weigh_session", {})
        events = await weight_repo.async_list_for_batch(runtime.batch.id)
        progress = build_weigh_session_progress(
            batch_id=runtime.batch.id,
            batch_nfc_uid=runtime.batch.nfc_uid,
            recipe_scale=runtime.recipe_scale,
            events=events,
        )
        warnings = list(session.get("warnings") or [])
        last_reject = session.get("last_reject")
        self._progress_text = progress.progress_text()
        if warnings:
            self._progress_text += "\n\n**Warnings:** " + ", ".join(warnings)
        if last_reject:
            self._progress_text += f"\n\n**Last reject:** {last_reject}"
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
            "warnings": warnings,
            "warning": warnings[0] if warnings else None,
            "last_reject": last_reject,
            "tare_seen": bool(session.get("tare_seen")),
            "record_count": int(session.get("record_count") or 0),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return str(self._attrs.get("summary", "0/0 lines recorded"))

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs
