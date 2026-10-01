"""SQLite repository for Communifarm weight / material events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from homeassistant.core import HomeAssistant

from ..domain.weight import WeightEvent
from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


class WeightEventRepository:
    """Append-only weight events for local analysis and future cloud sync."""

    def __init__(self, hass: HomeAssistant, path: Path | None = None) -> None:
        self._hass = hass
        self._path = path or sqlite_db.db_path_for_config_dir(hass.config.config_dir)
        self._conn = None

    @property
    def path(self) -> Path:
        return self._path

    async def async_setup(self) -> None:
        await self._hass.async_add_executor_job(self._setup_sync)

    def _setup_sync(self) -> None:
        with sqlite_db.DB_LOCK:
            self._conn = sqlite_db.connect(self._path)
            version = sqlite_db.apply_migrations(self._conn)
        _LOGGER.info("Communifarm SQLite ready at %s (schema v%s)", self._path, version)

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


    async def async_insert(self, event: WeightEvent) -> WeightEvent:
        await self._hass.async_add_executor_job(self._locked, self._insert_sync, event)
        return event

    def _insert_sync(self, event: WeightEvent) -> None:
        assert self._conn is not None
        created = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO weight_events (
              stable_id, site_id, environment_id, batch_id,
              ingredient_key, ingredient_label, mass_g, unit,
              source_entity_id, nfc_uid, recorded_at, created_at,
              recipe_scale, target_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.site_id,
                event.environment_id,
                event.batch_id,
                event.ingredient_key,
                event.ingredient_label,
                float(event.mass_g),
                event.unit,
                event.source_entity_id,
                event.nfc_uid,
                event.recorded_at,
                created,
                event.recipe_scale,
                event.target_amount,
            ),
        )
        self._conn.commit()

    async def async_list_for_batch(self, batch_id: str) -> list[WeightEvent]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_for_batch_sync, batch_id
        )

    def _list_for_batch_sync(self, batch_id: str) -> list[WeightEvent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT stable_id, site_id, environment_id, batch_id,
                   ingredient_key, ingredient_label, mass_g, unit,
                   source_entity_id, nfc_uid, recorded_at,
                   recipe_scale, target_amount
            FROM weight_events
            WHERE batch_id = ?
            ORDER BY recorded_at ASC, id ASC
            """,
            (batch_id,),
        ).fetchall()
        return [
            WeightEvent(
                id=row["stable_id"],
                site_id=row["site_id"],
                environment_id=row["environment_id"],
                batch_id=row["batch_id"],
                ingredient_key=row["ingredient_key"],
                ingredient_label=row["ingredient_label"],
                mass_g=float(row["mass_g"]),
                unit=row["unit"],
                source_entity_id=row["source_entity_id"],
                nfc_uid=row["nfc_uid"],
                recorded_at=row["recorded_at"],
                recipe_scale=row["recipe_scale"],
                target_amount=row["target_amount"],
            )
            for row in rows
        ]
