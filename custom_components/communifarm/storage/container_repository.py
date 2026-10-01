"""SQLite repository for per-container production units + sale packs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.container import (
    CONTAINER_STATUS_ACTIVE,
    ProductionContainer,
    SalePack,
)
from ..domain.production import DEFAULT_MAX_FLUSHES, STAGE_INOCULATED
from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


class ContainerRepository:
    """CRUD for production_containers and sale_packs."""

    def __init__(self, hass: HomeAssistant, path: Path | None = None) -> None:
        self._hass = hass
        self._path = path
        self._conn: Any = None

    async def async_setup(self) -> Path:
        return await self._hass.async_add_executor_job(self._setup_sync)

    def _setup_sync(self) -> Path:
        if self._path is None:
            self._path = sqlite_db.db_path_for_config_dir(self._hass.config.path(""))
        with sqlite_db.DB_LOCK:
            self._conn = sqlite_db.connect(self._path)
            sqlite_db.apply_migrations(self._conn)
        return self._path

    @property
    def path(self) -> Path:
        assert self._path is not None
        return self._path

    def _locked(self, fn, /, *args):
        """Serialize all Communifarm SQLite access (process-wide DB_LOCK)."""
        with sqlite_db.DB_LOCK:
            return fn(*args)


    async def async_close(self) -> None:
        await self._hass.async_add_executor_job(self._close_sync)

    def _close_sync(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def async_insert_containers(
        self, containers: list[ProductionContainer]
    ) -> list[ProductionContainer]:
        return await self._hass.async_add_executor_job(self._locked, 
            self._insert_containers_sync, containers
        )

    def _insert_containers_sync(
        self, containers: list[ProductionContainer]
    ) -> list[ProductionContainer]:
        assert self._conn is not None
        for cont in containers:
            self._conn.execute(
                """
                INSERT INTO production_containers (
                  stable_id, batch_id, container_index, container_type, nfc_uid,
                  lifecycle_phase, flush_count, max_flushes, zone_id, status,
                  created_at, completed_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cont.id,
                    cont.batch_id,
                    cont.container_index,
                    cont.container_type,
                    cont.nfc_uid,
                    cont.lifecycle_phase,
                    cont.flush_count,
                    cont.max_flushes,
                    cont.zone_id,
                    cont.status,
                    cont.created_at,
                    cont.completed_at,
                    cont.notes,
                ),
            )
        self._conn.commit()
        return containers

    async def async_get(self, container_id: str) -> ProductionContainer | None:
        return await self._hass.async_add_executor_job(self._locked, self._get_sync, container_id)

    def _get_sync(self, container_id: str) -> ProductionContainer | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM production_containers WHERE stable_id = ?",
            (container_id,),
        ).fetchone()
        return self._row_to_container(row) if row else None

    async def async_get_by_nfc(self, nfc_uid: str) -> ProductionContainer | None:
        return await self._hass.async_add_executor_job(self._locked, self._get_by_nfc_sync, nfc_uid)

    def _get_by_nfc_sync(self, nfc_uid: str) -> ProductionContainer | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM production_containers WHERE nfc_uid = ?",
            (nfc_uid,),
        ).fetchone()
        return self._row_to_container(row) if row else None

    async def async_list_for_batch(self, batch_id: str) -> list[ProductionContainer]:
        return await self._hass.async_add_executor_job(self._locked, 
            self._list_for_batch_sync, batch_id
        )

    def _list_for_batch_sync(self, batch_id: str) -> list[ProductionContainer]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM production_containers
            WHERE batch_id = ?
            ORDER BY container_index ASC
            """,
            (batch_id,),
        ).fetchall()
        return [self._row_to_container(row) for row in rows]

    async def async_update(self, container: ProductionContainer) -> ProductionContainer:
        return await self._hass.async_add_executor_job(self._locked, self._update_sync, container)

    def _update_sync(self, container: ProductionContainer) -> ProductionContainer:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE production_containers
            SET nfc_uid = ?, lifecycle_phase = ?, flush_count = ?, max_flushes = ?,
                zone_id = ?, status = ?, completed_at = ?, notes = ?
            WHERE stable_id = ?
            """,
            (
                container.nfc_uid,
                container.lifecycle_phase,
                container.flush_count,
                container.max_flushes,
                container.zone_id,
                container.status,
                container.completed_at,
                container.notes,
                container.id,
            ),
        )
        self._conn.commit()
        return container

    async def async_set_zone(
        self, container_id: str, zone_id: str | None
    ) -> None:
        await self._hass.async_add_executor_job(self._locked, 
            self._set_zone_sync, container_id, zone_id
        )

    def _set_zone_sync(self, container_id: str, zone_id: str | None) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE production_containers SET zone_id = ? WHERE stable_id = ?",
            (zone_id, container_id),
        )
        self._conn.commit()

    async def async_set_nfc(self, container_id: str, nfc_uid: str) -> None:
        await self._hass.async_add_executor_job(self._locked, 
            self._set_nfc_sync, container_id, nfc_uid
        )

    def _set_nfc_sync(self, container_id: str, nfc_uid: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE production_containers SET nfc_uid = ? WHERE stable_id = ?",
            (nfc_uid, container_id),
        )
        self._conn.commit()

    async def async_insert_sale_pack(self, pack: SalePack) -> SalePack:
        return await self._hass.async_add_executor_job(
            self._locked, self._insert_sale_pack_sync, pack
        )

    def _insert_sale_pack_sync(self, pack: SalePack) -> SalePack:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO sale_packs (
              stable_id, harvest_id, mass_g, size_label, zone_id, status,
              sold_sale_id, created_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pack.id,
                pack.harvest_id,
                pack.mass_g,
                pack.size_label,
                pack.zone_id,
                pack.status,
                pack.sold_sale_id,
                pack.created_at,
                pack.notes,
            ),
        )
        self._conn.commit()
        return pack

    async def async_get_sale_pack(self, pack_id: str) -> SalePack | None:
        return await self._hass.async_add_executor_job(self._locked, 
            self._get_sale_pack_sync, pack_id
        )

    def _get_sale_pack_sync(self, pack_id: str) -> SalePack | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM sale_packs WHERE stable_id = ?",
            (pack_id,),
        ).fetchone()
        return self._row_to_sale_pack(row) if row else None

    async def async_list_open_sale_packs(self) -> list[SalePack]:
        return await self._hass.async_add_executor_job(self._locked, 
            self._list_open_sale_packs_sync
        )

    def _list_open_sale_packs_sync(self) -> list[SalePack]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM sale_packs
            WHERE status = 'open'
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
        return [self._row_to_sale_pack(row) for row in rows]

    async def async_mark_sale_pack_sold(
        self, pack_id: str, sale_id: str
    ) -> None:
        await self._hass.async_add_executor_job(self._locked, 
            self._mark_sale_pack_sold_sync, pack_id, sale_id
        )

    def _mark_sale_pack_sold_sync(self, pack_id: str, sale_id: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE sale_packs
            SET status = 'sold', sold_sale_id = ?
            WHERE stable_id = ?
            """,
            (sale_id, pack_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_sale_pack(row: Any) -> SalePack:
        keys = row.keys()
        return SalePack(
            id=row["stable_id"],
            harvest_id=row["harvest_id"],
            mass_g=float(row["mass_g"]),
            size_label=row["size_label"],
            zone_id=row["zone_id"],
            status=row["status"] or "open",
            sold_sale_id=row["sold_sale_id"] if "sold_sale_id" in keys else None,
            created_at=row["created_at"],
            notes=row["notes"],
        )

    @staticmethod
    def _row_to_container(row: Any) -> ProductionContainer:
        return ProductionContainer(
            id=row["stable_id"],
            batch_id=row["batch_id"],
            container_index=int(row["container_index"]),
            container_type=row["container_type"],
            nfc_uid=row["nfc_uid"],
            lifecycle_phase=row["lifecycle_phase"] or STAGE_INOCULATED,
            flush_count=int(row["flush_count"] or 0),
            max_flushes=int(row["max_flushes"] or DEFAULT_MAX_FLUSHES),
            zone_id=row["zone_id"],
            status=row["status"] or CONTAINER_STATUS_ACTIVE,
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            notes=row["notes"],
        )
