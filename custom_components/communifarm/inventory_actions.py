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
from .domain.batch_milestones import (
    MILESTONE_RELOCATED_FOR_STERILIZATION,
    MIX_PROTOCOL_MILESTONES,
)
from .domain.container import ProductionContainer
from .domain.inventory import (
    OBJECT_BATCH,
    OBJECT_CONTAINER,
    OBJECT_CULTURE,
    OBJECT_EMPLOYEE,
    OBJECT_INVENTORY,
    OBJECT_LOCATION,
    OBJECT_MACHINE,
    SCAN_MODE_NORMAL,
    TAG_SOURCE_LAST_SCANNED,
    WATER_KINDS,
    EmployeeBadge,
    InventoryLot,
    MachineAsset,
    NdefIdentity,
    PendingNfcWrite,
    inventory_write_choices,
    recipe_ingredient_key,
    water_kind_from_label,
)
from .domain.location import zone_option_label
from .domain.mix_protocol import (
    build_mix_protocol_progress,
    next_open_milestone,
)
from .domain.models import CommunifarmState
from .domain.nfc import parse_nfc_uid
from .domain.production import CONTAINER_BAG, DEFAULT_MAX_FLUSHES, STAGE_INOCULATED
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


def format_tag_source_option(nfc_uid: str, label: str) -> str:
    """Select option text: '04ABC… — hardwood pellets'."""
    return f"{nfc_uid} — {label}"


def parse_tag_source_option(option: str | None) -> str | None:
    """Extract UID from a tag-source option (or None for last-scanned)."""
    text = str(option or "").strip()
    if not text or text == TAG_SOURCE_LAST_SCANNED or text.startswith("("):
        return None
    if " — " in text:
        return text.split(" — ", 1)[0].strip() or None
    return text


def resolve_tag_source_uid(hass: HomeAssistant, entry_id: str) -> str | None:
    """UID from Tag source select, else last scanned writer helper."""
    bucket = hass.data[DOMAIN][entry_id]
    choice = bucket.get("intake_tag_uid_choice") or TAG_SOURCE_LAST_SCANNED
    from_db = parse_tag_source_option(str(choice))
    if from_db:
        return from_db
    return _read_writer_uid(hass)


# Back-compat for internal call sites.
_resolve_tag_source_uid = resolve_tag_source_uid


def new_pending_nfc_write() -> dict[str, Any]:
    return PendingNfcWrite().to_dict()


def _notify_write(hass: HomeAssistant, entry_id: str) -> None:
    async_dispatcher_send(hass, SIGNAL_NFC_CHECKIN_UPDATED, entry_id)
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)


def _purchase_fields_from_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    tracked = bucket.get("intake_tracked")
    receipt = bucket.get("intake_receipt_tracked")
    amount = bucket.get("intake_amount")
    cost = bucket.get("intake_cost")
    return {
        "amount": float(amount) if amount not in (None, "") else None,
        "amount_unit": bucket.get("intake_amount_unit") or None,
        "cost": float(cost) if cost not in (None, "") else None,
        "payment_location": bucket.get("intake_payment_location") or None,
        "purchase_location": (bucket.get("intake_purchase_location") or "").strip()
        or None,
        "tracked": None
        if tracked in (None, "")
        else str(tracked).lower() in {"yes", "true", "1"},
        "receipt_tracked": None
        if receipt in (None, "")
        else str(receipt).lower() in {"yes", "true", "1"},
        "purchase_date": (bucket.get("intake_purchase_date") or "").strip() or None,
    }


