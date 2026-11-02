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
from .domain.inventory import NdefIdentity
from .domain.nfc import (
    ACTIVITY_HARVEST,
    ACTIVITY_MOVE,
    OBJECT_BATCH,
    OBJECT_CONTAINER,
    OBJECT_CULTURE,
    OBJECT_EMPLOYEE,
    OBJECT_INVENTORY,
    OBJECT_LOCATION,
    OBJECT_MEDIA,
    NfcCheckin,
    NfcResolution,
    NfcScanEvent,
    format_resolution_markdown,
    parse_nfc_uid,
    validate_activity,
    validate_bind_target,
)
from .domain.nfc_bind import (
    SCAN_SOURCE_BIND,
    SCAN_SOURCE_RESOLVE,
    PoolBindTarget,
    pool_should_align_on_resolve,
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
        "amount": None,
        "amount_unit": None,
        "found": False,
        "checkin_id": None,
        "scan_event_id": None,
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


def _session_from_resolution(
    resolution: NfcResolution, *, scan_event_id: str | None = None
) -> dict[str, Any]:
    detail = resolution.detail or {}
    return {
        "nfc_uid": resolution.nfc_uid,
        "object_type": resolution.object_type,
        "object_id": resolution.object_id,
        "batch_id": resolution.batch_id,
        "zone_id": resolution.zone_id,
        "label": resolution.label,
        "lifecycle_phase": resolution.lifecycle_phase,
        "flush_count": resolution.flush_count,
        "max_flushes": resolution.max_flushes,
        "amount": detail.get("amount"),
        "amount_unit": detail.get("amount_unit"),
        "found": resolution.found,
        "scan_event_id": scan_event_id,
        "progress_text": format_resolution_markdown(resolution),
    }


async def async_dual_write_pool_bind(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str,
    object_type: str,
    object_id: str,
    label: str | None = None,
) -> None:
    """Update ``nfc_tag_pool`` to match an entity ``nfc_uid`` bind (dual-write)."""
    bucket = hass.data[DOMAIN][entry_id]
    pool = bucket.get("nfc_tag_pool_repository")
    if pool is None:
        return
    state = bucket["state"]
    await pool.async_dual_write_bind(
        state.site.id,
        PoolBindTarget(
            nfc_uid=nfc_uid,
            object_type=object_type,
            object_id=object_id,
            label=label,
        ),
    )


async def _align_pool_after_resolve(
    hass: HomeAssistant,
    entry_id: str,
    resolution: NfcResolution,
) -> None:
    """Fix drift on already-bound pool rows; never auto-bind available chips."""
    if not resolution.found or not resolution.object_id:
        return
    bucket = hass.data[DOMAIN][entry_id]
    pool = bucket.get("nfc_tag_pool_repository")
    if pool is None:
        return
    site_id = bucket["state"].site.id
    entry = await pool.async_get_by_uid(site_id, resolution.nfc_uid)
    if entry is None:
        return
    if pool_should_align_on_resolve(
        pool_status=entry.status,
        pool_bound_object_id=entry.bound_object_id,
        pool_bound_object_type=entry.bound_object_type,
        resolved_object_id=resolution.object_id,
        resolved_object_type=resolution.object_type,
    ):
        await pool.async_mark_bound(
            site_id,
            resolution.nfc_uid,
            resolution.object_id,
            resolution.object_type,
        )


async def async_resolve_nfc(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str | None = None,
    scan_source: str = SCAN_SOURCE_RESOLVE,
    audit: bool = True,
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
    # Scan mode 3A: unknown UID while registering production blocks → bind new container.
    if (
        not resolution.found
        and bucket.get("nfc_scan_mode") == "register_production_block"
    ):
        from . import inventory_actions

        cont = await inventory_actions.async_register_production_block(
            hass, entry_id, nfc_uid=uid
        )
        resolution = await repo.async_resolve(uid)
        if not resolution.found:
            resolution = NfcResolution(
                nfc_uid=uid,
                object_type=OBJECT_CONTAINER,
                object_id=cont.id,
                label=f"{cont.container_type} #{cont.container_index}",
                batch_id=cont.batch_id,
                zone_id=cont.zone_id,
                found=True,
            )

    scan_event_id: str | None = None
    if audit:
        when = datetime.now(tz=UTC).isoformat()
        event = NfcScanEvent(
            site_id=bucket["state"].site.id,
            nfc_uid=resolution.nfc_uid,
            recorded_at=when,
            object_type=resolution.object_type if resolution.found else None,
            object_id=resolution.object_id,
            found=resolution.found,
            source=scan_source,
        )
        await repo.async_insert_scan_event(event)
        scan_event_id = event.id

    await _align_pool_after_resolve(hass, entry_id, resolution)

    session = bucket.setdefault("nfc_session", new_nfc_session())
    session.update(_session_from_resolution(resolution, scan_event_id=scan_event_id))
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

    bind_label: str | None = None
    if ot == OBJECT_CONTAINER:
        repo = _container_repo(hass, entry_id)
        cont = await repo.async_get(oid)
        if cont is None:
            raise HomeAssistantError(f"unknown container_id: {oid}")
        updated = rebind_container_nfc(cont, uid)
        await repo.async_update(updated)
        bind_label = f"{updated.container_type} #{updated.container_index}"
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
        bind_label = batch.name
    elif ot == OBJECT_INVENTORY:
        inv = hass.data[DOMAIN][entry_id].get("inventory_repository")
        if inv is None:
            raise HomeAssistantError("Inventory repository is not available")
        lot = await inv.async_get_lot(oid)
        if lot is None:
            raise HomeAssistantError(f"unknown inventory lot: {oid}")
        lot.nfc_uid = uid
        identity = NdefIdentity(
            object_type=OBJECT_INVENTORY,
            object_id=lot.id,
            label=lot.label,
            ingredient_key=lot.ingredient_key,
            water_kind=lot.water_kind,
        )
        lot.ndef_payload = identity.to_payload()
        await inv.async_update_lot(lot)
        bind_label = lot.label
    elif ot == OBJECT_EMPLOYEE:
        inv = hass.data[DOMAIN][entry_id].get("inventory_repository")
        if inv is None:
            raise HomeAssistantError("Inventory repository is not available")
        badge = await inv.async_get_employee(oid)
        if badge is None:
            raise HomeAssistantError(f"unknown employee: {oid}")
        badge.nfc_uid = uid
        identity = NdefIdentity(
            object_type=OBJECT_EMPLOYEE,
            object_id=badge.id,
            label=badge.label,
        )
        badge.ndef_payload = identity.to_payload()
        await inv.async_update_employee(badge)
        bind_label = badge.label
    elif ot == OBJECT_LOCATION:
        loc = hass.data[DOMAIN][entry_id].get("location_repository")
        if loc is None:
            raise HomeAssistantError("Location repository is not available")
        zone = await loc.async_get_zone(oid)
        if zone is None:
            raise HomeAssistantError(f"unknown zone_id: {oid}")
        identity = NdefIdentity(
            object_type=OBJECT_LOCATION,
            object_id=zone.id,
            label=zone.name,
            zone_id=zone.id,
        )
        await loc.async_bind_zone_nfc(zone.id, uid, identity.to_payload())
        bind_label = zone.name
    else:
        raise HomeAssistantError(
            f"bind_nfc for {ot} not implemented "
            "(container/batch/inventory/employee/location)"
        )

    await async_dual_write_pool_bind(
        hass,
        entry_id,
        nfc_uid=uid,
        object_type=ot,
        object_id=oid,
        label=bind_label,
    )
    await async_resolve_nfc(
        hass, entry_id, nfc_uid=uid, scan_source=SCAN_SOURCE_BIND
    )
    _LOGGER.info("Bound NFC %s → %s %s", uid, ot, oid)
    return uid
