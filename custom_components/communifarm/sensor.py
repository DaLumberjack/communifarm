"""Sensor platform for Communifarm."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .climate_entities import drawing_sensor_entities
from .const import (
    BATCH_LIST_WIDGET_LIMIT,
    DOMAIN,
    ENTITY_ACTIVE_CULTURE_ID,
    ENTITY_BATCH_LIST,
    ENTITY_BATCH_MILESTONES,
    ENTITY_BATCH_NFC_UID,
    ENTITY_BATCH_STAGE,
    ENTITY_CLIMATE_STATUS,
    ENTITY_CULTURE_INVENTORY,
    ENTITY_FIELD_CAPACITY,
    ENTITY_FIELD_CAPACITY_RAW,
    ENTITY_MIX_PROTOCOL,
    ENTITY_NFC_CHECKIN,
    ENTITY_NFC_WRITE_STATUS,
    ENTITY_PLACEMENT_COLD_STORAGE,
    ENTITY_PLACEMENT_FRUITING_TENT,
    ENTITY_PLACEMENT_INOCULATION_TENT,
    ENTITY_PLACEMENT_STORAGE,
    ENTITY_PRODUCTION_STATUS,
    ENTITY_SALES_STATUS,
    ENTITY_TACHOMETER_STATUS,
    ENTITY_VARIETY_LIST,
    ENTITY_WEIGH_SESSION,
    FIELD_CAPACITY_MAX_OK,
    FIELD_CAPACITY_MIN_OK,
    ROLE_HUMIDITY,
    ROLE_TEMPERATURE,
    SIGNAL_BATCH_UPDATED,
    SIGNAL_CLIMATE_UPDATED,
    SIGNAL_CULTURE_UPDATED,
    SIGNAL_NFC_CHECKIN_UPDATED,
    SIGNAL_SALES_UPDATED,
    SIGNAL_TACHOMETER_UPDATED,
    SIGNAL_WEIGH_SESSION_UPDATED,
)
from .domain.location import (
    AREA_COLD_STORAGE,
    AREA_FRUITING_TENT,
    AREA_INOCULATION_TENT,
    AREA_STORAGE,
)
from .domain.models import CommunifarmState
from .domain.recipe import build_weigh_session_progress
from .domain.validation import assess_environment_readings
from .entity import CommunifarmEntity
from .storage.batch_repository import BatchRepository
from .storage.culture_repository import CultureRepository
from .storage.weight_repository import WeightEventRepository


class CommunifarmSensor(CommunifarmEntity, SensorEntity):
    """Sensor identity, entry bucket, and optional cached domain state."""

    def __init__(
        self,
        entry_id: str,
        state: CommunifarmState | None = None,
        *,
        entity_id: str,
    ) -> None:
        super().__init__(entry_id, entity_id=entity_id)
        self._state = state


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Communifarm sensors."""
    state: CommunifarmState = hass.data[DOMAIN][entry.entry_id]["state"]
    entry_id = entry.entry_id
    async_add_entities(
        [
            CommunifarmBatchStageSensor(entry_id, state),
            CommunifarmEnvironmentStatusSensor(entry_id, state),
            CommunifarmBatchNfcUidSensor(entry_id, state),
            CommunifarmWeighSessionSensor(entry_id, state),
            CommunifarmMixProtocolSensor(entry_id, state),
            CommunifarmNfcWriteStatusSensor(entry_id),
            CommunifarmFieldCapacitySensor(entry_id),
            CommunifarmBatchListSensor(entry_id),
            CommunifarmBatchMilestonesSensor(entry_id),
            CommunifarmProductionStatusSensor(entry_id),
            CommunifarmPlacementInventorySensor(
                entry_id,
                area_kind=AREA_STORAGE,
                title="Storage",
                unique_id="communifarm_placement_storage",
                entity_id=ENTITY_PLACEMENT_STORAGE,
                icon="mdi:warehouse",
            ),
            CommunifarmPlacementInventorySensor(
                entry_id,
                area_kind=AREA_COLD_STORAGE,
                title="Cold storage",
                unique_id="communifarm_placement_cold_storage",
                entity_id=ENTITY_PLACEMENT_COLD_STORAGE,
                icon="mdi:snowflake",
            ),
            CommunifarmPlacementInventorySensor(
                entry_id,
                area_kind=AREA_FRUITING_TENT,
                title="Fruiting tent",
                unique_id="communifarm_placement_fruiting_tent",
                entity_id=ENTITY_PLACEMENT_FRUITING_TENT,
                icon="mdi:tent",
            ),
            CommunifarmPlacementInventorySensor(
                entry_id,
                area_kind=AREA_INOCULATION_TENT,
                title="Inoculation tent",
                unique_id="communifarm_placement_inoculation_tent",
                entity_id=ENTITY_PLACEMENT_INOCULATION_TENT,
                icon="mdi:greenhouse",
            ),
            CommunifarmActiveCultureIdSensor(entry_id),
            CommunifarmVarietyListSensor(entry_id),
            CommunifarmCultureInventorySensor(entry_id),
            CommunifarmNfcCheckinSensor(entry_id),
            CommunifarmSalesStatusSensor(entry_id),
            CommunifarmClimateStatusSensor(entry_id),
            CommunifarmTachometerStatusSensor(entry_id),
            *drawing_sensor_entities(entry_id),
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


class CommunifarmBatchStageSensor(CommunifarmSensor):
    """Expose the current production batch stage."""

    _attr_name = "Batch stage"
    _attr_unique_id = "communifarm_batch_stage"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        super().__init__(entry_id, state, entity_id=ENTITY_BATCH_STAGE)

    @property
    def native_value(self) -> str:
        return self.runtime_state().batch.stage

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        runtime = self.runtime_state()
        return {
            "batch_id": runtime.batch.id,
            "batch_nfc_uid": runtime.batch.nfc_uid,
            "batch_name": runtime.batch.name,
            "event_count": str(len(runtime.batch.events)),
        }


class CommunifarmEnvironmentStatusSensor(CommunifarmSensor):
    """Environment health from bound sensors (absolute range checks)."""

    _attr_name = "Environment status"
    _attr_unique_id = "communifarm_environment_status"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        super().__init__(entry_id, state, entity_id="sensor.communifarm_environment_status")

    def _assessment(self):
        runtime = self.runtime_state()
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
        runtime = self.runtime_state()
        assessment = self._assessment()
        return {
            "site": runtime.site.name,
            "environment": runtime.environment.name,
            "warnings": list(assessment.warnings),
            "temperature_c": assessment.temperature_c,
            "humidity_pct": assessment.humidity_pct,
        }


class CommunifarmBatchNfcUidSensor(CommunifarmSensor):
    """Batch UID written to NFC and followed until container split."""

    _attr_name = "Batch NFC UID"
    _attr_unique_id = "communifarm_batch_nfc_uid"
    _attr_icon = "mdi:nfc-variant"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        super().__init__(entry_id, state, entity_id=ENTITY_BATCH_NFC_UID)

    @property
    def native_value(self) -> str:
        return self.runtime_state().batch.nfc_uid


class CommunifarmWeighSessionSensor(CommunifarmSensor):
    """Publish current weigh-session progress from SQLite + scaled recipe."""

    _attr_name = "Weigh session"
    _attr_unique_id = "communifarm_weigh_session"
    _attr_icon = "mdi:clipboard-list"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        super().__init__(entry_id, state, entity_id=ENTITY_WEIGH_SESSION)
        self._progress_text = "Loading…"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh_from_db()
        self.listen_entry_signals(
            SIGNAL_WEIGH_SESSION_UPDATED, method="async_refresh_from_db"
        )

    async def async_refresh_from_db(self) -> None:
        runtime = self.runtime_state()
        weight_repo: WeightEventRepository = self.bucket()["weight_repository"]
        session = self.bucket().get("weigh_session", {})
        events = await weight_repo.async_list_for_batch(runtime.batch.id)
        progress = build_weigh_session_progress(
            batch_id=runtime.batch.id,
            batch_nfc_uid=runtime.batch.nfc_uid,
            recipe_scale=runtime.recipe_scale,
            events=events,
        )
        from .const import ENTITY_MANUAL_WEIGH_G, ENTITY_SCALE_MASS_G, MANUAL_WEIGH_OMIT_G
        from .domain.validation import ValidationError
        from .domain.weight import resolve_weigh_mass_g

        warnings = list(session.get("warnings") or [])
        last_reject = session.get("last_reject")
        manual_raw = self.bucket().get("manual_weigh_g", MANUAL_WEIGH_OMIT_G)
        scale_state = self.hass.states.get(ENTITY_SCALE_MASS_G)
        scale_g = None
        if scale_state is not None and scale_state.state not in (
            "unknown",
            "unavailable",
            "",
        ):
            try:
                scale_g = float(scale_state.state)
            except (TypeError, ValueError):
                scale_g = None
        try:
            resolved = resolve_weigh_mass_g(manual_g=manual_raw, scale_g=scale_g)
            effective_mass = resolved.mass_g
            mass_source = resolved.source
        except ValidationError:
            effective_mass = None
            mass_source = None
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
            "dry_progress_text": progress.dry_progress_text(),
            "wet_progress_text": progress.wet_progress_text(),
            "lines": [line.to_attr_dict() for line in progress.lines],
            "warnings": warnings,
            "warning": warnings[0] if warnings else None,
            "last_reject": last_reject,
            "tare_seen": bool(session.get("tare_seen")),
            "record_count": int(session.get("record_count") or 0),
            "manual_weigh_g": manual_raw,
            "scale_mass_g": scale_g,
            "effective_mass_g": effective_mass,
            "mass_source": mass_source,
            "manual_weigh_entity": ENTITY_MANUAL_WEIGH_G,
            "last_mass_source": session.get("last_mass_source"),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return str(self._attrs.get("summary", "0/0 lines recorded"))

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmMixProtocolSensor(CommunifarmSensor):
    """Ordered mix-batch checklist (task-focused, not general scale use)."""

    _attr_name = "Mix protocol"
    _attr_unique_id = "communifarm_mix_protocol"
    _attr_icon = "mdi:format-list-checks"

    def __init__(self, entry_id: str, state: CommunifarmState) -> None:
        super().__init__(entry_id, state, entity_id=ENTITY_MIX_PROTOCOL)
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(
            SIGNAL_BATCH_UPDATED,
            SIGNAL_WEIGH_SESSION_UPDATED,
            method="async_refresh",
        )

    async def async_refresh(self) -> None:
        from . import inventory_actions

        progress = await inventory_actions.async_mix_protocol_snapshot(
            self.hass, self._entry_id
        )
        self._attrs = {
            "summary": progress.summary,
            "batch_id": progress.batch_id,
            "completed": progress.completed,
            "total": progress.total,
            "section": progress.section,
            "next_key": progress.next_key,
            "next_label": progress.next_label,
            "last_done_key": progress.last_done_key,
            "last_done_label": progress.last_done_label,
            "dry_weigh_done": progress.dry_weigh_done,
            "field_capacity_ok": progress.field_capacity_ok,
            "focus_text": progress.focus_text(),
            "progress_text": progress.progress_text(),
            "steps": [s.to_attr_dict() for s in progress.steps],
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return str(self._attrs.get("summary", "0/0 mix steps"))

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmNfcWriteStatusSensor(CommunifarmSensor):
    """Pending NDEF payload for the lab NFC writer."""

    _attr_name = "NFC write status"
    _attr_unique_id = "communifarm_nfc_write_status"
    _attr_icon = "mdi:nfc-variant"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_NFC_WRITE_STATUS)
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(SIGNAL_NFC_CHECKIN_UPDATED, method="async_refresh")

    async def async_refresh(self) -> None:
        pending = dict(self.bucket().get("pending_nfc_write") or {})
        self._attrs = pending
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return str(self._attrs.get("status") or "idle")

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmFieldCapacitySensor(CommunifarmSensor):
    """Mirror mix-room capacitance reading + calibration band status."""

    _attr_name = "Field capacity"
    _attr_unique_id = "communifarm_field_capacity"
    _attr_icon = "mdi:water-percent"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_FIELD_CAPACITY)
        self._value: float | None = None
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(SIGNAL_BATCH_UPDATED, method="async_refresh")

    async def async_refresh(self) -> None:
        from .inventory_actions import assess_field_capacity_reading

        raw = None
        state = self.hass.states.get(ENTITY_FIELD_CAPACITY_RAW)
        if state is not None and state.state not in ("unknown", "unavailable", ""):
            try:
                raw = float(state.state)
            except (TypeError, ValueError):
                raw = None
        ok, warning = assess_field_capacity_reading(
            raw, min_ok=FIELD_CAPACITY_MIN_OK, max_ok=FIELD_CAPACITY_MAX_OK
        )
        self.bucket()["field_capacity_ok"] = ok
        self._value = raw
        self._attrs = {
            "in_band": ok,
            "warning": warning,
            "min_ok": FIELD_CAPACITY_MIN_OK,
            "max_ok": FIELD_CAPACITY_MAX_OK,
            "note": (
                "Salts skew capacitance; calibrate band for this substrate before "
                "trusting field-capacity automation."
            ),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmBatchListSensor(CommunifarmSensor):
    """Historical + active batches with mix start/finish times."""

    _attr_name = "Batch list"
    _attr_unique_id = "communifarm_batch_list"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BATCH_LIST)
        self._value = "0 batches"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(
            SIGNAL_BATCH_UPDATED,
            SIGNAL_WEIGH_SESSION_UPDATED,
            method="async_refresh",
        )

    async def async_refresh(self) -> None:
        runtime = self.runtime_state()
        batch_repo: BatchRepository = self.bucket()["batch_repository"]
        # async_list_batches is newest-first; widget shows a fixed recent window.
        all_batches = await batch_repo.async_list_batches()
        batches = all_batches[:BATCH_LIST_WIDGET_LIMIT]
        total = len(all_batches)
        if total > BATCH_LIST_WIDGET_LIMIT:
            self._value = f"{total} batches (latest {BATCH_LIST_WIDGET_LIMIT})"
        else:
            self._value = f"{total} batches"
        self._attrs = {
            "active_batch_id": runtime.batch.id,
            "active_batch_name": runtime.batch.name,
            "total_batches": total,
            "limit": BATCH_LIST_WIDGET_LIMIT,
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


class CommunifarmBatchMilestonesSensor(CommunifarmSensor):
    """Milestones for the active batch."""

    _attr_name = "Batch milestones"
    _attr_unique_id = "communifarm_batch_milestones"
    _attr_icon = "mdi:timeline-clock"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_BATCH_MILESTONES)
        self._value = "0 milestones"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(
            SIGNAL_BATCH_UPDATED,
            SIGNAL_WEIGH_SESSION_UPDATED,
            method="async_refresh",
        )

    async def async_refresh(self) -> None:
        runtime = self.runtime_state()
        batch_repo: BatchRepository = self.bucket()["batch_repository"]
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


class CommunifarmProductionStatusSensor(CommunifarmSensor):
    """Production inoculate / harvest status for the active batch."""

    _attr_name = "Production status"
    _attr_unique_id = "communifarm_production_status"
    _attr_icon = "mdi:mushroom"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_PRODUCTION_STATUS)
        self._value = "planned"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(SIGNAL_BATCH_UPDATED, method="async_refresh")

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


