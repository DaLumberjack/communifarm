"""SQLite repository for placement areas and zones."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.location import (
    PlacementArea,
    Zone,
    build_default_layout,
)
from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


class LocationRepository:
    """Placement areas + zones under a site."""

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
        self._conn = sqlite_db.connect(self._path)
        version = sqlite_db.apply_migrations(self._conn)
        _LOGGER.info(
            "Communifarm location SQLite ready at %s (schema v%s)", self._path, version
        )

    async def async_close(self) -> None:
        await self._hass.async_add_executor_job(self._close_sync)

    def _close_sync(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def async_ensure_default_layout(
        self, site_id: str
    ) -> tuple[list[PlacementArea], list[Zone]]:
        return await self._hass.async_add_executor_job(
            self._ensure_default_layout_sync, site_id
        )

    def _ensure_default_layout_sync(
        self, site_id: str
    ) -> tuple[list[PlacementArea], list[Zone]]:
        assert self._conn is not None
        existing = self._list_areas_sync(site_id)
        if existing:
            zones: list[Zone] = []
            for area in existing:
                zones.extend(self._list_zones_for_area_sync(area.id))
            return existing, zones

        layout = build_default_layout(site_id)
        when = datetime.now(tz=UTC).isoformat()
        for area in layout.areas:
            self._conn.execute(
                """
                INSERT INTO placement_areas (
                  stable_id, site_id, name, area_kind, slot_kind, slot_count,
                  created_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    area.id,
                    area.site_id,
                    area.name,
                    area.area_kind,
                    area.slot_kind,
                    area.slot_count,
                    when,
                    area.notes,
                ),
            )
            area.created_at = when
        for zone in layout.zones:
            self._conn.execute(
                """
                INSERT INTO zones (
                  stable_id, area_id, site_id, name, slot_kind, slot_index, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    zone.id,
                    zone.area_id,
                    zone.site_id,
                    zone.name,
                    zone.slot_kind,
                    zone.slot_index,
                    when,
                ),
            )
            zone.created_at = when
        self._conn.commit()
        _LOGGER.info(
            "Seeded default placement layout for site %s: %s areas, %s zones",
            site_id,
            len(layout.areas),
            len(layout.zones),
        )
        return layout.areas, layout.zones

    async def async_list_areas(self, site_id: str | None = None) -> list[PlacementArea]:
        return await self._hass.async_add_executor_job(
            self._list_areas_sync, site_id
        )

    def _list_areas_sync(self, site_id: str | None = None) -> list[PlacementArea]:
        assert self._conn is not None
        if site_id:
            rows = self._conn.execute(
                """
                SELECT * FROM placement_areas
                WHERE site_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (site_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM placement_areas ORDER BY created_at ASC, id ASC"
            ).fetchall()
        return [self._row_to_area(row) for row in rows]

    async def async_get_area(self, area_id: str) -> PlacementArea | None:
        return await self._hass.async_add_executor_job(self._get_area_sync, area_id)

    def _get_area_sync(self, area_id: str) -> PlacementArea | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM placement_areas WHERE stable_id = ?", (area_id,)
        ).fetchone()
        return self._row_to_area(row) if row else None

    async def async_list_zones_for_area(self, area_id: str) -> list[Zone]:
        return await self._hass.async_add_executor_job(
            self._list_zones_for_area_sync, area_id
        )

    def _list_zones_for_area_sync(self, area_id: str) -> list[Zone]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM zones
            WHERE area_id = ?
            ORDER BY slot_index ASC, id ASC
            """,
            (area_id,),
        ).fetchall()
        return [self._row_to_zone(row) for row in rows]

    async def async_list_zones(self, site_id: str | None = None) -> list[Zone]:
        return await self._hass.async_add_executor_job(
            self._list_zones_sync, site_id
        )

    def _list_zones_sync(self, site_id: str | None = None) -> list[Zone]:
        assert self._conn is not None
        if site_id:
            rows = self._conn.execute(
                """
                SELECT * FROM zones
                WHERE site_id = ?
                ORDER BY area_id ASC, slot_index ASC, id ASC
                """,
                (site_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM zones ORDER BY area_id ASC, slot_index ASC, id ASC"
            ).fetchall()
        return [self._row_to_zone(row) for row in rows]

    async def async_get_zone(self, zone_id: str) -> Zone | None:
        return await self._hass.async_add_executor_job(self._get_zone_sync, zone_id)

    def _get_zone_sync(self, zone_id: str) -> Zone | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM zones WHERE stable_id = ?", (zone_id,)
        ).fetchone()
        return self._row_to_zone(row) if row else None

    @staticmethod
    def _row_to_area(row: Any) -> PlacementArea:
        return PlacementArea(
            id=row["stable_id"],
            site_id=row["site_id"],
            name=row["name"],
            area_kind=row["area_kind"],
            slot_kind=row["slot_kind"],
            slot_count=int(row["slot_count"]),
            created_at=row["created_at"],
            notes=row["notes"],
        )

    @staticmethod
    def _row_to_zone(row: Any) -> Zone:
        return Zone(
            id=row["stable_id"],
            area_id=row["area_id"],
            site_id=row["site_id"],
            name=row["name"],
            slot_kind=row["slot_kind"],
            slot_index=int(row["slot_index"]),
            created_at=row["created_at"],
        )
