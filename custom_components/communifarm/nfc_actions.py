"""NFC resolve / check-in application helpers (handheld scanner pull model)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    ENTITY_SCALE_NFC_UID,
    SIGNAL_BATCH_UPDATED,
    SIGNAL_NFC_CHECKIN_UPDATED,
)
from .domain.container import rebind_container_nfc
from .domain.nfc import (
    ACTIVITY_HARVEST,
    ACTIVITY_MOVE,
    OBJECT_BATCH,
    OBJECT_CONTAINER,
    OBJECT_CULTURE,
    OBJECT_MEDIA,
    NfcCheckin,
    NfcResolution,
    format_resolution_markdown,
    parse_nfc_uid,
    validate_activity,
    validate_bind_target,
)
from .domain.validation import ValidationError
from .storage.container_repository import ContainerRepository
from .storage.nfc_repository import NfcRepository

_LOGGER = logging.getLogger(__name__)


def _nfc_repo(hass: HomeAssistant, entry_id: str) -> NfcRepository:
    repo = hass.data[DOMAIN][entry_id].get("nfc_repository")
    if repo is None:
        raise HomeAssistantError("NFC repository is not available")
    return repo


def _container_repo(hass: HomeAssistant, entry_id: str) -> ContainerRepository:
    repo = hass.data[DOMAIN][entry_id].get("container_repository")
    if repo is None:
        raise HomeAssistantError("Container repository is not available")
    return repo


def new_nfc_session() -> dict[str, Any]:
    return {
        "nfc_uid": None,
        "object_type": None,
        "object_id": None,
        "activity": None,
        "batch_id": None,
        "zone_id": None,
        "label": None,
        "lifecycle_phase": None,
        "flush_count": None,
        "max_flushes": None,
        "found": False,
        "checkin_id": None,
        "progress_text": "Scan a tag with the handheld reader.",
    }


def _notify(hass: HomeAssistant, entry_id: str) -> None:
    async_dispatcher_send(hass, SIGNAL_NFC_CHECKIN_UPDATED, entry_id)
    async_dispatcher_send(hass, SIGNAL_BATCH_UPDATED, entry_id)


def _read_last_nfc_entity(hass: HomeAssistant) -> str | None:
    state = hass.states.get(ENTITY_SCALE_NFC_UID)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return None
    return str(state.state)


async def async_resolve_nfc(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str | None = None,
) -> NfcResolution:
    raw = nfc_uid or _read_last_nfc_entity(hass)
    try:
        uid = parse_nfc_uid(raw, required=True)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    assert uid is not None
    repo = _nfc_repo(hass, entry_id)
    resolution = await repo.async_resolve(uid)
    bucket = hass.data[DOMAIN][entry_id]
    session = bucket.setdefault("nfc_session", new_nfc_session())
    session.update(
        {
            "nfc_uid": resolution.nfc_uid,
            "object_type": resolution.object_type,
            "object_id": resolution.object_id,
            "batch_id": resolution.batch_id,
            "zone_id": resolution.zone_id,
            "label": resolution.label,
            "lifecycle_phase": resolution.lifecycle_phase,
            "flush_count": resolution.flush_count,
            "max_flushes": resolution.max_flushes,
            "found": resolution.found,
            "progress_text": format_resolution_markdown(resolution),
        }
    )
    _notify(hass, entry_id)
    return resolution


async def async_check_in(
    hass: HomeAssistant,
    entry_id: str,
    *,
    activity: str,
    nfc_uid: str | None = None,
    zone_id: str | None = None,
) -> str:
    """Resolve tag → set session context → optional zone update → append check-in."""
    try:
        act = validate_activity(activity)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

    resolution = await async_resolve_nfc(hass, entry_id, nfc_uid=nfc_uid)
    if not resolution.found or not resolution.object_id:
        raise HomeAssistantError(f"unknown NFC UID: {resolution.nfc_uid}")

    resolved_zone: str | None = None
    if zone_id:
        from . import location_actions

        await location_actions.async_ensure_default_layout(hass, entry_id)
        loc_repo = hass.data[DOMAIN][entry_id].get("location_repository")
        if loc_repo is None:
            raise HomeAssistantError("Location repository is not available")
        zone = await loc_repo.async_get_zone(str(zone_id).strip())
        if zone is None:
            raise HomeAssistantError(f"unknown zone_id: {zone_id}")
        resolved_zone = zone.id

        if resolution.object_type == OBJECT_CONTAINER:
            await _container_repo(hass, entry_id).async_set_zone(
                resolution.object_id, resolved_zone
            )
        elif resolution.object_type == OBJECT_BATCH:
            await location_actions.async_set_batch_location(
                hass, entry_id, zone_id=resolved_zone, batch_id=resolution.object_id
            )
        elif resolution.object_type == OBJECT_CULTURE:
            from . import culture_actions

            await culture_actions.async_set_culture_location(
                hass,
                entry_id,
                culture_id=resolution.object_id,
                zone_id=resolved_zone,
            )
        elif resolution.object_type == OBJECT_MEDIA:
            from . import culture_actions

            await culture_actions.async_set_media_location(
                hass,
                entry_id,
                media_batch_id=resolution.object_id,
                zone_id=resolved_zone,
            )

    when = datetime.now(tz=UTC).isoformat()
    event = NfcCheckin(
        nfc_uid=resolution.nfc_uid,
        object_type=resolution.object_type,
        object_id=resolution.object_id,
        activity=act,
        recorded_at=when,
        zone_id=resolved_zone or resolution.zone_id,
        detail={
            "label": resolution.label,
            "batch_id": resolution.batch_id,
            "lifecycle_phase": resolution.lifecycle_phase,
        },
    )
    await _nfc_repo(hass, entry_id).async_insert_checkin(event)

    bucket = hass.data[DOMAIN][entry_id]
    session = bucket.setdefault("nfc_session", new_nfc_session())
    session.update(
        {
            "activity": act,
            "zone_id": event.zone_id,
            "checkin_id": event.id,
            "progress_text": (
                f"**Checked in** for `{act}`\n\n"
                + format_resolution_markdown(resolution)
            ),
        }
    )
    if act == ACTIVITY_HARVEST and resolution.object_type == OBJECT_CONTAINER:
        session["container_id"] = resolution.object_id
    if act == ACTIVITY_MOVE and resolved_zone:
        _LOGGER.info(
            "NFC move %s %s → zone %s",
            resolution.object_type,
            resolution.object_id,
            resolved_zone,
        )
    _notify(hass, entry_id)
    return event.id


async def async_bind_nfc(
    hass: HomeAssistant,
    entry_id: str,
    *,
    object_type: str,
    object_id: str,
    nfc_uid: str | None = None,
) -> str:
    """Bind a physical handheld-scanned UID onto an existing Communifarm object."""
    try:
        ot, oid = validate_bind_target(object_type, object_id)
        uid = parse_nfc_uid(nfc_uid or _read_last_nfc_entity(hass), required=True)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    assert uid is not None

    if ot == OBJECT_CONTAINER:
        repo = _container_repo(hass, entry_id)
        cont = await repo.async_get(oid)
        if cont is None:
            raise HomeAssistantError(f"unknown container_id: {oid}")
        updated = rebind_container_nfc(cont, uid)
        await repo.async_update(updated)
    elif ot == OBJECT_BATCH:
        batch_repo = hass.data[DOMAIN][entry_id]["batch_repository"]
        batch = await batch_repo.async_get_batch(oid)
        if batch is None:
            raise HomeAssistantError(f"unknown batch_id: {oid}")
        await batch_repo.async_ensure_batch(
            batch_id=batch.id,
            site_id=batch.site_id,
            environment_id=batch.environment_id,
            name=batch.name,
            nfc_uid=uid,
            recipe_scale=batch.recipe_scale,
            recipe_key=batch.recipe_key,
        )
    else:
        raise HomeAssistantError(
            f"bind_nfc for {ot} not implemented in this slice (container/batch only)"
        )

    await async_resolve_nfc(hass, entry_id, nfc_uid=uid)
    _LOGGER.info("Bound NFC %s → %s %s", uid, ot, oid)
    return uid
