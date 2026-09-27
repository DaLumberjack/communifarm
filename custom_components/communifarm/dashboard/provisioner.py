"""Provision a Communifarm-managed Lovelace dashboard via lovelace storage."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.lovelace import dashboard as lovelace_dashboard
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..const import (
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL_PATH,
    DOMAIN,
)
from ..domain.models import CommunifarmState
from .builder import DashboardBuilder

_LOGGER = logging.getLogger(__name__)


def resolve_bindings(hass: HomeAssistant, state: CommunifarmState) -> dict[str, str | None]:
    """Resolve role -> current entity_id from stable entity registry entry ids."""
    registry = er.async_get(hass)
    resolved: dict[str, str | None] = {}
    for binding in state.bindings:
        entry = None
        entities = getattr(registry, "entities", None)
        if entities is not None and hasattr(entities, "get_entry"):
            entry = entities.get_entry(binding.entity_entry_id)
        if entry is None and binding.entity_id:
            entry = registry.async_get(binding.entity_id)
        if entry is not None:
            resolved[binding.role] = entry.entity_id
        else:
            resolved[binding.role] = binding.entity_id
    return resolved


async def async_provision_dashboard(
    hass: HomeAssistant, state: CommunifarmState
) -> str:
    """Create or update the Communifarm dashboard; return relative URL path."""
    resolved = resolve_bindings(hass, state)
    config = DashboardBuilder().build(state, resolved)

    try:
        await _async_save_lovelace(hass, config)
    except Exception:  # noqa: BLE001 - dashboard is best-effort in MVP
        _LOGGER.exception("Failed to provision Communifarm dashboard")
        hass.data.setdefault(DOMAIN, {})["dashboard_config"] = config

    return f"/{DASHBOARD_URL_PATH}/overview"


def _lovelace_const() -> Any:
    """Import lovelace constants lazily (HA version variance)."""
    from homeassistant.components.lovelace import const as lovelace_const

    return lovelace_const


def _live_dashboards_collection(hass: HomeAssistant) -> Any | None:
    """Return HA's live DashboardsCollection via the websocket create handler.

    Lovelace keeps the collection in a setup closure; the websocket create
    handler is the supported in-process handle that shares listeners/panel
    registration. A second DashboardsCollection instance would persist to disk
    but leave HA's in-memory collection stale (and risk being wiped).
    """
    handlers = hass.data.get("websocket_api") or {}
    entry = handlers.get("lovelace/dashboards/create")
    if not entry:
        return None
    handler = entry[0]
    # Unwrap websocket decorator layers until we reach the bound method.
    seen: set[int] = set()
    while True:
        if id(handler) in seen:
            break
        seen.add(id(handler))
        if hasattr(handler, "__self__") and hasattr(
            handler.__self__, "storage_collection"
        ):
            return handler.__self__.storage_collection
        next_handler = getattr(handler, "__wrapped__", None)
        if next_handler is None:
            break
        handler = next_handler
    return None


async def _async_register_panel(
    hass: HomeAssistant, item: dict[str, Any], *, update: bool
) -> None:
    """Register the Communifarm Lovelace panel in the frontend sidebar."""
    lovelace_const = _lovelace_const()
    frontend.async_register_built_in_panel(
        hass,
        lovelace_const.DOMAIN,
        frontend_url_path=item[lovelace_const.CONF_URL_PATH],
        require_admin=item.get(lovelace_const.CONF_REQUIRE_ADMIN, False),
        show_in_sidebar=item.get(lovelace_const.CONF_SHOW_IN_SIDEBAR, True),
        sidebar_title=item.get(lovelace_const.CONF_TITLE, DASHBOARD_TITLE),
        sidebar_icon=item.get(lovelace_const.CONF_ICON, DASHBOARD_ICON),
        config={"mode": lovelace_const.MODE_STORAGE},
        update=update,
    )


async def _async_ensure_dashboard_item(
    hass: HomeAssistant, lovelace_data: Any
) -> Any:
    """Ensure a storage dashboard exists and is present in lovelace_data.dashboards."""
    lovelace_const = _lovelace_const()
    url_path = DASHBOARD_URL_PATH

    existing = lovelace_data.dashboards.get(url_path)
    if existing is not None:
        return existing

    create_payload = {
        lovelace_const.CONF_ALLOW_SINGLE_WORD: True,
        lovelace_const.CONF_URL_PATH: url_path,
        lovelace_const.CONF_TITLE: DASHBOARD_TITLE,
        lovelace_const.CONF_ICON: DASHBOARD_ICON,
        lovelace_const.CONF_REQUIRE_ADMIN: False,
        lovelace_const.CONF_SHOW_IN_SIDEBAR: True,
    }

    collection = _live_dashboards_collection(hass)
    item: dict[str, Any] | None = None
    if collection is not None:
        for candidate in collection.async_items():
            if candidate.get(lovelace_const.CONF_URL_PATH) == url_path:
                item = candidate
                break
        if item is None:
            item = await collection.async_create_item(create_payload)
            # Live collection listeners register the panel; still ensure store.
    else:
        # Fallback: persist via a fresh collection, then register manually.
        _LOGGER.warning(
            "Live Lovelace dashboards collection unavailable; "
            "persisting Communifarm dashboard via storage fallback"
        )
        fallback = lovelace_dashboard.DashboardsCollection(hass)
        await fallback.async_load()
        for candidate in fallback.async_items():
            if candidate.get(lovelace_const.CONF_URL_PATH) == url_path:
                item = candidate
                break
        if item is None:
            item = await fallback.async_create_item(create_payload)

    assert item is not None
    store = lovelace_data.dashboards.get(url_path)
    if store is None:
        store = lovelace_dashboard.LovelaceStorage(hass, item)
        lovelace_data.dashboards[url_path] = store
        await _async_register_panel(hass, item, update=False)
    return store


async def _async_save_lovelace(hass: HomeAssistant, config: dict[str, Any]) -> None:
    """Register and save a storage-mode dashboard when lovelace APIs allow it."""
    hass.data.setdefault(DOMAIN, {})["dashboard_config"] = config

    lovelace_const = _lovelace_const()
    lovelace_data = hass.data.get(lovelace_const.LOVELACE_DATA)
    if lovelace_data is None:
        _LOGGER.info("Lovelace not ready; stored dashboard config in integration data")
        return

    store = await _async_ensure_dashboard_item(hass, lovelace_data)
    if hasattr(store, "async_save"):
        await store.async_save(config)
        _LOGGER.info(
            "Provisioned Communifarm dashboard at /%s/overview", DASHBOARD_URL_PATH
        )
    else:
        _LOGGER.warning(
            "Communifarm dashboard store is not writable; config kept in DOMAIN data"
        )
