"""Batch milestone / complete-and-new application helpers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    SIGNAL_BATCH_UPDATED,
    SIGNAL_WEIGH_SESSION_UPDATED,
    new_weigh_session_tracker,
)
from .dashboard.provisioner import async_provision_dashboard
from .domain.batch_milestones import (
    BATCH_TAB_MILESTONES,
    HEAT_METHODS,
    MILESTONE_BATCH_COMPLETED,
    MILESTONE_BATCH_CREATED,
    MILESTONE_COMPLETELY_MIXED,
    MILESTONE_CONTAINERS_SEPARATED,
    MILESTONE_DRY_MIXING_STARTED,
    MILESTONE_HEAT_TREATED,
    WEIGH_MILESTONES,
)
from .domain.models import CommunifarmState, ProductionBatch, new_id
from .domain.validation import validate_readable_name
from .storage.batch_repository import BatchRepository
from .storage.repository import CommunifarmRepository

_LOGGER = logging.getLogger(__name__)

ALLOWED_MANUAL = WEIGH_MILESTONES | BATCH_TAB_MILESTONES


async def async_record_milestone(
    hass: HomeAssistant,
    entry_id: str,
    event_type: str,
    *,
    detail: dict | None = None,
    allow_auto: bool = False,
) -> None:
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    batch_repo: BatchRepository = bucket["batch_repository"]

    if not allow_auto and event_type not in ALLOWED_MANUAL:
        raise HomeAssistantError(f"Unsupported milestone: {event_type}")

    if event_type == MILESTONE_HEAT_TREATED:
        method = (detail or {}).get("method")
        if method not in HEAT_METHODS:
            raise HomeAssistantError("heat treatment method must be sterilized or pasteurized")

    if event_type == MILESTONE_CONTAINERS_SEPARATED:
        count = int((detail or {}).get("container_count") or bucket.get("container_count") or 1)
        if count < 1:
            raise HomeAssistantError("container_count must be >= 1")
        detail = {**(detail or {}), "container_count": count}
        notes = (detail or {}).get("notes")
        await batch_repo.async_set_containers(state.batch.id, count, notes)

    when = datetime.now(tz=UTC).isoformat()
    await batch_repo.async_ensure_batch(
        batch_id=state.batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=state.batch.name,
        nfc_uid=state.batch.nfc_uid,
    )
    await batch_repo.async_insert_milestone(
        batch_id=state.batch.id,
        event_type=event_type,
        recorded_at=when,
        detail=detail,
    )

    if event_type == MILESTONE_DRY_MIXING_STARTED:
        await batch_repo.async_mark_mixing_started(state.batch.id, when)
    if event_type == MILESTONE_COMPLETELY_MIXED:
        await batch_repo.async_mark_mixing_finished(state.batch.id, when)

    _LOGGER.info("Batch %s milestone %s detail=%s", state.batch.id, event_type, detail)
    async_dispatcher_send(hass, SIGNAL_BATCH_UPDATED, entry_id)
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)


async def async_ensure_dry_mixing_started(hass: HomeAssistant, entry_id: str) -> None:
    """Auto-fire dry mixing start on first successful weigh for the active batch."""
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    batch_repo: BatchRepository = bucket["batch_repository"]
    await batch_repo.async_ensure_batch(
        batch_id=state.batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=state.batch.name,
        nfc_uid=state.batch.nfc_uid,
    )
    if await batch_repo.async_has_milestone(state.batch.id, MILESTONE_DRY_MIXING_STARTED):
        return
    await async_record_milestone(
        hass,
        entry_id,
        MILESTONE_DRY_MIXING_STARTED,
        allow_auto=True,
        detail={"source": "first_weight_record"},
    )


async def async_complete_and_new_batch(
    hass: HomeAssistant,
    entry_id: str,
    *,
    new_name: str | None = None,
) -> CommunifarmState:
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    batch_repo: BatchRepository = bucket["batch_repository"]
    repo: CommunifarmRepository = bucket["repository"]
    entry: ConfigEntry | None = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise HomeAssistantError("Communifarm config entry missing")

    when = datetime.now(tz=UTC).isoformat()
    await batch_repo.async_ensure_batch(
        batch_id=state.batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=state.batch.name,
        nfc_uid=state.batch.nfc_uid,
    )
    await batch_repo.async_insert_milestone(
        batch_id=state.batch.id,
        event_type=MILESTONE_BATCH_COMPLETED,
        recorded_at=when,
    )
    await batch_repo.async_complete_batch(state.batch.id, when)

    name = new_name or _next_batch_name(state.batch.name)
    validate_readable_name(name, field_name="batch.name")
    new_batch = ProductionBatch(
        name=name,
        environment_id=state.environment.id,
        id=new_id("batch"),
    )
    state.batch = new_batch
    await repo.async_save(state)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "state": state.to_dict()}
    )

    await batch_repo.async_ensure_batch(
        batch_id=new_batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=new_batch.name,
        nfc_uid=new_batch.nfc_uid,
        created_at=when,
    )
    await batch_repo.async_insert_milestone(
        batch_id=new_batch.id,
        event_type=MILESTONE_BATCH_CREATED,
        recorded_at=when,
    )

    bucket["weigh_session"] = new_weigh_session_tracker()
    bucket["state"] = state
    await async_provision_dashboard(hass, state)
    async_dispatcher_send(hass, SIGNAL_BATCH_UPDATED, entry_id)
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)
    _LOGGER.info("Completed previous batch; active batch is now %s", new_batch.id)
    return state


def _next_batch_name(previous: str) -> str:
    # "Batch 1" -> "Batch 2"; otherwise append " (next)".
    parts = previous.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{parts[0]} {int(parts[1]) + 1}"
    return f"{previous} next"[:64]
