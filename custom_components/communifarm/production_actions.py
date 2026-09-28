"""Production inoculate / stage / harvest application helpers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_BATCH_UPDATED, SIGNAL_WEIGH_SESSION_UPDATED
from .domain.batch_milestones import (
    MILESTONE_BATCH_NOTE,
    MILESTONE_CHECK_REMINDER_SET,
    MILESTONE_HARVEST_RECORDED,
    MILESTONE_HARVEST_STARTED,
    MILESTONE_INOCULATED,
    MILESTONE_MOVED_TO_FRUITING,
    MILESTONE_MOVED_TO_INCUBATION,
    MILESTONE_TO_PHASE,
)
from .domain.culture import EVENT_CULTURE_INOCULATED_BATCH, CultureEvent
from .domain.models import CommunifarmState
from .domain.production import (
    DEFAULT_MAX_FLUSHES,
    STAGE_FRUITING,
    STAGE_HARVESTING,
    STAGE_INCUBATING,
    STAGE_INOCULATED,
    HarvestEvent,
    InoculateSpec,
    ProductionSummary,
    assert_can_advance,
    assert_can_harvest,
    assert_can_inoculate,
    format_production_markdown,
    validate_inoculate_spec,
)
from .domain.validation import ValidationError
from .storage.batch_repository import BatchRepository
from .storage.culture_repository import CultureRepository

_LOGGER = logging.getLogger(__name__)

_ADVANCE_MILESTONE = {
    STAGE_INCUBATING: MILESTONE_MOVED_TO_INCUBATION,
    STAGE_FRUITING: MILESTONE_MOVED_TO_FRUITING,
    STAGE_HARVESTING: MILESTONE_HARVEST_STARTED,
}


def _batch_repo(hass: HomeAssistant, entry_id: str) -> BatchRepository:
    repo = hass.data[DOMAIN][entry_id].get("batch_repository")
    if repo is None:
        raise HomeAssistantError("Batch repository is not available")
    return repo


def _culture_repo(hass: HomeAssistant, entry_id: str) -> CultureRepository:
    repo = hass.data[DOMAIN][entry_id].get("culture_repository")
    if repo is None:
        raise HomeAssistantError("Culture repository is not available")
    return repo


def _state(hass: HomeAssistant, entry_id: str) -> CommunifarmState:
    return hass.data[DOMAIN][entry_id]["state"]


def _notify_batch(hass: HomeAssistant, entry_id: str) -> None:
    async_dispatcher_send(hass, SIGNAL_BATCH_UPDATED, entry_id)
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)


async def async_inoculate_batch(
    hass: HomeAssistant,
    entry_id: str,
    *,
    culture_id: str,
    container_type: str,
    container_count: int,
    substrate_g_per_container: float,
    inoculum_amount: float | None = None,
    inoculum_unit: str | None = None,
    max_flushes: int = DEFAULT_MAX_FLUSHES,
    expected_check_at: str | None = None,
    notes: str | None = None,
    zone_id: str | None = None,
) -> str:
    state = _state(hass, entry_id)
    batch_repo = _batch_repo(hass, entry_id)
    culture_repo = _culture_repo(hass, entry_id)

    culture = await culture_repo.async_get_culture(culture_id)
    if culture is None:
        raise HomeAssistantError(f"unknown culture_id: {culture_id}")

    try:
        spec = validate_inoculate_spec(
            InoculateSpec(
                culture_id=culture_id,
                container_type=container_type,
                container_count=container_count,
                substrate_g_per_container=substrate_g_per_container,
                inoculum_amount=inoculum_amount,
                inoculum_unit=inoculum_unit,
                max_flushes=max_flushes,
                expected_check_at=expected_check_at,
                notes=notes,
            )
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

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

    batch = await batch_repo.async_get_batch(state.batch.id)
    phase = batch.lifecycle_phase if batch else "planned"
    try:
        assert_can_inoculate(phase)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

    when = datetime.now(tz=UTC).isoformat()
    await batch_repo.async_ensure_batch(
        batch_id=state.batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=state.batch.name,
        nfc_uid=state.batch.nfc_uid,
    )
    updated = await batch_repo.async_apply_inoculate(
        batch_id=state.batch.id,
        spec=spec,
        inoculated_at=when,
        lifecycle_phase=STAGE_INOCULATED,
        zone_id=resolved_zone,
    )
    detail = spec.to_dict()
    if resolved_zone:
        detail["zone_id"] = resolved_zone
    await batch_repo.async_insert_milestone(
        batch_id=state.batch.id,
        event_type=MILESTONE_INOCULATED,
        recorded_at=when,
        detail=detail,
    )
    await culture_repo.async_insert_culture_event(
        CultureEvent(
            event_type=EVENT_CULTURE_INOCULATED_BATCH,
            culture_id=culture.id,
            batch_id=state.batch.id,
            recorded_at=when,
            detail={
                "container_type": spec.container_type,
                "container_count": spec.container_count,
                "substrate_g_per_container": spec.substrate_g_per_container,
                "zone_id": resolved_zone,
            },
        )
    )
    hass.data[DOMAIN][entry_id]["active_culture_id"] = culture.id
    if expected_check_at:
        await _async_create_check_notification(
            hass, state.batch.id, expected_check_at
        )
    _LOGGER.info(
        "Inoculated batch %s with culture %s containers=%s×%s zone=%s",
        updated.id,
        culture.id,
        spec.container_count,
        spec.container_type,
        resolved_zone,
    )
    _notify_batch(hass, entry_id)
    return state.batch.id


async def async_advance_production_stage(
    hass: HomeAssistant,
    entry_id: str,
    *,
    target_stage: str | None = None,
    zone_id: str | None = None,
) -> str:
    state = _state(hass, entry_id)
    batch_repo = _batch_repo(hass, entry_id)
    batch = await batch_repo.async_get_batch(state.batch.id)
    if batch is None:
        raise HomeAssistantError(f"unknown batch_id: {state.batch.id}")
    try:
        resolved = assert_can_advance(batch.lifecycle_phase, target_stage)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

    when = datetime.now(tz=UTC).isoformat()
    milestone = _ADVANCE_MILESTONE[resolved]
    detail: dict = {"from": batch.lifecycle_phase, "to": resolved}
    if zone_id:
        from . import location_actions

        await location_actions.async_set_batch_location(
            hass, entry_id, zone_id=zone_id, batch_id=batch.id
        )
        detail["zone_id"] = str(zone_id).strip()
    await batch_repo.async_insert_milestone(
        batch_id=batch.id,
        event_type=milestone,
        recorded_at=when,
        detail=detail,
    )
    phase = MILESTONE_TO_PHASE.get(milestone, resolved)
    await batch_repo.async_set_lifecycle_phase(batch.id, phase)
    _LOGGER.info("Batch %s advanced %s → %s", batch.id, batch.lifecycle_phase, phase)
    _notify_batch(hass, entry_id)
    return phase


async def async_record_harvest(
    hass: HomeAssistant,
    entry_id: str,
    *,
    mass_g: float,
    is_final: bool = False,
    notes: str | None = None,
    zone_id: str | None = None,
) -> str:
    state = _state(hass, entry_id)
    batch_repo = _batch_repo(hass, entry_id)
    batch = await batch_repo.async_get_batch(state.batch.id)
    if batch is None:
        raise HomeAssistantError(f"unknown batch_id: {state.batch.id}")

    try:
        assert_can_harvest(
            lifecycle_phase=batch.lifecycle_phase,
            flush_count=batch.flush_count,
            max_flushes=batch.max_flushes or DEFAULT_MAX_FLUSHES,
            mass_g=mass_g,
            is_final=is_final,
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

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

    when = datetime.now(tz=UTC).isoformat()
    if batch.lifecycle_phase == STAGE_FRUITING:
        await batch_repo.async_insert_milestone(
            batch_id=batch.id,
            event_type=MILESTONE_HARVEST_STARTED,
            recorded_at=when,
        )
        await batch_repo.async_set_lifecycle_phase(batch.id, STAGE_HARVESTING)

    flush_number = int(batch.flush_count or 0) + 1
    event = HarvestEvent(
        batch_id=batch.id,
        mass_g=float(mass_g),
        recorded_at=when,
        flush_number=flush_number,
        is_final=is_final,
        notes=notes,
        zone_id=resolved_zone,
    )
    await batch_repo.async_insert_harvest(event)
    harvest_detail: dict = {
        "flush_number": flush_number,
        "mass_g": float(mass_g),
        "is_final": is_final,
    }
    if resolved_zone:
        harvest_detail["zone_id"] = resolved_zone
    await batch_repo.async_insert_milestone(
        batch_id=batch.id,
        event_type=MILESTONE_HARVEST_RECORDED,
        recorded_at=when,
        detail=harvest_detail,
    )
    if is_final:
        await batch_repo.async_complete_batch(batch.id, when)
        _LOGGER.info("Batch %s final harvest flush=%s mass=%sg", batch.id, flush_number, mass_g)
    else:
        _LOGGER.info("Batch %s harvest flush=%s mass=%sg", batch.id, flush_number, mass_g)
    _notify_batch(hass, entry_id)
    return event.id


async def async_add_batch_note(
    hass: HomeAssistant,
    entry_id: str,
    *,
    note: str,
) -> None:
    if not note or not str(note).strip():
        raise HomeAssistantError("note is required")
    state = _state(hass, entry_id)
    batch_repo = _batch_repo(hass, entry_id)
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
        event_type=MILESTONE_BATCH_NOTE,
        recorded_at=when,
        detail={"note": str(note).strip()},
    )
    _notify_batch(hass, entry_id)


async def async_set_check_reminder(
    hass: HomeAssistant,
    entry_id: str,
    *,
    expected_check_at: str,
) -> None:
    if not expected_check_at or not str(expected_check_at).strip():
        raise HomeAssistantError("expected_check_at is required")
    state = _state(hass, entry_id)
    batch_repo = _batch_repo(hass, entry_id)
    when = datetime.now(tz=UTC).isoformat()
    check_at = str(expected_check_at).strip()
    await batch_repo.async_ensure_batch(
        batch_id=state.batch.id,
        site_id=state.site.id,
        environment_id=state.environment.id,
        name=state.batch.name,
        nfc_uid=state.batch.nfc_uid,
    )
    await batch_repo.async_set_expected_check_at(state.batch.id, check_at)
    await batch_repo.async_insert_milestone(
        batch_id=state.batch.id,
        event_type=MILESTONE_CHECK_REMINDER_SET,
        recorded_at=when,
        detail={"expected_check_at": check_at},
    )
    await _async_create_check_notification(hass, state.batch.id, check_at)
    _notify_batch(hass, entry_id)


async def _async_create_check_notification(
    hass: HomeAssistant, batch_id: str, expected_check_at: str
) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "Communifarm check reminder",
            "message": (
                f"Batch `{batch_id}` expected check at **{expected_check_at}**."
            ),
            "notification_id": f"communifarm_check_{batch_id}",
        },
        blocking=False,
    )


async def async_production_summary(
    hass: HomeAssistant, entry_id: str
) -> ProductionSummary:
    from . import location_actions

    state = _state(hass, entry_id)
    batch_repo = _batch_repo(hass, entry_id)
    batch = await batch_repo.async_get_batch(state.batch.id)
    harvests = await batch_repo.async_list_harvests(state.batch.id) if batch else []
    total = sum(h.mass_g for h in harvests)
    if batch is None:
        return ProductionSummary(
            batch_id=state.batch.id,
            lifecycle_phase="planned",
        )
    loc = await location_actions.async_resolve_location_attrs(
        hass,
        entry_id,
        zone_id=batch.zone_id,
        lifecycle_phase=batch.lifecycle_phase,
    )
    return ProductionSummary(
        batch_id=batch.id,
        lifecycle_phase=batch.lifecycle_phase,
        culture_id=batch.culture_id,
        container_type=batch.container_type,
        container_count=batch.container_count,
        substrate_g_per_container=batch.substrate_g_per_container,
        inoculum_amount=batch.inoculum_amount,
        inoculum_unit=batch.inoculum_unit,
        flush_count=batch.flush_count,
        max_flushes=batch.max_flushes or DEFAULT_MAX_FLUSHES,
        expected_check_at=batch.expected_check_at,
        inoculated_at=batch.inoculated_at,
        zone_id=batch.zone_id,
        area_name=loc.get("area_name"),
        area_kind=loc.get("area_kind"),
        zone_name=loc.get("zone_name"),
        suggested_area_kind=loc.get("suggested_area_kind"),
        location_warning=loc.get("location_warning"),
        total_harvest_g=total,
        harvests=[h.to_dict() for h in harvests],
    )


def production_summary_markdown(summary: ProductionSummary) -> str:
    return format_production_markdown(summary)
