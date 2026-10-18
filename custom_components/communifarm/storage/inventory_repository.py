"""SQLite repository for inventory lots and employee badges."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.inventory import STATUS_ACTIVE, EmployeeBadge, InventoryLot
from .sqlite_repository import SqliteRepository


class InventoryRepository(SqliteRepository):
    """Inventory lots + employee badges; shares the Communifarm DB connection."""

    _eager_path = False

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)

    def bind_connection(self, conn: Any) -> None:
        self._conn = conn

    async def async_insert_lot(self, lot: InventoryLot) -> InventoryLot:
        return await self._hass.async_add_executor_job(
            self._locked, self._insert_lot_sync, lot
        )

    def _insert_lot_sync(self, lot: InventoryLot) -> InventoryLot:
        assert self._conn is not None
        created = lot.created_at or datetime.now(tz=UTC).isoformat()
        lot.created_at = created
        self._conn.execute(
            """
            INSERT INTO inventory_lots (
              stable_id, site_id, ingredient_key, label, water_kind,
              nfc_uid, ndef_payload, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lot.id,
                lot.site_id,
                lot.ingredient_key,
                lot.label,
                lot.water_kind,
                lot.nfc_uid,
                lot.ndef_payload,
                lot.status,
                lot.notes,
                created,
            ),
        )
        self._conn.commit()
        return lot

    async def async_update_lot(self, lot: InventoryLot) -> InventoryLot:
        return await self._hass.async_add_executor_job(
            self._locked, self._update_lot_sync, lot
        )

    def _update_lot_sync(self, lot: InventoryLot) -> InventoryLot:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE inventory_lots SET
              label = ?, water_kind = ?, nfc_uid = ?, ndef_payload = ?,
              status = ?, notes = ?
            WHERE stable_id = ?
            """,
            (
                lot.label,
                lot.water_kind,
                lot.nfc_uid,
                lot.ndef_payload,
                lot.status,
                lot.notes,
                lot.id,
            ),
        )
        self._conn.commit()
        return lot

    async def async_get_lot(self, lot_id: str) -> InventoryLot | None:
        return await self._hass.async_add_executor_job(
            self._locked, self._get_lot_sync, lot_id
        )

    def _get_lot_sync(self, lot_id: str) -> InventoryLot | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM inventory_lots WHERE stable_id = ? LIMIT 1", (lot_id,)
        ).fetchone()
        return self._row_to_lot(row) if row else None

    async def async_get_lot_by_nfc(self, nfc_uid: str) -> InventoryLot | None:
        return await self._hass.async_add_executor_job(
            self._locked, self._get_lot_by_nfc_sync, nfc_uid
        )

    def _get_lot_by_nfc_sync(self, nfc_uid: str) -> InventoryLot | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM inventory_lots WHERE nfc_uid = ? LIMIT 1", (nfc_uid,)
        ).fetchone()
        return self._row_to_lot(row) if row else None

    async def async_list_lots(
        self, site_id: str, *, ingredient_key: str | None = None
    ) -> list[InventoryLot]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_lots_sync, site_id, ingredient_key
        )

    def _list_lots_sync(
        self, site_id: str, ingredient_key: str | None
    ) -> list[InventoryLot]:
        assert self._conn is not None
        if ingredient_key:
            rows = self._conn.execute(
                """
                SELECT * FROM inventory_lots
                WHERE site_id = ? AND ingredient_key = ? AND status = ?
                ORDER BY created_at DESC, id DESC
                """,
                (site_id, ingredient_key, STATUS_ACTIVE),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM inventory_lots
                WHERE site_id = ? AND status = ?
                ORDER BY label COLLATE NOCASE ASC, created_at DESC
                """,
                (site_id, STATUS_ACTIVE),
            ).fetchall()
        return [self._row_to_lot(row) for row in rows]

    async def async_insert_employee(self, badge: EmployeeBadge) -> EmployeeBadge:
        return await self._hass.async_add_executor_job(
            self._locked, self._insert_employee_sync, badge
        )

    def _insert_employee_sync(self, badge: EmployeeBadge) -> EmployeeBadge:
        assert self._conn is not None
        created = badge.created_at or datetime.now(tz=UTC).isoformat()
        badge.created_at = created
        self._conn.execute(
            """
            INSERT INTO employees (
              stable_id, site_id, label, nfc_uid, ndef_payload, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                badge.id,
                badge.site_id,
                badge.label,
                badge.nfc_uid,
                badge.ndef_payload,
                badge.status,
                created,
            ),
        )
        self._conn.commit()
        return badge

    async def async_update_employee(self, badge: EmployeeBadge) -> EmployeeBadge:
        return await self._hass.async_add_executor_job(
            self._locked, self._update_employee_sync, badge
        )

    def _update_employee_sync(self, badge: EmployeeBadge) -> EmployeeBadge:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE employees SET
              label = ?, nfc_uid = ?, ndef_payload = ?, status = ?
            WHERE stable_id = ?
            """,
            (badge.label, badge.nfc_uid, badge.ndef_payload, badge.status, badge.id),
        )
        self._conn.commit()
        return badge

    async def async_get_employee(self, employee_id: str) -> EmployeeBadge | None:
        return await self._hass.async_add_executor_job(
            self._locked, self._get_employee_sync, employee_id
        )

    def _get_employee_sync(self, employee_id: str) -> EmployeeBadge | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM employees WHERE stable_id = ? LIMIT 1", (employee_id,)
        ).fetchone()
        return self._row_to_employee(row) if row else None

    async def async_get_employee_by_nfc(self, nfc_uid: str) -> EmployeeBadge | None:
        return await self._hass.async_add_executor_job(
            self._locked, self._get_employee_by_nfc_sync, nfc_uid
        )

    def _get_employee_by_nfc_sync(self, nfc_uid: str) -> EmployeeBadge | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM employees WHERE nfc_uid = ? LIMIT 1", (nfc_uid,)
        ).fetchone()
        return self._row_to_employee(row) if row else None

    async def async_list_employees(self, site_id: str) -> list[EmployeeBadge]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_employees_sync, site_id
        )

    def _list_employees_sync(self, site_id: str) -> list[EmployeeBadge]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM employees
            WHERE site_id = ? AND status = ?
            ORDER BY label COLLATE NOCASE ASC
            """,
            (site_id, STATUS_ACTIVE),
        ).fetchall()
        return [self._row_to_employee(row) for row in rows]

    @staticmethod
    def _row_to_lot(row: Any) -> InventoryLot:
        return InventoryLot(
            id=row["stable_id"],
            site_id=row["site_id"],
            ingredient_key=row["ingredient_key"],
            label=row["label"],
            water_kind=row["water_kind"],
            nfc_uid=row["nfc_uid"],
            ndef_payload=row["ndef_payload"],
            status=row["status"],
            notes=row["notes"],
            created_at=row["created_at"] or "",
        )

    @staticmethod
    def _row_to_employee(row: Any) -> EmployeeBadge:
        return EmployeeBadge(
            id=row["stable_id"],
            site_id=row["site_id"],
            label=row["label"],
            nfc_uid=row["nfc_uid"],
            ndef_payload=row["ndef_payload"],
            status=row["status"],
            created_at=row["created_at"] or "",
        )
