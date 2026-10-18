"""Inventory lot create / NFC write prepare / badge mix-step helpers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    ENTITY_SCALE_NFC_UID,
    SIGNAL_BATCH_UPDATED,
    SIGNAL_NFC_CHECKIN_UPDATED,
    SIGNAL_WEIGH_SESSION_UPDATED,
)
from .domain.batch_milestones import MIX_PROTOCOL_MILESTONES
from .domain.inventory import (
    OBJECT_EMPLOYEE,
    OBJECT_INVENTORY,
    OBJECT_LOCATION,
    WATER_KINDS,
    EmployeeBadge,
    InventoryLot,
    NdefIdentity,
    PendingNfcWrite,
    inventory_write_choices,
    recipe_ingredient_key,
    water_kind_from_label,
)
from .domain.mix_protocol import (
    build_mix_protocol_progress,
    next_open_milestone,
)
from .domain.models import CommunifarmState
from .domain.nfc import OBJECT_BATCH, OBJECT_CONTAINER, parse_nfc_uid
from .domain.recipe import build_weigh_session_progress
from .domain.validation import ValidationError, validate_readable_name
from .fixtures.cf_nfc_reader import ENTITY_NFC_WRITE_UID
from .storage.batch_repository import BatchRepository
from .storage.inventory_repository import InventoryRepository
from .storage.location_repository import LocationRepository
from .storage.weight_repository import WeightEventRepository

_LOGGER = logging.getLogger(__name__)


def _inv_repo(hass: HomeAssistant, entry_id: str) -> InventoryRepository:
    repo = hass.data[DOMAIN][entry_id].get("inventory_repository")
    if repo is None:
        raise HomeAssistantError("Inventory repository is not available")
    return repo


def _read_writer_uid(hass: HomeAssistant) -> str | None:
    for entity_id in (ENTITY_NFC_WRITE_UID, ENTITY_SCALE_NFC_UID):
        state = hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            continue
        return str(state.state)
    return None


def new_pending_nfc_write() -> dict[str, Any]:
    return PendingNfcWrite().to_dict()


def _notify_write(hass: HomeAssistant, entry_id: str) -> None:
    async_dispatcher_send(hass, SIGNAL_NFC_CHECKIN_UPDATED, entry_id)
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)


async def async_create_inventory_lot(
    hass: HomeAssistant,
    entry_id: str,
    *,
    label: str,
    water_kind: str | None = None,
) -> InventoryLot:
    """Create a new inventory lot UUID for an ingredient (names may duplicate)."""
    state: CommunifarmState = hass.data[DOMAIN][entry_id]["state"]
    try:
        validate_readable_name(label, field_name="inventory.label")
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

    kind = water_kind or water_kind_from_label(label)
    if kind and kind not in WATER_KINDS:
        raise HomeAssistantError(f"unknown water_kind: {kind}")
    key = recipe_ingredient_key(WATER_KINDS.get(kind, label) if kind else label)
    if not key:
        raise HomeAssistantError("ingredient label is required")
    display = WATER_KINDS[kind] if kind else label.strip()

    lot = InventoryLot(
        site_id=state.site.id,
        ingredient_key=key,
        label=display,
        water_kind=kind,
    )
    identity = NdefIdentity(
        object_type=OBJECT_INVENTORY,
        object_id=lot.id,
        label=lot.label,
        ingredient_key=lot.ingredient_key,
        water_kind=lot.water_kind,
    )
    lot.ndef_payload = identity.to_payload()
    await _inv_repo(hass, entry_id).async_insert_lot(lot)
    bucket = hass.data[DOMAIN][entry_id]
    bucket["nfc_write_label"] = lot.label
    bucket["nfc_write_object_type"] = OBJECT_INVENTORY
    bucket["nfc_write_object_id"] = lot.id
    _LOGGER.info("Created inventory lot %s label=%s key=%s", lot.id, lot.label, key)
    _notify_write(hass, entry_id)
    return lot


async def async_create_employee_badge(
    hass: HomeAssistant,
    entry_id: str,
    *,
    label: str,
) -> EmployeeBadge:
    state: CommunifarmState = hass.data[DOMAIN][entry_id]["state"]
    try:
        validate_readable_name(label, field_name="employee.label")
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    badge = EmployeeBadge(site_id=state.site.id, label=label.strip())
    identity = NdefIdentity(
        object_type=OBJECT_EMPLOYEE,
        object_id=badge.id,
        label=badge.label,
    )
    badge.ndef_payload = identity.to_payload()
    await _inv_repo(hass, entry_id).async_insert_employee(badge)
    bucket = hass.data[DOMAIN][entry_id]
    bucket["nfc_write_object_type"] = OBJECT_EMPLOYEE
    bucket["nfc_write_object_id"] = badge.id
    bucket["nfc_write_label"] = badge.label
    _notify_write(hass, entry_id)
    return badge


async def async_prepare_nfc_write(
    hass: HomeAssistant,
    entry_id: str,
    *,
    object_type: str | None = None,
    object_id: str | None = None,
    label: str | None = None,
    zone_id: str | None = None,
) -> PendingNfcWrite:
    """Build NDEF JSON for the ESPHome writer and stash it on the session sensor."""
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    ot = (object_type or bucket.get("nfc_write_object_type") or OBJECT_INVENTORY).strip()
    oid = (object_id or bucket.get("nfc_write_object_id") or "").strip() or None
    chosen_label = (label or bucket.get("nfc_write_label") or "").strip() or None
    chosen_zone = (zone_id or bucket.get("nfc_write_zone_id") or "").strip() or None

    inv = _inv_repo(hass, entry_id)
    identity: NdefIdentity

    if ot == OBJECT_INVENTORY:
        if oid:
            lot = await inv.async_get_lot(oid)
            if lot is None:
                raise HomeAssistantError(f"unknown inventory lot: {oid}")
        else:
            if not chosen_label:
                raise HomeAssistantError("select an ingredient label or create a lot first")
            if chosen_label not in inventory_write_choices():
                raise HomeAssistantError(f"unsupported write label: {chosen_label}")
            lot = await async_create_inventory_lot(
                hass, entry_id, label=chosen_label
            )
        identity = NdefIdentity(
            object_type=OBJECT_INVENTORY,
            object_id=lot.id,
            label=lot.label,
            ingredient_key=lot.ingredient_key,
            water_kind=lot.water_kind,
        )
        oid = lot.id
        chosen_label = lot.label
    elif ot == OBJECT_EMPLOYEE:
        if oid:
            badge = await inv.async_get_employee(oid)
            if badge is None:
                raise HomeAssistantError(f"unknown employee: {oid}")
        else:
            if not chosen_label:
                raise HomeAssistantError("employee label is required")
            badge = await async_create_employee_badge(
                hass, entry_id, label=chosen_label
            )
        identity = NdefIdentity(
            object_type=OBJECT_EMPLOYEE,
            object_id=badge.id,
            label=badge.label,
        )
        oid = badge.id
        chosen_label = badge.label
    elif ot == OBJECT_LOCATION:
        if not chosen_zone and not oid:
            raise HomeAssistantError("zone_id is required for location tags")
        loc: LocationRepository = bucket["location_repository"]
        zone = await loc.async_get_zone(chosen_zone or oid or "")
        if zone is None:
            raise HomeAssistantError(f"unknown zone_id: {chosen_zone or oid}")
        identity = NdefIdentity(
            object_type=OBJECT_LOCATION,
            object_id=zone.id,
            label=zone.name,
            zone_id=zone.id,
        )
        oid = zone.id
        chosen_label = zone.name
        chosen_zone = zone.id
    else:
        raise HomeAssistantError(f"unsupported NFC write object_type: {ot}")

    payload = identity.to_payload()
    pending = PendingNfcWrite(
        object_type=ot,
        object_id=oid,
        label=chosen_label,
        ingredient_key=identity.ingredient_key,
        water_kind=identity.water_kind,
        zone_id=chosen_zone,
        ndef_payload=payload,
        status="ready",
        progress_text=(
            f"**Ready to write** `{ot}` `{oid}`\n\n"
            f"Label: **{chosen_label}**\n\n"
            f"```\n{payload}\n```\n\n"
            "Present the tag to the lab NFC writer, then confirm write."
        ),
    )
    bucket["pending_nfc_write"] = pending.to_dict()
    bucket["nfc_write_object_type"] = ot
    bucket["nfc_write_object_id"] = oid
    bucket["nfc_write_label"] = chosen_label
    if chosen_zone:
        bucket["nfc_write_zone_id"] = chosen_zone
    # Expose payload for mock / ESPHome text entity consumers.
    if hass.states.get("input_text.cf_lab_nfc_write01_pending_ndef") is not None:
        hass.states.async_set(
            "input_text.cf_lab_nfc_write01_pending_ndef",
            payload[:255],
        )
    _LOGGER.info("Prepared NDEF write for %s %s", ot, oid)
    _notify_write(hass, entry_id)
    return pending


async def async_confirm_nfc_write(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str | None = None,
) -> str:
    """Bind the physical chip UID after a successful NDEF write (or mock)."""
    bucket = hass.data[DOMAIN][entry_id]
    pending = bucket.get("pending_nfc_write") or {}
    ot = pending.get("object_type")
    oid = pending.get("object_id")
    payload = pending.get("ndef_payload")
    if not ot or not oid or not payload:
        raise HomeAssistantError("prepare_nfc_write first")

    try:
        uid = parse_nfc_uid(nfc_uid or _read_writer_uid(hass), required=True)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    assert uid is not None

    inv = _inv_repo(hass, entry_id)
    if ot == OBJECT_INVENTORY:
        lot = await inv.async_get_lot(oid)
        if lot is None:
            raise HomeAssistantError(f"unknown inventory lot: {oid}")
        lot.nfc_uid = uid
        lot.ndef_payload = payload
        await inv.async_update_lot(lot)
    elif ot == OBJECT_EMPLOYEE:
        badge = await inv.async_get_employee(oid)
        if badge is None:
            raise HomeAssistantError(f"unknown employee: {oid}")
        badge.nfc_uid = uid
        badge.ndef_payload = payload
        await inv.async_update_employee(badge)
    elif ot == OBJECT_LOCATION:
        loc: LocationRepository = bucket["location_repository"]
        await loc.async_bind_zone_nfc(oid, uid, payload)
    else:
        raise HomeAssistantError(f"unsupported NFC write object_type: {ot}")

    pending = PendingNfcWrite(
        object_type=ot,
        object_id=oid,
        label=pending.get("label"),
        ingredient_key=pending.get("ingredient_key"),
        water_kind=pending.get("water_kind"),
        zone_id=pending.get("zone_id"),
        nfc_uid=uid,
        ndef_payload=payload,
        status="written",
        progress_text=(
            f"**Wrote** `{ot}` `{oid}` → chip `{uid}`\n\n"
            f"```\n{payload}\n```"
        ),
    )
    bucket["pending_nfc_write"] = pending.to_dict()
    from . import nfc_actions

    await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=uid)
    _LOGGER.info("Confirmed NFC write %s → %s %s", uid, ot, oid)
    _notify_write(hass, entry_id)
    return uid


async def async_complete_mix_step_from_badge(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str | None = None,
) -> str:
    """Employee badge scan completes the next open mix-protocol milestone."""
    from . import batch_actions
    from . import nfc_actions

    resolution = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=nfc_uid)
    if not resolution.found or resolution.object_type != OBJECT_EMPLOYEE:
        raise HomeAssistantError(
            "scan an employee badge to complete the next mix step"
        )

    progress = await async_mix_protocol_snapshot(hass, entry_id)
    milestone = next_open_milestone(progress)
    if milestone is None:
        if progress.next_key == "weigh_drys":
            raise HomeAssistantError("finish dry weighing before badge checkpoints")
        raise HomeAssistantError("mix protocol already complete")
    if milestone not in MIX_PROTOCOL_MILESTONES:
        raise HomeAssistantError(f"cannot badge-complete milestone: {milestone}")

    await batch_actions.async_record_milestone(
        hass,
        entry_id,
        milestone,
        detail={
            "source": "employee_badge",
            "employee_id": resolution.object_id,
            "employee_label": resolution.label,
        },
    )
    async_dispatcher_send(hass, SIGNAL_BATCH_UPDATED, entry_id)
    return milestone


async def async_relocate_for_sterilization(
    hass: HomeAssistant,
    entry_id: str,
    *,
    bag_nfc_uid: str | None = None,
    location_nfc_uid: str | None = None,
) -> str:
    """Document that the whole mix batch moved to sterilization staging.

    Requires at least one bag/bin (or batch) NFC scan. Location tag is optional
    but applied when present.
    """
    from . import batch_actions
    from . import location_actions
    from . import nfc_actions
    from .domain.batch_milestones import MILESTONE_RELOCATED_FOR_STERILIZATION
    from .domain.models import CommunifarmState

    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    bag_uid = bag_nfc_uid or bucket.get("relocate_bag_nfc_uid")
    loc_uid = location_nfc_uid or bucket.get("relocate_location_nfc_uid")

    # Fall back to the shared last-scan entity only when it is non-empty.
    if not bag_uid:
        last = _read_writer_uid(hass)
        if last:
            probe = await nfc_actions.async_resolve_nfc(
                hass, entry_id, nfc_uid=str(last)
            )
            if probe.found and probe.object_type in {OBJECT_CONTAINER, OBJECT_BATCH}:
                bag_uid = probe.nfc_uid
                bucket["relocate_bag_nfc_uid"] = bag_uid
            elif probe.found and probe.object_type == OBJECT_LOCATION:
                loc_uid = probe.nfc_uid
                bucket["relocate_location_nfc_uid"] = loc_uid

    if not bag_uid:
        raise HomeAssistantError(
            "Scan at least one bag/bin NFC tag (or the batch tag), then press "
            "Relocate for sterilization. That documents the whole batch moved."
        )

    bag = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=str(bag_uid))
    if not bag.found or bag.object_type not in {OBJECT_CONTAINER, OBJECT_BATCH}:
        raise HomeAssistantError(
            "bag/bin scan must resolve to a container or batch tag — "
            "write a bag tag on NFC Write if needed"
        )

    zone_id: str | None = None
    location_nfc: str | None = None
    if loc_uid:
        loc = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=str(loc_uid))
        if not loc.found or loc.object_type != OBJECT_LOCATION or not loc.zone_id:
            raise HomeAssistantError(
                "location scan must resolve to a location zone tag"
            )
        zone_id = loc.zone_id
        location_nfc = loc.nfc_uid
        if bag.object_type == OBJECT_CONTAINER and bag.batch_id:
            await location_actions.async_set_batch_location(
                hass,
                entry_id,
                zone_id=zone_id,
                batch_id=bag.batch_id,
            )
        else:
            await location_actions.async_set_batch_location(
                hass, entry_id, zone_id=zone_id
            )

    await batch_actions.async_record_milestone(
        hass,
        entry_id,
        MILESTONE_RELOCATED_FOR_STERILIZATION,
        detail={
            "bag_nfc_uid": bag.nfc_uid,
            "bag_object_type": bag.object_type,
            "bag_object_id": bag.object_id,
            "batch_id": bag.batch_id or state.batch.id,
            "zone_id": zone_id,
            "location_nfc_uid": location_nfc,
            "scope": "entire_batch",
        },
    )
    bucket["relocate_bag_nfc_uid"] = None
    bucket["relocate_location_nfc_uid"] = None
    return MILESTONE_RELOCATED_FOR_STERILIZATION


async def async_record_water_pour(
    hass: HomeAssistant,
    entry_id: str,
) -> None:
    """Record current scale mass as a water pour for the active batch.

    Uses the selected water variant when the ingredient select is a water label;
    otherwise defaults to water (tap). Location tare first so the pour is net.
    """
    from .const import DOMAIN, ENTITY_SCALE_SELECTED_INGREDIENT, SERVICE_RECORD_WEIGHT

    select_state = hass.states.get(ENTITY_SCALE_SELECTED_INGREDIENT)
    label = "water (tap)"
    if select_state is not None:
        raw = str(select_state.state)
        if recipe_ingredient_key(raw) == "water":
            label = raw

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECORD_WEIGHT,
        {"ingredient": label},
        blocking=True,
    )


async def async_mix_protocol_snapshot(
    hass: HomeAssistant, entry_id: str
) -> Any:
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    batch_repo: BatchRepository = bucket["batch_repository"]
    weight_repo: WeightEventRepository = bucket["weight_repository"]
    milestones = await batch_repo.async_list_milestones(state.batch.id)
    types = [m.event_type for m in milestones]
    events = await weight_repo.async_list_for_batch(state.batch.id)
    weigh = build_weigh_session_progress(
        batch_id=state.batch.id,
        batch_nfc_uid=state.batch.nfc_uid,
        recipe_scale=state.recipe_scale,
        events=events,
    )
    fc_ok = bucket.get("field_capacity_ok")
    return build_mix_protocol_progress(
        batch_id=state.batch.id,
        milestone_types=types,
        weigh=weigh,
        field_capacity_ok=fc_ok if isinstance(fc_ok, bool) else None,
    )


def assess_field_capacity_reading(
    raw: float | None,
    *,
    min_ok: float = 40.0,
    max_ok: float = 70.0,
) -> tuple[bool | None, str | None]:
    """Return (in_band, warning). None reading → unknown."""
    if raw is None:
        return None, None
    if raw < 0 or raw > 100:
        return False, "field_capacity_out_of_sensor_range"
    if min_ok <= raw <= max_ok:
        return True, None
    return False, "field_capacity_outside_calibrated_band"