class CommunifarmPlacementInventorySensor(CommunifarmSensor):
    """Markdown inventory of bags/boxes in one placement area kind."""

    def __init__(
        self,
        entry_id: str,
        *,
        area_kind: str,
        title: str,
        unique_id: str,
        entity_id: str,
        icon: str,
    ) -> None:
        super().__init__(entry_id, entity_id=entity_id)
        self._attr_name = f"Placement — {title}"
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self._area_kind = area_kind
        self._title = title
        self._value = "0 units"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(SIGNAL_BATCH_UPDATED, method="async_refresh")
        self.listen_entry_signals(SIGNAL_NFC_CHECKIN_UPDATED, method="async_refresh")

    async def async_refresh(self) -> None:
        from . import production_actions

        if self._entry_id not in self.hass.data.get(DOMAIN, {}):
            return
        value, markdown, rows = await production_actions.async_placement_section(
            self.hass, self._entry_id, self._area_kind, self._title
        )
        self._value = value
        self._attrs = {
            "area_kind": self._area_kind,
            "area_title": self._title,
            "count": len(rows),
            "containers": rows,
            "progress_text": markdown,
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmActiveCultureIdSensor(CommunifarmSensor):
    """Stable id of the culture lot selected for inoculation."""

    _attr_name = "Active culture id"
    _attr_unique_id = "communifarm_active_culture_id"
    _attr_icon = "mdi:identifier"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_ACTIVE_CULTURE_ID)

    async def async_added_to_hass(self) -> None:
        self._refresh()
        self.listen_entry_signals(SIGNAL_CULTURE_UPDATED, method="_refresh")

    @callback
    def _refresh(self) -> None:
        active = self.bucket().get("active_culture_id")
        self._attr_native_value = active or "none"
        self.async_write_ha_state()


