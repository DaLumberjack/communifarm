"""Culture / media application helpers (services)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .domain.culture import (
    CONTAINER_JAR,
    CONTAINER_PLATE,
    CONTAINER_SYRINGE,
    CULTURE_CONTAINERS,
    CULTURE_FORMS,
    DEFAULT_AGAR_RECIPE_KEY,
    EVENT_CULTURE_LOCATION_SET,
    EVENT_MEDIA_LOCATION_SET,
    FORM_AGAR,
    FORM_SPORES,
    MEDIA_MILESTONES,
    SOURCE_TYPES,
    CultureEvent,
    CultureLot,
    MediaWeightEvent,
    build_media_batch_from_recipe,
    media_recipe_lines,
    target_for_media_ingredient,
    validate_media_amount,
)
from .domain.location import (
    suggest_area_kind_for_culture_form,
    suggest_area_kind_for_media_status,
)
from .domain.models import CommunifarmState
from .domain.recipe import clamp_recipe_scale
from .domain.validation import ValidationError, validate_ingredient_label, validate_readable_name
from .domain.weight import ingredient_key_from_label
from .storage.culture_repository import CultureRepository
from .storage.location_repository import LocationRepository

_LOGGER = logging.getLogger(__name__)


def _repo(hass: HomeAssistant, entry_id: str) -> CultureRepository:
    bucket = hass.data[DOMAIN][entry_id]
    repo = bucket.get("culture_repository")
    if repo is None:
        raise HomeAssistantError("Culture repository is not available")
    return repo


def _location_repo(hass: HomeAssistant, entry_id: str) -> LocationRepository:
    repo = hass.data[DOMAIN][entry_id].get("location_repository")
    if repo is None:
        raise HomeAssistantError("Location repository is not available")
    return repo


def _state(hass: HomeAssistant, entry_id: str) -> CommunifarmState:
    return hass.data[DOMAIN][entry_id]["state"]


async def _require_zone(
    hass: HomeAssistant, entry_id: str, zone_id: str | None
) -> str | None:
    """Validate optional zone_id; return stripped id or None."""
    if zone_id is None or not str(zone_id).strip():
        return None
    resolved = str(zone_id).strip()
    zone = await _location_repo(hass, entry_id).async_get_zone(resolved)
    if zone is None:
        raise HomeAssistantError(f"unknown zone_id: {zone_id}")
    return resolved


async def async_create_media_batch(
    hass: HomeAssistant,
    entry_id: str,
    *,
    recipe_key: str = DEFAULT_AGAR_RECIPE_KEY,
    name: str | None = None,
    recipe_scale: float = 1.0,
    vessel_count: int | None = None,
    zone_id: str | None = None,
) -> str:
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    resolved_zone = await _require_zone(hass, entry_id, zone_id)
    try:
        batch = build_media_batch_from_recipe(
            site_id=state.site.id,
            environment_id=state.environment.id,
            recipe_key=recipe_key,
            name=name,
            recipe_scale=recipe_scale,
            vessel_count=vessel_count,
            zone_id=resolved_zone,
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    if resolved_zone:
        loc_repo = _location_repo(hass, entry_id)
        zone = await loc_repo.async_get_zone(resolved_zone)
        area = await loc_repo.async_get_area(zone.area_id) if zone else None
        suggested = suggest_area_kind_for_media_status(batch.status)
        if suggested and area is not None and area.area_kind != suggested:
            _LOGGER.warning(
                "soft warning: media status %s usually uses %s; zone is in %s",
                batch.status,
                suggested,
                area.area_kind,
            )
    await repo.async_create_media_batch(batch)
    hass.data[DOMAIN][entry_id]["active_media_batch_id"] = batch.id
    _LOGGER.info("Created media batch %s recipe=%s", batch.id, batch.recipe_key)
    return batch.id


async def async_record_media_weight(
    hass: HomeAssistant,
    entry_id: str,
    *,
    media_batch_id: str,
    amount: float,
    unit: str,
    ingredient: str,
) -> str:
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    media = await repo.async_get_media_batch(media_batch_id)
    if media is None:
        raise HomeAssistantError(f"unknown media_batch_id: {media_batch_id}")
    try:
        label = validate_ingredient_label(ingredient, required=True)
        assert label is not None
        value, unit_norm = validate_media_amount(amount, unit)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

    key = ingredient_key_from_label(label)
    scale = clamp_recipe_scale(media.recipe_scale)
    target = target_for_media_ingredient(media.recipe_key, key, scale)
    target_amount = target[0] if target else None
    when = datetime.now(tz=UTC).isoformat()
    event = MediaWeightEvent(
        site_id=state.site.id,
        environment_id=state.environment.id,
        media_batch_id=media.id,
        amount=value,
        unit=unit_norm,
        recorded_at=when,
        ingredient_key=key,
        ingredient_label=label,
        recipe_scale=scale,
        target_amount=target_amount,
    )
    await repo.async_insert_media_weight(event)
    await repo.async_ensure_weighing_started(media.id, when)
    _LOGGER.info(
        "Media weight %s batch=%s ingredient=%s amount=%s%s",
        event.id,
        media.id,
        key,
        value,
        unit_norm,
    )
    return event.id


async def async_record_media_milestone(
    hass: HomeAssistant,
    entry_id: str,
    *,
    media_batch_id: str,
    event_type: str,
) -> None:
    repo = _repo(hass, entry_id)
    if event_type not in MEDIA_MILESTONES:
        raise HomeAssistantError(f"Unsupported media milestone: {event_type}")
    media = await repo.async_get_media_batch(media_batch_id)
    if media is None:
        raise HomeAssistantError(f"unknown media_batch_id: {media_batch_id}")
    when = datetime.now(tz=UTC).isoformat()
    await repo.async_insert_media_milestone(
        media_batch_id=media.id,
        event_type=event_type,
        recorded_at=when,
    )
    _LOGGER.info("Media %s milestone %s", media.id, event_type)


async def async_acquire_culture(
    hass: HomeAssistant,
    entry_id: str,
    *,
    name: str,
    source_type: str,
    form: str,
    container: str | None = None,
    strain_label: str = "",
    zone_id: str | None = None,
) -> str:
    state = _state(hass, entry_id)
    repo = _repo(hass, entry_id)
    if source_type not in SOURCE_TYPES:
        raise HomeAssistantError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
    if form not in CULTURE_FORMS:
        raise HomeAssistantError(f"form must be one of {sorted(CULTURE_FORMS)}")
    resolved_container = container
    if resolved_container is None:
        if form == FORM_SPORES:
            resolved_container = CONTAINER_SYRINGE
        elif form == FORM_AGAR:
            resolved_container = CONTAINER_PLATE
        else:
            resolved_container = CONTAINER_JAR
    if resolved_container not in CULTURE_CONTAINERS:
        raise HomeAssistantError(f"container must be one of {sorted(CULTURE_CONTAINERS)}")
    resolved_zone = await _require_zone(hass, entry_id, zone_id)
    try:
        validate_readable_name(name, field_name="culture name")
        lot = CultureLot(
            site_id=state.site.id,
            environment_id=state.environment.id,
            name=name,
            source_type=source_type,
            form=form,
            container=resolved_container,
            strain_label=strain_label or "",
            zone_id=resolved_zone,
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    if resolved_zone:
        loc_repo = _location_repo(hass, entry_id)
        zone = await loc_repo.async_get_zone(resolved_zone)
        area = await loc_repo.async_get_area(zone.area_id) if zone else None
        suggested = suggest_area_kind_for_culture_form(form)
        if suggested and area is not None and area.area_kind != suggested:
            _LOGGER.warning(
                "soft warning: culture form %s usually uses %s; zone is in %s",
                form,
                suggested,
                area.area_kind,
            )
    await repo.async_acquire_culture(lot)
    hass.data[DOMAIN][entry_id]["active_culture_id"] = lot.id
    _LOGGER.info("Acquired culture %s source=%s form=%s", lot.id, source_type, form)
    return lot.id


async def async_introduce_culture(
    hass: HomeAssistant,
    entry_id: str,
    *,
    culture_id: str,
    media_batch_id: str,
    child_name: str | None = None,
    zone_id: str | None = None,
) -> str:
    repo = _repo(hass, entry_id)
    resolved_zone = await _require_zone(hass, entry_id, zone_id)
    try:
        child, _event = await repo.async_introduce_culture(
            parent_culture_id=culture_id,
            media_batch_id=media_batch_id,
            child_name=child_name,
            zone_id=resolved_zone,
        )
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err
    _LOGGER.info(
        "Introduced culture %s into media %s → child %s",
        culture_id,
        media_batch_id,
        child.id,
    )
    return child.id


async def async_set_culture_location(
    hass: HomeAssistant,
    entry_id: str,
    *,
    culture_id: str,
    zone_id: str,
) -> str:
    repo = _repo(hass, entry_id)
    if not zone_id or not str(zone_id).strip():
        raise HomeAssistantError("zone_id is required")
    resolved_zone = await _require_zone(hass, entry_id, zone_id)
    assert resolved_zone is not None
    lot = await repo.async_get_culture(culture_id)
    if lot is None:
        raise HomeAssistantError(f"unknown culture_id: {culture_id}")

    loc_repo = _location_repo(hass, entry_id)
    zone = await loc_repo.async_get_zone(resolved_zone)
    area = await loc_repo.async_get_area(zone.area_id) if zone else None
    suggested = suggest_area_kind_for_culture_form(lot.form)
    if suggested and area is not None and area.area_kind != suggested:
        _LOGGER.warning(
            "soft warning: culture form %s usually uses %s; zone is in %s",
            lot.form,
            suggested,
            area.area_kind,
        )

    when = datetime.now(tz=UTC).isoformat()
    await repo.async_set_culture_zone(lot.id, resolved_zone)
    await repo.async_insert_culture_event(
        CultureEvent(
            event_type=EVENT_CULTURE_LOCATION_SET,
            culture_id=lot.id,
            recorded_at=when,
            detail={
                "zone_id": resolved_zone,
                "area_id": zone.area_id if zone else None,
                "area_kind": area.area_kind if area else None,
                "previous_zone_id": lot.zone_id,
            },
        )
    )
    _LOGGER.info(
        "Culture %s placed in zone %s (%s / %s)",
        lot.id,
        resolved_zone,
        area.name if area else (zone.area_id if zone else "?"),
        zone.name if zone else "?",
    )
    return resolved_zone


async def async_set_media_location(
    hass: HomeAssistant,
    entry_id: str,
    *,
    media_batch_id: str,
    zone_id: str,
) -> str:
    repo = _repo(hass, entry_id)
    if not zone_id or not str(zone_id).strip():
        raise HomeAssistantError("zone_id is required")
    resolved_zone = await _require_zone(hass, entry_id, zone_id)
    assert resolved_zone is not None
    media = await repo.async_get_media_batch(media_batch_id)
    if media is None:
        raise HomeAssistantError(f"unknown media_batch_id: {media_batch_id}")

    loc_repo = _location_repo(hass, entry_id)
    zone = await loc_repo.async_get_zone(resolved_zone)
    area = await loc_repo.async_get_area(zone.area_id) if zone else None
    suggested = suggest_area_kind_for_media_status(media.status)
    if suggested and area is not None and area.area_kind != suggested:
        _LOGGER.warning(
            "soft warning: media status %s usually uses %s; zone is in %s",
            media.status,
            suggested,
            area.area_kind,
        )

    when = datetime.now(tz=UTC).isoformat()
    await repo.async_set_media_zone(media.id, resolved_zone)
    await repo.async_insert_culture_event(
        CultureEvent(
            event_type=EVENT_MEDIA_LOCATION_SET,
            media_batch_id=media.id,
            recorded_at=when,
            detail={
                "zone_id": resolved_zone,
                "area_id": zone.area_id if zone else None,
                "area_kind": area.area_kind if area else None,
                "previous_zone_id": media.zone_id,
            },
        )
    )
    _LOGGER.info(
        "Media %s placed in zone %s (%s / %s)",
        media.id,
        resolved_zone,
        area.name if area else (zone.area_id if zone else "?"),
        zone.name if zone else "?",
    )
    return resolved_zone


def media_recipe_summary(recipe_key: str = DEFAULT_AGAR_RECIPE_KEY) -> list[dict[str, str | float]]:
    """Helper for tests / future sensors."""
    return [
        {"key": line.key, "label": line.label, "amount": line.amount, "unit": line.unit}
        for line in media_recipe_lines(recipe_key)
    ]
