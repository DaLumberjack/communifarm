"""SQLite repository for shipment / imported NFC tag pool (bind registry)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.models import new_id
from ..domain.nfc_bind import PoolBindTarget
from ..domain.shipment_tags import STATUS_AVAILABLE, STATUS_BOUND
from .sqlite_repository import SqliteRepository


@dataclass(slots=True)
class NfcTagPoolEntry:
    site_id: str
    nfc_uid: str
    intended_type: str
    label: str
    ingredient_key: str | None = None
    status: str = STATUS_AVAILABLE
    shipment_id: str | None = None
    bound_object_id: str | None = None
    bound_object_type: str | None = None
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("ntag")


class NfcTagPoolRepository(SqliteRepository):
    """Physical-tag registry. Domain rows keep ``nfc_uid``; this tracks bind state."""

    _eager_path = False

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)

    def bind_connection(self, conn: Any) -> None:
        self._conn = conn

    async def async_upsert(self, entry: NfcTagPoolEntry) -> NfcTagPoolEntry:
        return await self._hass.async_add_executor_job(
            self._locked, self._upsert_sync, entry
        )

    def _upsert_sync(self, entry: NfcTagPoolEntry) -> NfcTagPoolEntry:
        assert self._conn is not None
        created = entry.created_at or datetime.now(tz=UTC).isoformat()
        entry.created_at = created
        existing = self._conn.execute(
            """
            SELECT stable_id FROM nfc_tag_pool
            WHERE site_id = ? AND nfc_uid = ? LIMIT 1
            """,
            (entry.site_id, entry.nfc_uid),
        ).fetchone()
        if existing:
            entry.id = existing["stable_id"]
            self._conn.execute(
                """
                UPDATE nfc_tag_pool SET
                  intended_type = ?, label = ?, ingredient_key = ?,
                  status = ?, shipment_id = COALESCE(?, shipment_id),
                  bound_object_id = ?, bound_object_type = ?
                WHERE stable_id = ?
                """,
                (
                    entry.intended_type,
                    entry.label,
                    entry.ingredient_key,
                    entry.status,
                    entry.shipment_id,
                    entry.bound_object_id,
                    entry.bound_object_type,
                    entry.id,
                ),
            )
        else:
            self._conn.execute(
                """
                INSERT INTO nfc_tag_pool (
                  stable_id, site_id, nfc_uid, intended_type, label,
                  ingredient_key, status, shipment_id, bound_object_id,
                  bound_object_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.site_id,
                    entry.nfc_uid,
                    entry.intended_type,
                    entry.label,
                    entry.ingredient_key,
                    entry.status,
                    entry.shipment_id,
                    entry.bound_object_id,
                    entry.bound_object_type,
                    created,
                ),
            )
        self._conn.commit()
        return entry

    async def async_list(
        self,
        site_id: str,
        *,
        intended_type: str | None = None,
        status: str | None = None,
    ) -> list[NfcTagPoolEntry]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_sync, site_id, intended_type, status
        )

    def _list_sync(
        self,
        site_id: str,
        intended_type: str | None,
        status: str | None,
    ) -> list[NfcTagPoolEntry]:
        assert self._conn is not None
        sql = "SELECT * FROM nfc_tag_pool WHERE site_id = ?"
        params: list[Any] = [site_id]
        if intended_type:
            sql += " AND intended_type = ?"
            params.append(intended_type)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY intended_type ASC, label COLLATE NOCASE ASC"
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_entry(row) for row in rows]

    async def async_get_by_uid(
        self, site_id: str, nfc_uid: str
    ) -> NfcTagPoolEntry | None:
        return await self._hass.async_add_executor_job(
            self._locked, self._get_by_uid_sync, site_id, nfc_uid
        )

    def _get_by_uid_sync(self, site_id: str, nfc_uid: str) -> NfcTagPoolEntry | None:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT * FROM nfc_tag_pool
            WHERE site_id = ? AND nfc_uid = ? LIMIT 1
            """,
            (site_id, nfc_uid),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    async def async_mark_bound(
        self,
        site_id: str,
        nfc_uid: str,
        object_id: str,
        object_type: str | None = None,
    ) -> None:
        await self._hass.async_add_executor_job(
            self._locked,
            self._mark_bound_sync,
            site_id,
            nfc_uid,
            object_id,
            object_type,
        )

    def _mark_bound_sync(
        self,
        site_id: str,
        nfc_uid: str,
        object_id: str,
        object_type: str | None,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE nfc_tag_pool
            SET status = ?, bound_object_id = ?, bound_object_type = ?
            WHERE site_id = ? AND nfc_uid = ?
            """,
            (STATUS_BOUND, object_id, object_type, site_id, nfc_uid),
        )
        self._conn.commit()

    async def async_dual_write_bind(
        self, site_id: str, target: PoolBindTarget
    ) -> NfcTagPoolEntry:
        """Upsert pool registry row to match a successful entity ``nfc_uid`` bind."""
        return await self._hass.async_add_executor_job(
            self._locked, self._dual_write_bind_sync, site_id, target
        )

    def _dual_write_bind_sync(
        self, site_id: str, target: PoolBindTarget
    ) -> NfcTagPoolEntry:
        existing = self._get_by_uid_sync(site_id, target.nfc_uid)
        if existing is None:
            entry = NfcTagPoolEntry(
                site_id=site_id,
                nfc_uid=target.nfc_uid,
                intended_type=target.object_type,
                label=target.label or target.object_id,
                status=STATUS_BOUND,
                bound_object_id=target.object_id,
                bound_object_type=target.object_type,
            )
            return self._upsert_sync(entry)
        existing.status = STATUS_BOUND
        existing.bound_object_id = target.object_id
        existing.bound_object_type = target.object_type
        if target.label:
            existing.label = target.label
        return self._upsert_sync(existing)

    async def async_mark_available(self, site_id: str, nfc_uid: str) -> None:
        await self._hass.async_add_executor_job(
            self._locked, self._mark_available_sync, site_id, nfc_uid
        )

    def _mark_available_sync(self, site_id: str, nfc_uid: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE nfc_tag_pool
            SET status = ?, bound_object_id = NULL, bound_object_type = NULL
            WHERE site_id = ? AND nfc_uid = ?
            """,
            (STATUS_AVAILABLE, site_id, nfc_uid),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_entry(row: Any) -> NfcTagPoolEntry:
        keys = row.keys()
        return NfcTagPoolEntry(
            id=row["stable_id"],
            site_id=row["site_id"],
            nfc_uid=row["nfc_uid"],
            intended_type=row["intended_type"],
            label=row["label"],
            ingredient_key=row["ingredient_key"],
            status=row["status"],
            shipment_id=row["shipment_id"],
            bound_object_id=row["bound_object_id"],
            bound_object_type=(
                row["bound_object_type"] if "bound_object_type" in keys else None
            ),
            created_at=row["created_at"] or "",
        )