async def async_create_inventory_lot(
    hass: HomeAssistant,
    entry_id: str,
    *,
    label: str,
    water_kind: str | None = None,
) -> InventoryLot:
    """Create a new inventory lot UUID for an ingredient (names may duplicate)."""
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
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
    purchase = _purchase_fields_from_bucket(bucket)

    lot = InventoryLot(
        site_id=state.site.id,
        ingredient_key=key,
        label=display,
        water_kind=kind,
        **purchase,
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
    bucket["nfc_write_label"] = lot.label
    bucket["nfc_write_object_type"] = OBJECT_INVENTORY
    bucket["nfc_write_object_id"] = lot.id
    _LOGGER.info("Created inventory lot %s label=%s key=%s", lot.id, lot.label, key)
    # Persist purchase/lot row, then queue NDEF for the next physical tag bind.
    pending = await async_prepare_nfc_write(
        hass,
        entry_id,
        object_type=OBJECT_INVENTORY,
        object_id=lot.id,
        label=lot.label,
    )
    awaiting = PendingNfcWrite(
        object_type=pending.object_type,
        object_id=pending.object_id,
        label=pending.label,
        ingredient_key=pending.ingredient_key,
        water_kind=pending.water_kind,
        zone_id=pending.zone_id,
        nfc_uid=None,
        ndef_payload=pending.ndef_payload,
        status="awaiting_tag",
        progress_text=(
            f"**Awaiting tag** for inventory **{lot.label}** (`{lot.id}`)\n\n"
            "Lot is stored in inventory. Pick **Tag source** (last scanned or a "
            "known chip from the database), present/write the tag, then "
            "**Confirm write**.\n\n"
            f"```\n{pending.ndef_payload}\n```"
        ),
    )
    bucket["pending_nfc_write"] = awaiting.to_dict()
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
            emp_label = (
                (bucket.get("intake_employee_label") or "").strip()
                or chosen_label
            )
            if not emp_label:
                raise HomeAssistantError("employee label is required")
            badge = await async_create_employee_badge(
                hass, entry_id, label=emp_label
            )
        identity = NdefIdentity(
            object_type=OBJECT_EMPLOYEE,
            object_id=badge.id,
            label=badge.label,
        )
        oid = badge.id
        chosen_label = badge.label
    elif ot == OBJECT_LOCATION:
        zone_label = (bucket.get("intake_zone_label") or "").strip()
        if not chosen_zone and not oid and zone_label:
            chosen_zone = await _resolve_zone_label(hass, entry_id, zone_label)
        if not chosen_zone and not oid:
            raise HomeAssistantError(
                "select an Intake location zone before writing a location tag"
            )
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
    elif ot == OBJECT_CONTAINER:
        cont = await async_register_production_block(
            hass, entry_id, nfc_uid=None, prepare_only=True
        )
        identity = NdefIdentity(
            object_type=OBJECT_CONTAINER,
            object_id=cont.id,
            label=f"{cont.container_type} #{cont.container_index}",
        )
        oid = cont.id
        chosen_label = identity.label
    elif ot == OBJECT_BATCH:
        oid = state.batch.id
        chosen_label = state.batch.name
        identity = NdefIdentity(
            object_type=OBJECT_BATCH,
            object_id=oid,
            label=chosen_label,
        )
    elif ot == OBJECT_CULTURE:
        culture_id = (bucket.get("active_culture_id") or "").strip()
        if not culture_id:
            raise HomeAssistantError("select an active culture before writing a culture tag")
        culture_repo = bucket["culture_repository"]
        culture = await culture_repo.async_get_culture(culture_id)
        if culture is None:
            raise HomeAssistantError(f"unknown culture: {culture_id}")
        oid = culture.id
        chosen_label = culture.name
        identity = NdefIdentity(
            object_type=OBJECT_CULTURE,
            object_id=oid,
            label=chosen_label,
        )
    elif ot == OBJECT_MACHINE:
        machine_label = (
            chosen_label
            or (bucket.get("intake_machine_label") or "").strip()
            or "machine"
        )
        try:
            validate_readable_name(machine_label, field_name="machine.label")
        except ValidationError as err:
            raise HomeAssistantError(str(err)) from err
        if oid:
            machine = await inv.async_get_machine(oid)
            if machine is None:
                raise HomeAssistantError(f"unknown machine: {oid}")
        else:
            machine = MachineAsset(site_id=state.site.id, label=machine_label)
            identity_tmp = NdefIdentity(
                object_type=OBJECT_MACHINE,
                object_id=machine.id,
                label=machine.label,
            )
            machine.ndef_payload = identity_tmp.to_payload()
            await inv.async_insert_machine(machine)
        identity = NdefIdentity(
            object_type=OBJECT_MACHINE,
            object_id=machine.id,
            label=machine.label,
        )
        oid = machine.id
        chosen_label = machine.label
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

    chosen = nfc_uid or _resolve_tag_source_uid(hass, entry_id)
    try:
        uid = parse_nfc_uid(chosen, required=True)
    except ValidationError as err:
        raise HomeAssistantError(
            "select Tag source (last scanned or a DB chip) and present a tag — "
            f"{err}"
        ) from err
    assert uid is not None

    inv = _inv_repo(hass, entry_id)
    state: CommunifarmState = bucket["state"]
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
    elif ot == OBJECT_CONTAINER:
        cont_repo = bucket["container_repository"]
        cont = await cont_repo.async_get(oid)
        if cont is None:
            raise HomeAssistantError(f"unknown container: {oid}")
        cont.nfc_uid = uid
        await cont_repo.async_update(cont)
    elif ot == OBJECT_BATCH:
        batch_repo: BatchRepository = bucket["batch_repository"]
        batch = await batch_repo.async_get_batch(oid)
        if batch is None:
            raise HomeAssistantError(f"unknown batch: {oid}")
        await batch_repo.async_ensure_batch(
            batch_id=batch.id,
            site_id=batch.site_id,
            environment_id=batch.environment_id,
            name=batch.name,
            nfc_uid=uid,
            recipe_scale=batch.recipe_scale,
            recipe_key=batch.recipe_key,
        )
        state.batch.nfc_uid = uid
    elif ot == OBJECT_CULTURE:
        culture_repo = bucket["culture_repository"]
        culture = await culture_repo.async_get_culture(oid)
        if culture is None:
            raise HomeAssistantError(f"unknown culture: {oid}")
        await culture_repo.async_set_culture_nfc(oid, uid)
    elif ot == OBJECT_MACHINE:
        machine = await inv.async_get_machine(oid)
        if machine is None:
            raise HomeAssistantError(f"unknown machine: {oid}")
        machine.nfc_uid = uid
        machine.ndef_payload = payload
        await inv.async_update_machine(machine)
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
    from .domain.nfc_bind import SCAN_SOURCE_CONFIRM_WRITE

    await nfc_actions.async_dual_write_pool_bind(
        hass,
        entry_id,
        nfc_uid=uid,
        object_type=ot,
        object_id=oid,
        label=pending.label,
    )
    await nfc_actions.async_resolve_nfc(
        hass, entry_id, nfc_uid=uid, scan_source=SCAN_SOURCE_CONFIRM_WRITE
    )
    _LOGGER.info("Confirmed NFC write %s → %s %s", uid, ot, oid)
    _notify_write(hass, entry_id)
    return uid


async def async_list_zone_option_labels(
    hass: HomeAssistant,
    entry_id: str,
    *,
    area_kind: str | None = None,
) -> list[str]:
    """Ensure layout and return 'Area / Zone' labels for selects."""
    from . import location_actions

    await location_actions.async_ensure_default_layout(hass, entry_id)
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    loc: LocationRepository = bucket["location_repository"]
    areas, _zones = await loc.async_ensure_default_layout(state.site.id)
    area_by_id = {a.id: a for a in areas}
    labels: list[str] = []
    for area in areas:
        if area_kind and area.area_kind != area_kind:
            continue
        for zone in await loc.async_list_zones_for_area(area.id):
            labels.append(zone_option_label(area_by_id[area.id].name, zone.name))
    if labels:
        return labels
    if area_kind:
        return [f"(no {area_kind} zones — run ensure_placement_layout)"]
    return ["(no zones — run ensure_placement_layout)"]


async def async_list_tag_source_options(
    hass: HomeAssistant, entry_id: str
) -> list[str]:
    """Last-scanned placeholder plus pool + known chip UIDs from Communifarm tables."""
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    options: list[str] = [TAG_SOURCE_LAST_SCANNED]
    seen: set[str] = set()

    pool = bucket.get("nfc_tag_pool_repository")
    if pool is not None:
        for entry in await pool.async_list(state.site.id):
            if entry.nfc_uid not in seen:
                seen.add(entry.nfc_uid)
                options.append(
                    format_tag_source_option(
                        entry.nfc_uid, f"{entry.intended_type}: {entry.label}"
                    )
                )

    inv = _inv_repo(hass, entry_id)
    for lot in await inv.async_list_lots(state.site.id):
        if lot.nfc_uid and lot.nfc_uid not in seen:
            seen.add(lot.nfc_uid)
            options.append(format_tag_source_option(lot.nfc_uid, lot.label))
    for badge in await inv.async_list_employees(state.site.id):
        if badge.nfc_uid and badge.nfc_uid not in seen:
            seen.add(badge.nfc_uid)
            options.append(format_tag_source_option(badge.nfc_uid, badge.label))

    cont_repo = bucket.get("container_repository")
    if cont_repo is not None:
        for cont in await cont_repo.async_list_for_batch(state.batch.id):
            if cont.nfc_uid and cont.nfc_uid not in seen and cont.nfc_uid != cont.id:
                seen.add(cont.nfc_uid)
                options.append(
                    format_tag_source_option(
                        cont.nfc_uid, f"{cont.container_type} #{cont.container_index}"
                    )
                )

    loc: LocationRepository | None = bucket.get("location_repository")
    if loc is not None:
        for zone in await loc.async_list_zones(state.site.id):
            if zone.nfc_uid and zone.nfc_uid not in seen:
                seen.add(zone.nfc_uid)
                options.append(format_tag_source_option(zone.nfc_uid, zone.name))

    last = _read_writer_uid(hass)
    if last and last not in seen:
        options.insert(1, format_tag_source_option(last, "last scanned (live)"))
    return options


async def async_seed_shipment_nfc_tags(
    hass: HomeAssistant,
    entry_id: str,
    *,
    shipment_id: str | None = None,
) -> dict[str, Any]:
    """Load the all-in-one kit tag pack into Communifarm SQLite.

    Creates inventory lots / employee badges with bound UIDs for inventory and
    employee chips. Bag/bin chips stay in the pool as *available* until
    register_production_block binds them.

    HA entity rule: the integration never *creates* mock sensors (production
    safety). In the sandbox, ``devcontainer`` packages already provide fake
    last-NFC helpers; when those exist, this seed updates their state so UX /
    Playwright can drive tags without a PN532.
    """
    from .domain.shipment_tags import (
        DEFAULT_SHIPMENT_ID,
        DEFAULT_SHIPMENT_TAGS,
        STATUS_AVAILABLE,
        STATUS_BOUND,
    )
    from .storage.nfc_tag_pool_repository import NfcTagPoolEntry

    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    pool = bucket.get("nfc_tag_pool_repository")
    if pool is None:
        raise HomeAssistantError("NFC tag pool repository is not available")
    inv = _inv_repo(hass, entry_id)
    ship = (shipment_id or DEFAULT_SHIPMENT_ID).strip()
    created_lots = 0
    created_badges = 0
    pool_rows = 0
    first_bag_uid: str | None = None

    for spec in DEFAULT_SHIPMENT_TAGS:
        status = STATUS_AVAILABLE
        bound_id: str | None = None
        if spec.intended_type == OBJECT_INVENTORY:
            existing = await inv.async_get_lot_by_nfc(spec.nfc_uid)
            if existing is None:
                lot = InventoryLot(
                    site_id=state.site.id,
                    ingredient_key=spec.ingredient_key
                    or recipe_ingredient_key(spec.label)
                    or "unknown",
                    label=spec.label,
                    water_kind=water_kind_from_label(spec.label),
                    nfc_uid=spec.nfc_uid,
                )
                identity = NdefIdentity(
                    object_type=OBJECT_INVENTORY,
                    object_id=lot.id,
                    label=lot.label,
                    ingredient_key=lot.ingredient_key,
                    water_kind=lot.water_kind,
                )
                lot.ndef_payload = identity.to_payload()
                await inv.async_insert_lot(lot)
                created_lots += 1
                bound_id = lot.id
            else:
                bound_id = existing.id
            status = STATUS_BOUND
        elif spec.intended_type == OBJECT_EMPLOYEE:
            existing_emp = await inv.async_get_employee_by_nfc(spec.nfc_uid)
            if existing_emp is None:
                badge = EmployeeBadge(
                    site_id=state.site.id,
                    label=spec.label,
                    nfc_uid=spec.nfc_uid,
                )
                identity = NdefIdentity(
                    object_type=OBJECT_EMPLOYEE,
                    object_id=badge.id,
                    label=badge.label,
                )
                badge.ndef_payload = identity.to_payload()
                await inv.async_insert_employee(badge)
                created_badges += 1
                bound_id = badge.id
            else:
                bound_id = existing_emp.id
            status = STATUS_BOUND
        elif spec.intended_type == OBJECT_CONTAINER and first_bag_uid is None:
            first_bag_uid = spec.nfc_uid

        await pool.async_upsert(
            NfcTagPoolEntry(
                site_id=state.site.id,
                nfc_uid=spec.nfc_uid,
                intended_type=spec.intended_type,
                label=spec.label,
                ingredient_key=spec.ingredient_key,
                status=status,
                shipment_id=ship,
                bound_object_id=bound_id,
                bound_object_type=spec.intended_type if bound_id else None,
            )
        )
        pool_rows += 1

    # Point existing last-scan helpers at a bag chip so register_block works
    # without a physical PN532 — only if the helper already exists.
    if first_bag_uid:
        for entity_id in (ENTITY_SCALE_NFC_UID, ENTITY_NFC_WRITE_UID):
            if hass.states.get(entity_id) is not None:
                hass.states.async_set(entity_id, first_bag_uid)
        bucket["intake_tag_uid_choice"] = format_tag_source_option(
            first_bag_uid, f"{OBJECT_CONTAINER}: bag / block 01"
        )

    _notify_write(hass, entry_id)
    summary = {
        "shipment_id": ship,
        "pool_rows": pool_rows,
        "inventory_lots_created": created_lots,
        "employee_badges_created": created_badges,
        "default_bag_uid": first_bag_uid,
    }
    bucket["shipment_seed_summary"] = summary
    _LOGGER.info("Seeded shipment NFC tags: %s", summary)
    return summary


async def async_import_nfc_from_entity(
    hass: HomeAssistant,
    entry_id: str,
    *,
    entity_id: str | None = None,
    intended_type: str = OBJECT_CONTAINER,
    label: str | None = None,
) -> str:
    """Import a UID from an *existing* HA entity into the Communifarm tag pool.

    Default source is the shared last-NFC helper. Does not create HA entities —
    sandbox mocks must come from ``devcontainer/ha_config/packages/``.
    """
    from .domain.shipment_tags import STATUS_AVAILABLE
    from .storage.nfc_tag_pool_repository import NfcTagPoolEntry

    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    pool = bucket.get("nfc_tag_pool_repository")
    if pool is None:
        raise HomeAssistantError("NFC tag pool repository is not available")

    source = (entity_id or ENTITY_SCALE_NFC_UID).strip()
    ha_state = hass.states.get(source)
    if ha_state is None:
        raise HomeAssistantError(
            f"entity {source} is not present — import only reads existing HA "
            "entities. In the sandbox, load "
            "devcontainer packages (mock_cf_nfc_reader / mock_esp32dev_scale); "
            "production uses real ESPHome last-NFC sensors."
        )
    try:
        uid = parse_nfc_uid(str(ha_state.state), required=True)
    except ValidationError as err:
        raise HomeAssistantError(
            f"{source} has no usable NFC UID — scan or set it first ({err})"
        ) from err
    assert uid is not None

    ot = (intended_type or OBJECT_CONTAINER).strip()
    display = (label or "").strip() or f"imported {ot}"
    await pool.async_upsert(
        NfcTagPoolEntry(
            site_id=state.site.id,
            nfc_uid=uid,
            intended_type=ot,
            label=display,
            status=STATUS_AVAILABLE,
            shipment_id="imported",
        )
    )
    bucket["intake_tag_uid_choice"] = format_tag_source_option(uid, f"{ot}: {display}")
    _notify_write(hass, entry_id)
    _LOGGER.info("Imported NFC UID %s from %s as %s", uid, source, ot)
    return uid


async def _resolve_zone_label(
    hass: HomeAssistant, entry_id: str, label: str
) -> str:
    from . import location_actions

    await location_actions.async_ensure_default_layout(hass, entry_id)
    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    loc: LocationRepository = bucket["location_repository"]
    areas, _ = await loc.async_ensure_default_layout(state.site.id)
    for area in areas:
        for zone in await loc.async_list_zones_for_area(area.id):
            if zone_option_label(area.name, zone.name) == label:
                return zone.id
    raise HomeAssistantError(f"unknown location option: {label}")


async def async_register_production_block(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str | None = None,
    prepare_only: bool = False,
) -> ProductionContainer:
    """Create a production-block container for the active batch; optionally bind UID."""
    from datetime import UTC, datetime

    from . import nfc_actions

    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    cont_repo = bucket["container_repository"]
    existing = await cont_repo.async_list_for_batch(state.batch.id)
    next_index = (max((c.container_index for c in existing), default=0)) + 1
    ctype = str(bucket.get("container_type") or CONTAINER_BAG)
    zone_id: str | None = None
    zone_label = (bucket.get("intake_zone_label") or "").strip()
    if zone_label and not zone_label.startswith("("):
        zone_id = await _resolve_zone_label(hass, entry_id, zone_label)

    cont = ProductionContainer(
        batch_id=state.batch.id,
        container_index=next_index,
        container_type=ctype,
        nfc_uid="",
        lifecycle_phase=STAGE_INOCULATED,
        max_flushes=DEFAULT_MAX_FLUSHES,
        zone_id=zone_id,
        created_at=datetime.now(tz=UTC).isoformat(),
    )
    await cont_repo.async_insert_containers([cont])

    if prepare_only:
        bucket["nfc_write_object_type"] = OBJECT_CONTAINER
        bucket["nfc_write_object_id"] = cont.id
        _notify_write(hass, entry_id)
        return cont

    uid = nfc_uid or _resolve_tag_source_uid(hass, entry_id)
    pool = bucket.get("nfc_tag_pool_repository")
    if not uid and pool is not None:
        available = await pool.async_list(
            state.site.id, intended_type=OBJECT_CONTAINER, status="available"
        )
        if available:
            uid = available[0].nfc_uid
            bucket["intake_tag_uid_choice"] = format_tag_source_option(
                uid, f"{OBJECT_CONTAINER}: {available[0].label}"
            )
    try:
        uid = parse_nfc_uid(uid, required=True)
    except ValidationError as err:
        raise HomeAssistantError(
            "pick Tag source (seeded bag chip or last scanned) — "
            "run Seed shipment NFC tags on Intake if the pool is empty"
        ) from err
    assert uid is not None
    cont.nfc_uid = uid
    await cont_repo.async_update(cont)
    await nfc_actions.async_dual_write_pool_bind(
        hass,
        entry_id,
        nfc_uid=uid,
        object_type=OBJECT_CONTAINER,
        object_id=cont.id,
        label=f"{cont.container_type} #{cont.container_index}",
    )
    bucket["nfc_scan_mode"] = SCAN_MODE_NORMAL
    await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=uid)
    _LOGGER.info(
        "Registered production block %s index=%s uid=%s batch=%s",
        cont.id,
        cont.container_index,
        uid,
        state.batch.id,
    )
    _notify_write(hass, entry_id)
    return cont


