"""Store-backed repository for Communifarm domain state."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..const import STORAGE_KEY, STORAGE_VERSION
from ..domain.models import CommunifarmState


class CommunifarmRepository:
    """Persist and reload CommunifarmState via Home Assistant Store."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._state: CommunifarmState | None = None

    @property
    def state(self) -> CommunifarmState | None:
        return self._state

    async def async_load(self) -> CommunifarmState | None:
        data = await self._store.async_load()
        if not data or "site" not in data:
            self._state = None
            return None
        self._state = CommunifarmState.from_dict(data)
        return self._state

    async def async_save(self, state: CommunifarmState) -> None:
        state.profile.validate()
        self._state = state
        await self._store.async_save(state.to_dict())

    async def async_clear(self) -> None:
        self._state = None
        await self._store.async_remove()
