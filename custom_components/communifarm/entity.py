"""Shared Communifarm entity plumbing.

Two levels only: this base, then one platform base in the platform module.
Subclasses override behavior. ``entity_id`` and ``unique_id`` stay explicit.
"""

from __future__ import annotations

import inspect
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .domain.models import CommunifarmState


class CommunifarmEntity:
    """Entry bucket, stable unique_id, and explicit entity_id."""

    _attr_has_entity_name = True
    hass: HomeAssistant

    def __init__(
        self,
        entry_id: str,
        *,
        entity_id: str,
        name: str | None = None,
        unique_id: str | None = None,
        icon: str | None = None,
    ) -> None:
        self._entry_id = entry_id
        self.entity_id = entity_id
        if name is not None:
            self._attr_name = name
        if unique_id is not None:
            self._attr_unique_id = unique_id
        if icon is not None:
            self._attr_icon = icon

    def bucket(self) -> dict[str, Any]:
        """Runtime dict for this config entry (state, repos, drafts)."""
        return self.hass.data[DOMAIN][self._entry_id]

    def runtime_state(self) -> CommunifarmState:
        """Domain state stored on the entry bucket."""
        return self.bucket()["state"]

    def listen_entry_signals(self, *signals: str, method: str) -> None:
        """Refresh when a dispatcher signal targets this config entry.

        ``method`` is an instance method name. Async methods are scheduled;
        sync methods run inline (they write state themselves).
        """
        refresh = getattr(self, method)

        @callback
        def _on_signal(signaled_entry_id: str) -> None:
            if signaled_entry_id != self._entry_id:
                return
            result = refresh()
            if inspect.isawaitable(result):
                self.hass.async_create_task(result)

        for signal in signals:
            self.async_on_remove(
                async_dispatcher_connect(self.hass, signal, _on_signal)
            )
