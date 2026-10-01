"""Shared SQLite connection, migrations, and process-wide lock.

Repositories keep their own SQL and row mapping. Schema text stays in
``sqlite_db.MIGRATIONS``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


class SqliteRepository:
    """Open ``communifarm.db``, apply migrations, and serialize access."""

    # Eager repos resolve the path in ``__init__`` from ``config_dir``.
    # Lazy repos (container, sale) wait until setup and use ``config.path("")``.
    _eager_path = True
    # When set, setup logs ``"{label} ready at …"``. None keeps setup quiet.
    _ready_label: str | None = None

    def __init__(self, hass: HomeAssistant, path: Path | None = None) -> None:
        self._hass = hass
        self._conn = None
        if path is not None:
            self._path: Path | None = path
        elif self._eager_path:
            self._path = sqlite_db.db_path_for_config_dir(hass.config.config_dir)
        else:
            self._path = None

    @property
    def path(self) -> Path:
        assert self._path is not None
        return self._path

    async def async_setup(self) -> Path:
        return await self._hass.async_add_executor_job(self._setup_sync)

    def _setup_sync(self) -> Path:
        if self._path is None:
            self._path = sqlite_db.db_path_for_config_dir(self._hass.config.path(""))
        with sqlite_db.DB_LOCK:
            self._conn = sqlite_db.connect(self._path)
            version = sqlite_db.apply_migrations(self._conn)
            self._after_open_sync()
        if self._ready_label is not None:
            _LOGGER.info(
                "%s ready at %s (schema v%s)",
                self._ready_label,
                self._path,
                version,
            )
        return self._path

    def _after_open_sync(self) -> None:
        """Hook while ``DB_LOCK`` is held, after migrations."""

    async def async_close(self) -> None:
        await self._hass.async_add_executor_job(self._close_sync)

    def _close_sync(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _locked(self, fn, /, *args):
        """Serialize all Communifarm SQLite access (process-wide DB_LOCK)."""
        with sqlite_db.DB_LOCK:
            return fn(*args)
