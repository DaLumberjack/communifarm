"""Provision a Communifarm-managed Lovelace dashboard via lovelace storage."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import lovelace
from homeassistant.components.lovelace import dashboard as lovelace_dashboard
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..const import DASHBOARD_TITLE, DASHBOARD_URL_PATH, DOMAIN
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


async def _async_save_lovelace(hass: HomeAssistant, config: dict[str, Any]) -> None:
    """Register and save a storage-mode dashboard when lovelace APIs allow it."""
    # Prefer modern lovelace dashboard collection when available.
    if hasattr(lovelace, "async_get_resource_items"):
        pass

    dashboards = hass.data.get("lovelace")
    if dashboards is None:
        hass.data.setdefault(DOMAIN, {})["dashboard_config"] = config
        _LOGGER.info("Lovelace not ready; stored dashboard config in integration data")
        return

    # Store a copy for tests and diagnostics regardless of lovelace mode.
    hass.data.setdefault(DOMAIN, {})["dashboard_config"] = config

    try:
        from homeassistant.components.lovelace.const import (  # type: ignore
            LOVELACE_DATA,
        )
    except ImportError:
        LOVELACE_DATA = "lovelace"

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return

    # Attempt to register URL path if the collection API exists.
    dashboards_collection = getattr(lovelace_data, "dashboards", None)
    if dashboards_collection is None and isinstance(lovelace_data, dict):
        # Older/layout-agnostic fallback: keep config in DOMAIN data only.
        return

    url_path = DASHBOARD_URL_PATH
    existing = None
    if hasattr(dashboards_collection, "async_get_info"):
        try:
            existing = dashboards_collection.async_get_info().get(url_path)
        except Exception:  # noqa: BLE001
            existing = None

    if existing is None and hasattr(dashboards_collection, "async_create_item"):
        await dashboards_collection.async_create_item(
            {
                "id": url_path,
                "url_path": url_path,
                "title": DASHBOARD_TITLE,
                "require_admin": False,
                "show_in_sidebar": True,
            }
        )

    # Save YAML-like config into the dashboard storage if possible.
    dashboard_obj = None
    if isinstance(dashboards_collection, dict):
        dashboard_obj = dashboards_collection.get(url_path)
    elif hasattr(dashboards_collection, "async_get"):
        try:
            dashboard_obj = dashboards_collection.async_get(url_path)
        except Exception:  # noqa: BLE001
            dashboard_obj = None

    if dashboard_obj is not None and hasattr(dashboard_obj, "async_save"):
        await dashboard_obj.async_save(config)
    elif lovelace_dashboard is not None:
        _LOGGER.debug("Dashboard object save skipped; config retained in DOMAIN data")
