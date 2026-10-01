"""Sensor platform for Communifarm."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ROLE_HUMIDITY,
    ROLE_TEMPERATURE,
    SIGNAL_BATCH_UPDATED,
    SIGNAL_NFC_CHECKIN_UPDATED,
    SIGNAL_SALES_UPDATED,
    SIGNAL_WEIGH_SESSION_UPDATED,
)
from .domain.models import CommunifarmState
from .domain.recipe import build_weigh_session_progress
from .domain.validation import assess_environment_readings
from .storage.batch_repository import BatchRepository
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
            CommunifarmBatchListSensor(entry.entry_id),
            CommunifarmBatchMilestonesSensor(entry.entry_id),
            CommunifarmProductionStatusSensor(entry.entry_id),
            CommunifarmNfcCheckinSensor(entry.entry_id),
            CommunifarmSalesStatusSensor(entry.entry_id),
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


class CommunifarmBatchListSensor(SensorEntity):
    """Historical + active batches with mix start/finish times."""

    _attr_has_entity_name = True
    _attr_name = "Batch list"
    _attr_unique_id = "communifarm_batch_list"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "sensor.communifarm_batch_list"
        self._value = "0 batches"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_BATCH_UPDATED, self._on_update
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_WEIGH_SESSION_UPDATED, self._on_update
            )
        )

    @callback
    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self.hass.async_create_task(self.async_refresh())

    async def async_refresh(self) -> None:
        runtime: CommunifarmState = self.hass.data[DOMAIN][self._entry_id]["state"]
        batch_repo: BatchRepository = self.hass.data[DOMAIN][self._entry_id][
            "batch_repository"
        ]
        batches = await batch_repo.async_list_batches()
        self._value = f"{len(batches)} batches"
        self._attrs = {
            "active_batch_id": runtime.batch.id,
            "active_batch_name": runtime.batch.name,
            "batches": [b.to_attr_dict() for b in batches],
            "list_text": BatchRepository.format_batch_list_text(batches),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmBatchMilestonesSensor(SensorEntity):
    """Milestones for the active batch."""

    _attr_has_entity_name = True
    _attr_name = "Batch milestones"
    _attr_unique_id = "communifarm_batch_milestones"
    _attr_icon = "mdi:timeline-clock"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "sensor.communifarm_batch_milestones"
        self._value = "0 milestones"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_BATCH_UPDATED, self._on_update
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_WEIGH_SESSION_UPDATED, self._on_update
            )
        )

    @callback
    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self.hass.async_create_task(self.async_refresh())

    async def async_refresh(self) -> None:
        runtime: CommunifarmState = self.hass.data[DOMAIN][self._entry_id]["state"]
        batch_repo: BatchRepository = self.hass.data[DOMAIN][self._entry_id][
            "batch_repository"
        ]
        milestones = await batch_repo.async_list_milestones(runtime.batch.id)
        types = [m.event_type for m in milestones]
        self._value = f"{len(milestones)} milestones"
        lines = [
            "| When | Event | Detail |",
            "| --- | --- | --- |",
        ]
        for m in milestones:
            detail = m.detail or {}
            detail_s = ", ".join(f"{k}={v}" for k, v in detail.items()) or "—"
            lines.append(f"| {m.recorded_at} | {m.event_type} | {detail_s} |")
        self._attrs = {
            "batch_id": runtime.batch.id,
            "event_types": types,
            "milestones": [m.to_attr_dict() for m in milestones],
            "progress_text": "\n".join(lines) if milestones else "_No milestones yet._",
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmProductionStatusSensor(SensorEntity):
    """Production inoculate / harvest status for the active batch."""

    _attr_has_entity_name = True
    _attr_name = "Production status"
    _attr_unique_id = "communifarm_production_status"
    _attr_icon = "mdi:mushroom"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "sensor.communifarm_production_status"
        self._value = "planned"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_BATCH_UPDATED, self._on_update
            )
        )

    @callback
    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self.hass.async_create_task(self.async_refresh())

    async def async_refresh(self) -> None:
        from . import production_actions

        summary = await production_actions.async_production_summary(
            self.hass, self._entry_id
        )
        self._value = summary.lifecycle_phase
        self._attrs = {
            **summary.to_dict(),
            "progress_text": production_actions.production_summary_markdown(summary),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmNfcCheckinSensor(SensorEntity):
    """Last handheld NFC resolve / check-in context for harvest."""

    _attr_has_entity_name = True
    _attr_name = "NFC check-in"
    _attr_unique_id = "communifarm_nfc_checkin"
    _attr_icon = "mdi:nfc"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "sensor.communifarm_nfc_checkin"
        self._value = "idle"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        self._refresh()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_NFC_CHECKIN_UPDATED, self._on_update
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_BATCH_UPDATED, self._on_update
            )
        )

    @callback
    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self._refresh()

    def _refresh(self) -> None:
        session = self.hass.data[DOMAIN][self._entry_id].get("nfc_session") or {}
        if session.get("found"):
            self._value = f"{session.get('object_type')}:{session.get('object_id')}"
        elif session.get("nfc_uid"):
            self._value = "not_found"
        else:
            self._value = "idle"
        self._attrs = {
            "nfc_uid": session.get("nfc_uid"),
            "object_type": session.get("object_type"),
            "object_id": session.get("object_id"),
            "container_id": session.get("container_id"),
            "activity": session.get("activity"),
            "batch_id": session.get("batch_id"),
            "zone_id": session.get("zone_id"),
            "label": session.get("label"),
            "lifecycle_phase": session.get("lifecycle_phase"),
            "flush_count": session.get("flush_count"),
            "max_flushes": session.get("max_flushes"),
            "found": bool(session.get("found")),
            "checkin_id": session.get("checkin_id"),
            "progress_text": session.get("progress_text")
            or "Scan a tag with the handheld reader.",
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmSalesStatusSensor(SensorEntity):
    """POS sales snapshot — updates when sales or cleanup are recorded."""

    _attr_has_entity_name = True
    _attr_name = "Sales status"
    _attr_unique_id = "communifarm_sales_status"
    _attr_icon = "mdi:point-of-sale"

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self.entity_id = "sensor.communifarm_sales_status"
        self._value = "idle"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_SALES_UPDATED, self._on_update
            )
        )

    @callback
    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry_id:
            return
        self.hass.async_create_task(self.async_refresh())

    async def async_refresh(self) -> None:
        from . import sale_actions

        summary = await sale_actions.async_sales_summary(self.hass, self._entry_id)
        last = summary.get("last_sale") or {}
        self._value = last.get("id") if last else "idle"
        self._attrs = summary
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs
