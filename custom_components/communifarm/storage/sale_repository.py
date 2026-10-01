"""SQLite repository for sales, line items, and cleanup events."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.sale import Sale, SaleCleanupEvent, SaleLineItem
from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


class SaleRepository:
    """CRUD for POS sales tables (schema v10+)."""

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


    async def async_insert_sale(
        self,
        sale: Sale,
        lines: list[SaleLineItem],
    ) -> Sale:
        return await self._hass.async_add_executor_job(self._locked, 
            self._insert_sale_sync, sale, lines
        )

    def _insert_sale_sync(self, sale: Sale, lines: list[SaleLineItem]) -> Sale:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO sales (
              stable_id, venue_label, buyer_label, payment_method, currency,
              total_amount, sold_at, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sale.id,
                sale.venue_label,
                sale.buyer_label,
                sale.payment_method,
                sale.currency,
                sale.total_amount,
                sale.sold_at,
                sale.notes,
                sale.created_at,
            ),
        )
        for line in lines:
            self._conn.execute(
                """
                INSERT INTO sale_line_items (
                  stable_id, sale_id, sale_pack_id, batch_id, harvest_id,
                  product_label, mass_g, unit_price, line_amount, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    line.id,
                    line.sale_id,
                    line.sale_pack_id,
                    line.batch_id,
                    line.harvest_id,
                    line.product_label,
                    line.mass_g,
                    line.unit_price,
                    line.line_amount,
                    line.created_at,
                ),
            )
        self._conn.commit()
        return sale

    async def async_list_sales(self, *, limit: int = 20) -> list[Sale]:
        return await self._hass.async_add_executor_job(self._locked, self._list_sales_sync, limit)

    def _list_sales_sync(self, limit: int) -> list[Sale]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM sales
            ORDER BY sold_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_sale(row) for row in rows]

    async def async_get_sale(self, sale_id: str) -> Sale | None:
        return await self._hass.async_add_executor_job(self._locked, self._get_sale_sync, sale_id)

    def _get_sale_sync(self, sale_id: str) -> Sale | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM sales WHERE stable_id = ?",
            (sale_id,),
        ).fetchone()
        return self._row_to_sale(row) if row else None

    async def async_list_lines_for_sale(self, sale_id: str) -> list[SaleLineItem]:
        return await self._hass.async_add_executor_job(self._locked, 
            self._list_lines_for_sale_sync, sale_id
        )

    def _list_lines_for_sale_sync(self, sale_id: str) -> list[SaleLineItem]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM sale_line_items
            WHERE sale_id = ?
            ORDER BY id ASC
            """,
            (sale_id,),
        ).fetchall()
        return [self._row_to_line(row) for row in rows]

    async def async_insert_cleanup(
        self, event: SaleCleanupEvent
    ) -> SaleCleanupEvent:
        return await self._hass.async_add_executor_job(self._locked, 
            self._insert_cleanup_sync, event
        )

    def _insert_cleanup_sync(self, event: SaleCleanupEvent) -> SaleCleanupEvent:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO sale_cleanup_events (
              stable_id, sale_id, sale_day, checklist_json, notes,
              recorded_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.sale_id,
                event.sale_day,
                event.checklist_json,
                event.notes,
                event.recorded_at,
                event.created_at,
            ),
        )
        self._conn.commit()
        return event

    async def async_list_cleanups(self, *, limit: int = 10) -> list[SaleCleanupEvent]:
        return await self._hass.async_add_executor_job(self._locked, 
            self._list_cleanups_sync, limit
        )

    def _list_cleanups_sync(self, limit: int) -> list[SaleCleanupEvent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM sale_cleanup_events
            ORDER BY recorded_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_cleanup(row) for row in rows]

    @staticmethod
    def _row_to_sale(row: Any) -> Sale:
        return Sale(
            id=row["stable_id"],
            venue_label=row["venue_label"],
            buyer_label=row["buyer_label"],
            payment_method=row["payment_method"],
            currency=row["currency"] or "USD",
            total_amount=float(row["total_amount"]),
            sold_at=row["sold_at"],
            notes=row["notes"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_line(row: Any) -> SaleLineItem:
        return SaleLineItem(
            id=row["stable_id"],
            sale_id=row["sale_id"],
            sale_pack_id=row["sale_pack_id"],
            batch_id=row["batch_id"],
            harvest_id=row["harvest_id"],
            product_label=row["product_label"],
            mass_g=float(row["mass_g"]),
            unit_price=(
                float(row["unit_price"]) if row["unit_price"] is not None else None
            ),
            line_amount=float(row["line_amount"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_cleanup(row: Any) -> SaleCleanupEvent:
        return SaleCleanupEvent(
            id=row["stable_id"],
            sale_id=row["sale_id"],
            sale_day=row["sale_day"],
            checklist_json=row["checklist_json"] or "{}",
            notes=row["notes"],
            recorded_at=row["recorded_at"],
            created_at=row["created_at"],
        )
