"""The Communifarm integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, EVENT_CALL_SERVICE, Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ALLOWED_BATCH_TRANSITIONS,
    DOMAIN,
    ENTITY_SCALE_LOCATION_TARE_BUTTON,
    ENTITY_SCALE_MASS_G,
    ENTITY_SCALE_NFC_UID,
    ENTITY_SCALE_RECORD_BUTTON,
    ENTITY_SCALE_SELECTED_INGREDIENT,
    ENTITY_SCALE_TARE_BUTTON,
    PLATFORMS,
    SERVICE_RECORD_WEIGHT,
    SERVICE_TRANSITION_BATCH,
    SIGNAL_WEIGH_SESSION_UPDATED,
    new_weigh_session_tracker,
)
from .dashboard.provisioner import async_provision_dashboard
from .domain.models import CommunifarmState
from .domain.recipe import WOOD_LOVER_RECIPE, clamp_recipe_scale
from .domain.validation import (
    ValidationError,
    WARNING_MISSING_NFC,
    WARNING_UNKNOWN_INGREDIENT,
    assess_mass_g,
    validate_ingredient_label,
    validate_nfc_uid,
    validate_recipe_unit,
)
from .domain.weight import WeightEvent, ingredient_key_from_label
from .storage.repository import CommunifarmRepository
from .storage.weight_repository import WeightEventRepository

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

TRANSITION_SCHEMA = vol.Schema(
    {
        vol.Required("stage"): vol.In(
            {stage for stages in ALLOWED_BATCH_TRANSITIONS.values() for stage in stages}
            | set(ALLOWED_BATCH_TRANSITIONS)
        )
    }
)

RECORD_WEIGHT_SCHEMA = vol.Schema(
    {
        vol.Optional("mass_g"): vol.Coerce(float),
        vol.Optional("ingredient"): cv.string,
        vol.Optional("nfc_uid"): cv.string,
    }
)

_TARE_BUTTONS = frozenset(
    {ENTITY_SCALE_TARE_BUTTON, ENTITY_SCALE_LOCATION_TARE_BUTTON}
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Communifarm (config entry only)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Communifarm from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    repo = CommunifarmRepository(hass)

    state_data = entry.data.get("state")
    if state_data:
        state = CommunifarmState.from_dict(state_data)
        await repo.async_save(state)
    else:
        state = await repo.async_load()
        if state is None:
            _LOGGER.error("Communifarm config entry has no state")
            return False

    weight_repo = WeightEventRepository(hass)
    await weight_repo.async_setup()

    hass.data[DOMAIN][entry.entry_id] = {
        "repository": repo,
        "weight_repository": weight_repo,
        "state": state,
        "weigh_session": new_weigh_session_tracker(),
    }

    dashboard_url = await async_provision_dashboard(hass, state)
    hass.data[DOMAIN][entry.entry_id]["dashboard_url"] = dashboard_url

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(p) for p in PLATFORMS]
    )

    async def async_transition_batch(call: ServiceCall) -> None:
        new_stage = call.data["stage"]
        stored = hass.data[DOMAIN][entry.entry_id]["state"]
        assert isinstance(stored, CommunifarmState)
        timestamp = datetime.now(tz=UTC).isoformat()
        stored.batch.transition(new_stage, timestamp)
        await repo.async_save(stored)
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "state": stored.to_dict()}
        )
        await hass.config_entries.async_reload(entry.entry_id)

    async def async_record_weight(call: ServiceCall) -> None:
        await _async_persist_weight_event(
            hass, entry.entry_id, call.data, raise_on_reject=True
        )

    if not hass.services.has_service(DOMAIN, SERVICE_TRANSITION_BATCH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TRANSITION_BATCH,
            async_transition_batch,
            schema=TRANSITION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RECORD_WEIGHT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RECORD_WEIGHT,
            async_record_weight,
            schema=RECORD_WEIGHT_SCHEMA,
        )

    @callback
    def _on_call_service(event: Event) -> None:
        if event.data.get("domain") != "button" or event.data.get("service") != "press":
            return
        raw = event.data.get("service_data", {}).get(ATTR_ENTITY_ID)
        entity_ids = raw if isinstance(raw, list) else [raw]
        session = hass.data[DOMAIN][entry.entry_id]["weigh_session"]
        if any(eid in _TARE_BUTTONS for eid in entity_ids):
            session["tare_seen"] = True
            async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry.entry_id)
            return
        if ENTITY_SCALE_RECORD_BUTTON not in entity_ids:
            return
        hass.async_create_task(
            _async_persist_weight_event(hass, entry.entry_id, {}, raise_on_reject=False)
        )

    unsub = hass.bus.async_listen(EVENT_CALL_SERVICE, _on_call_service)
    hass.data[DOMAIN][entry.entry_id]["unsub_record_hook"] = unsub

    # Do not add_update_listener here: profile number saves update entry.data and
    # would reload the integration on every ±1°C/±1% nudge from the dashboard.
    return True


async def _async_persist_weight_event(
    hass: HomeAssistant,
    entry_id: str,
    data: dict,
    *,
    raise_on_reject: bool = True,
) -> None:
    """Write a weight_events row from service data and/or live scale entities."""
    bucket = hass.data.get(DOMAIN, {}).get(entry_id)
    if not bucket:
        return
    state: CommunifarmState = bucket["state"]
    weight_repo: WeightEventRepository = bucket["weight_repository"]
    session: dict = bucket["weigh_session"]

    mass_state = hass.states.get(ENTITY_SCALE_MASS_G)
    select_state = hass.states.get(ENTITY_SCALE_SELECTED_INGREDIENT)
    nfc_state = hass.states.get(ENTITY_SCALE_NFC_UID)

    mass_g = data.get("mass_g")
    if mass_g is None:
        if mass_state is None or mass_state.state in ("unknown", "unavailable"):
            _LOGGER.warning("record_weight skipped: %s unavailable", ENTITY_SCALE_MASS_G)
            return
        mass_g = float(mass_state.state)

    label = data.get("ingredient")
    if label is None and select_state is not None:
        label = select_state.state
    if label in (None, "", "(none)", "unknown", "unavailable"):
        label = None

    nfc_uid = data.get("nfc_uid")
    if nfc_uid is None and nfc_state is not None and nfc_state.state not in (
        "",
        "unknown",
        "unavailable",
    ):
        nfc_uid = nfc_state.state

    warnings: list[str] = []
    try:
        label = validate_ingredient_label(label, required=False)
        nfc_uid = validate_nfc_uid(nfc_uid, required=False)
    except ValidationError as err:
        session["last_reject"] = str(err)
        session["warnings"] = []
        _LOGGER.warning("record_weight rejected: %s", err)
        async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)
        if raise_on_reject:
            raise HomeAssistantError(str(err)) from err
        return

    key = ingredient_key_from_label(label) if label else None
    scale = clamp_recipe_scale(state.recipe_scale)
    target_amount = None
    recipe_unit = "g"
    if key:
        matched = False
        for line in WOOD_LOVER_RECIPE:
            if line.key == key:
                validate_recipe_unit(line.unit)
                target_amount = line.amount * scale
                recipe_unit = line.unit
                matched = True
                break
        if not matched:
            warnings.append(WARNING_UNKNOWN_INGREDIENT)
    if label and not nfc_uid:
        warnings.append(WARNING_MISSING_NFC)

    assessment = assess_mass_g(
        float(mass_g),
        previous_mass_g=session.get("last_mass_g"),
        previous_ingredient_key=session.get("last_ingredient_key"),
        ingredient_key=key,
        tare_seen=bool(session.get("tare_seen")),
        record_count_before=int(session.get("record_count") or 0),
    )
    if not assessment.accepted:
        session["last_reject"] = assessment.reject_reason
        session["warnings"] = []
        _LOGGER.warning("record_weight rejected: %s", assessment.reject_reason)
        async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)
        if raise_on_reject:
            raise HomeAssistantError(assessment.reject_reason or "invalid mass")
        return

    warnings.extend(assessment.warnings)
    if recipe_unit:
        try:
            validate_recipe_unit(recipe_unit)
        except ValidationError as err:
            session["last_reject"] = str(err)
            async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)
            if raise_on_reject:
                raise HomeAssistantError(str(err)) from err
            return

    event = WeightEvent(
        site_id=state.site.id,
        environment_id=state.environment.id,
        batch_id=state.batch.id,
        mass_g=assessment.mass_g,
        ingredient_label=label,
        ingredient_key=key,
        source_entity_id=ENTITY_SCALE_MASS_G,
        nfc_uid=nfc_uid,
        recorded_at=datetime.now(tz=UTC).isoformat(),
        recipe_scale=scale,
        target_amount=target_amount,
        unit=recipe_unit,
    )
    await weight_repo.async_insert(event)

    session["last_mass_g"] = assessment.mass_g
    session["last_ingredient_key"] = key
    session["record_count"] = int(session.get("record_count") or 0) + 1
    session["warnings"] = warnings
    session["last_reject"] = None
    # After a successful record, require a fresh tare signal for the next
    # unstable-step check unless the operator tares again.
    session["tare_seen"] = False

    if warnings:
        _LOGGER.warning(
            "Recorded weight_event %s with calibration warnings=%s mass=%sg",
            event.id,
            warnings,
            event.mass_g,
        )
    else:
        _LOGGER.info(
            "Recorded weight_event %s mass=%sg ingredient=%s scale=%s",
            event.id,
            event.mass_g,
            event.ingredient_label,
            scale,
        )
    async_dispatcher_send(hass, SIGNAL_WEIGH_SESSION_UPDATED, entry_id)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Communifarm (call explicitly from options flow when added)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Communifarm config entry."""
    bucket = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    unsub = bucket.get("unsub_record_hook")
    if unsub:
        unsub()
    weight_repo: WeightEventRepository | None = bucket.get("weight_repository")
    if weight_repo is not None:
        await weight_repo.async_close()

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform(p) for p in PLATFORMS]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not any(key != "dashboard_config" for key in hass.data.get(DOMAIN, {})):
            if hass.services.has_service(DOMAIN, SERVICE_TRANSITION_BATCH):
                hass.services.async_remove(DOMAIN, SERVICE_TRANSITION_BATCH)
            if hass.services.has_service(DOMAIN, SERVICE_RECORD_WEIGHT):
                hass.services.async_remove(DOMAIN, SERVICE_RECORD_WEIGHT)
    return unload_ok