async def async_apply_tag_source_scan(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str | None = None,
) -> str:
    """Treat Tag source (or explicit UID) as a live NFC scan.

    Updates existing last-NFC helpers when present, then resolve_nfc so Mix /
    Intake / register-block see the same UID a real PN532 would deliver.
    """
    from . import nfc_actions

    uid = nfc_uid or _resolve_tag_source_uid(hass, entry_id)
    try:
        uid = parse_nfc_uid(uid, required=True)
    except ValidationError as err:
        raise HomeAssistantError(
            "pick Tag source (select.communifarm_intake_tag_uid), then Scan NFC tag — "
            "or Seed shipment NFC tags first"
        ) from err
    assert uid is not None

    for entity_id in (ENTITY_SCALE_NFC_UID, ENTITY_NFC_WRITE_UID):
        if hass.states.get(entity_id) is not None:
            hass.states.async_set(entity_id, uid)

    # resolve_nfc already notifies NFC/batch; only nudge weigh session here.
    resolution = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=uid)
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)
    _LOGGER.info(
        "Applied tag-source scan uid=%s found=%s type=%s",
        uid,
        resolution.found,
        resolution.object_type,
    )
    return uid


async def async_complete_mix_step_from_badge(
    hass: HomeAssistant,
    entry_id: str,
    *,
    nfc_uid: str | None = None,
) -> str:
    """Employee badge (via Tag source or last scan) completes next mix milestone."""
    from . import batch_actions, nfc_actions

    progress = await async_mix_protocol_snapshot(hass, entry_id)
    milestone = next_open_milestone(progress)
    if milestone is None:
        if progress.next_key == "weigh_drys":
            raise HomeAssistantError("finish dry weighing before badge checkpoints")
        if progress.next_key == "relocate_sterile" or progress.completed >= progress.total:
            raise HomeAssistantError(
                "mix checkpoints done — pick sterilization location and press "
                "Relocate for sterilization (badge cannot finish relocate)"
            )
        raise HomeAssistantError("mix protocol already complete")
    if milestone == MILESTONE_RELOCATED_FOR_STERILIZATION:
        raise HomeAssistantError(
            "use Relocate for sterilization (location select + batch/bag NFC) — "
            "badge cannot complete relocate"
        )
    if milestone not in MIX_PROTOCOL_MILESTONES:
        raise HomeAssistantError(f"cannot badge-complete milestone: {milestone}")

    raw = nfc_uid or _resolve_tag_source_uid(hass, entry_id)
    if not raw:
        raise HomeAssistantError(
            "pick Tag source → employee badge (e.g. nfc-employee-01), then "
            "Scan NFC tag or Badge: complete next checkpoint"
        )

    resolution = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=raw)
    if not resolution.found or resolution.object_type != OBJECT_EMPLOYEE:
        raise HomeAssistantError(
            "Tag source must be an employee badge — select nfc-employee-01 "
            "(after Seed shipment NFC tags), Scan NFC tag, then retry"
        )

    await batch_actions.async_record_milestone(
        hass,
        entry_id,
        milestone,
        detail={
            "source": "employee_badge",
            "employee_id": resolution.object_id,
            "employee_label": resolution.label,
            "nfc_uid": resolution.nfc_uid,
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

    1A: location select (or location NFC) required. Bag/bin NFC preferred;
    active batch NFC is accepted when no bag tag is available yet.
    """
    from . import batch_actions, location_actions, nfc_actions

    bucket = hass.data[DOMAIN][entry_id]
    state: CommunifarmState = bucket["state"]
    bag_uid = bag_nfc_uid or bucket.get("relocate_bag_nfc_uid")
    loc_uid = location_nfc_uid or bucket.get("relocate_location_nfc_uid")

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

    zone_id: str | None = None
    location_nfc: str | None = None
    zone_label = (
        bucket.get("relocate_zone_label") or bucket.get("intake_zone_label") or ""
    ).strip()
    if zone_label and not zone_label.startswith("("):
        zone_id = await _resolve_zone_label(hass, entry_id, zone_label)

    if loc_uid and not zone_id:
        loc = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=str(loc_uid))
        if not loc.found or loc.object_type != OBJECT_LOCATION or not loc.zone_id:
            raise HomeAssistantError(
                "location scan must resolve to a location zone tag"
            )
        zone_id = loc.zone_id
        location_nfc = loc.nfc_uid

    if not zone_id:
        raise HomeAssistantError(
            "select a Storage shelf on Mix (post-sterile staging), "
            "then press Relocate for sterilization"
        )

    # 5A: bags always land in Storage awaiting culture — remap non-storage picks.
    zone_id = await location_actions.async_ensure_storage_zone(
        hass, entry_id, zone_id=zone_id
    )

    # 1A: fall back to active batch NFC when no bag/bin tag is registered yet.
    if not bag_uid:
        bag_uid = state.batch.nfc_uid

    bag = await nfc_actions.async_resolve_nfc(hass, entry_id, nfc_uid=str(bag_uid))
    if not bag.found or bag.object_type not in {OBJECT_CONTAINER, OBJECT_BATCH}:
        raise HomeAssistantError(
            "batch/bag NFC must resolve — set scan mode to register a production "
            "block on Intake, or use the active batch tag"
        )

    batch_id = bag.batch_id or state.batch.id
    await location_actions.async_set_batch_location(
        hass,
        entry_id,
        zone_id=zone_id,
        batch_id=batch_id,
    )
    # Place every active production block for this batch into Storage.
    cont_repo = bucket["container_repository"]
    for cont in await cont_repo.async_list_for_batch(batch_id):
        if cont.status == "complete":
            continue
        cont.zone_id = zone_id
        await cont_repo.async_update(cont)

    await batch_actions.async_record_milestone(
        hass,
        entry_id,
        MILESTONE_RELOCATED_FOR_STERILIZATION,
        detail={
            "bag_nfc_uid": bag.nfc_uid,
            "bag_object_type": bag.object_type,
            "bag_object_id": bag.object_id,
            "batch_id": batch_id,
            "zone_id": zone_id,
            "location_nfc_uid": location_nfc,
            "location_label": zone_label or None,
            "scope": "entire_batch",
            "area_kind": "storage",
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