class CommunifarmVarietyListSensor(CommunifarmSensor):
    """Mushroom variety catalog (seed + custom)."""

    _attr_name = "Variety catalog"
    _attr_unique_id = "communifarm_variety_list"
    _attr_icon = "mdi:mushroom"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_VARIETY_LIST)
        self._value = "0 varieties"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(SIGNAL_CULTURE_UPDATED, method="async_refresh")

    async def async_refresh(self) -> None:
        repo: CultureRepository = self.bucket()["culture_repository"]
        varieties = await repo.async_list_varieties(include_retired=True)
        active = [v for v in varieties if v.status == "active"]
        self._value = f"{len(active)} varieties"
        self._attrs = {
            "varieties": [v.to_dict() for v in varieties],
            "list_text": CultureRepository.format_variety_list_text(active),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmCultureInventorySensor(CommunifarmSensor):
    """Physical culture vessels (one UID per jar/vial)."""

    _attr_name = "Culture inventory"
    _attr_unique_id = "communifarm_culture_inventory"
    _attr_icon = "mdi:flask-outline"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_CULTURE_INVENTORY)
        self._value = "0 vessels"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(SIGNAL_CULTURE_UPDATED, method="async_refresh")

    async def async_refresh(self) -> None:
        repo: CultureRepository = self.bucket()["culture_repository"]
        lots = await repo.async_list_cultures()
        self._value = f"{len(lots)} vessels"
        self._attrs = {
            "lots": [lot.to_dict() for lot in lots[:40]],
            "list_text": CultureRepository.format_culture_inventory_text(lots),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmClimateStatusSensor(CommunifarmSensor):
    """Effective climate readings and the last control decision."""

    _attr_name = "Climate status"
    _attr_unique_id = "communifarm_climate_status"
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_CLIMATE_STATUS)
        self._value = "not seeded"
        self._attrs: dict = {"summary": "", "node_count": 0, "seeded": False}

    async def async_added_to_hass(self) -> None:
        self._refresh()
        self.listen_entry_signals(SIGNAL_CLIMATE_UPDATED, method="_refresh")

    @callback
    def _refresh(self) -> None:
        snapshot = self.bucket().get("climate_snapshot") or {}
        seeded = bool(snapshot.get("seeded"))
        count = int(snapshot.get("node_count") or 0)
        self._value = f"{count} nodes" if seeded else "not seeded"
        self._attrs = {
            "summary": snapshot.get("summary") or "",
            "node_count": count,
            "seeded": seeded,
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmTachometerStatusSensor(CommunifarmSensor):
    """Latest manual vent tachometer / air-exchange reading."""

    _attr_name = "Tachometer status"
    _attr_unique_id = "communifarm_tachometer_status"
    _attr_icon = "mdi:fan-clock"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_TACHOMETER_STATUS)
        self._value = "no readings"
        self._attrs: dict = {
            "vent_count": 0,
            "vents": [],
            "recent_readings": [],
        }

    async def async_added_to_hass(self) -> None:
        self._refresh()
        self.listen_entry_signals(SIGNAL_TACHOMETER_UPDATED, method="_refresh")

    @callback
    def _refresh(self) -> None:
        snapshot = self.bucket().get("tachometer_snapshot") or {}
        vent_count = int(snapshot.get("vent_count") or 0)
        last_label = snapshot.get("last_vent_label")
        last_value = snapshot.get("last_value")
        last_unit = snapshot.get("last_unit")
        if last_label is not None and last_value is not None:
            self._value = f"{last_label}: {last_value} {last_unit}"
        else:
            self._value = "no readings"
        self._attrs = {
            "vent_count": vent_count,
            "vents": snapshot.get("vents") or [],
            "recent_readings": snapshot.get("recent_readings") or [],
            "last_recorded_at": snapshot.get("last_recorded_at"),
            "last_vent_label": last_label,
            "last_value": last_value,
            "last_unit": last_unit,
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._value

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs


class CommunifarmNfcCheckinSensor(CommunifarmSensor):
    """Last handheld NFC resolve / check-in context for harvest."""

    _attr_name = "NFC check-in"
    _attr_unique_id = "communifarm_nfc_checkin"
    _attr_icon = "mdi:nfc"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_NFC_CHECKIN)
        self._value = "idle"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        self._refresh()
        self.listen_entry_signals(
            SIGNAL_NFC_CHECKIN_UPDATED,
            SIGNAL_BATCH_UPDATED,
            method="_refresh",
        )

    def _refresh(self) -> None:
        session = self.bucket().get("nfc_session") or {}
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
            "amount": session.get("amount"),
            "amount_unit": session.get("amount_unit"),
            "found": bool(session.get("found")),
            "checkin_id": session.get("checkin_id"),
            "scan_event_id": session.get("scan_event_id"),
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


class CommunifarmSalesStatusSensor(CommunifarmSensor):
    """POS sales snapshot — updates when sales or cleanup are recorded."""

    _attr_name = "Sales status"
    _attr_unique_id = "communifarm_sales_status"
    _attr_icon = "mdi:point-of-sale"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_SALES_STATUS)
        self._value = "idle"
        self._attrs: dict = {}

    async def async_added_to_hass(self) -> None:
        await self.async_refresh()
        self.listen_entry_signals(SIGNAL_SALES_UPDATED, method="async_refresh")

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
