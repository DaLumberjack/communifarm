"""Dashboard provisioner tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.communifarm.const import (
    DASHBOARD_TITLE,
    DASHBOARD_URL_PATH,
    DOMAIN,
)
from custom_components.communifarm.dashboard.provisioner import (
    _live_dashboards_collection,
    async_provision_dashboard,
)
from custom_components.communifarm.domain.models import CommunifarmState


@pytest.mark.asyncio
async def test_provision_creates_storage_dashboard_and_saves(
    hass: HomeAssistant, sample_state: CommunifarmState
) -> None:
    """Provisioner must create a lovelace storage dashboard and save views."""
    store = MagicMock()
    store.async_save = AsyncMock()

    collection = MagicMock()
    collection.async_items.return_value = []

    dashboards: dict = {}
    lovelace_data = SimpleNamespace(dashboards=dashboards)

    async def create_item(_payload: dict) -> dict:
        item = {
            "id": DASHBOARD_URL_PATH,
            "url_path": DASHBOARD_URL_PATH,
            "title": DASHBOARD_TITLE,
            "icon": "mdi:sprout",
            "require_admin": False,
            "show_in_sidebar": True,
            "mode": "storage",
        }
        # Mimic HA's storage_dashboard_changed listener.
        dashboards[DASHBOARD_URL_PATH] = store
        return item

    collection.async_create_item = create_item

    handler_self = SimpleNamespace(storage_collection=collection)

    def create_handler(*_args, **_kwargs):
        return None

    create_handler.__self__ = handler_self  # type: ignore[attr-defined]

    hass.data["websocket_api"] = {"lovelace/dashboards/create": (create_handler, None)}

    with patch(
        "custom_components.communifarm.dashboard.provisioner._lovelace_const"
    ) as const_mod:
        const_mod.return_value = SimpleNamespace(
            LOVELACE_DATA="lovelace",
            DOMAIN="lovelace",
            MODE_STORAGE="storage",
            CONF_ALLOW_SINGLE_WORD="allow_single_word",
            CONF_URL_PATH="url_path",
            CONF_TITLE="title",
            CONF_ICON="icon",
            CONF_REQUIRE_ADMIN="require_admin",
            CONF_SHOW_IN_SIDEBAR="show_in_sidebar",
        )
        hass.data["lovelace"] = lovelace_data
        url = await async_provision_dashboard(hass, sample_state)

    assert url == f"/{DASHBOARD_URL_PATH}/overview"
    assert hass.data[DOMAIN]["dashboard_config"]["title"] == DASHBOARD_TITLE
    store.async_save.assert_awaited()


def test_live_dashboards_collection_unwraps_websocket_handler(
    hass: HomeAssistant,
) -> None:
    collection = object()
    handler_self = SimpleNamespace(storage_collection=collection)

    def inner():
        return None

    inner.__self__ = handler_self  # type: ignore[attr-defined]

    def outer():
        return None

    outer.__wrapped__ = inner  # type: ignore[attr-defined]

    hass.data["websocket_api"] = {"lovelace/dashboards/create": (outer, None)}
    assert _live_dashboards_collection(hass) is collection
