"""SQLite repository for Communifarm batches and mix milestones."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.batch_milestones import BATCH_STATUS_ACTIVE, BATCH_STATUS_COMPLETE
from ..domain.models import new_id
from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BatchRecord:
    id: str
    site_id: str
    environment_id: str
    name: str
    nfc_uid: str
    status: str
    created_at: str
    completed_at: str | None = None
    mixing_started_at: str | None = None
    mixing_finished_at: str | None = None
    container_count: int | None = None
    notes: str | None = None

    def to_attr_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nfc_uid": self.nfc_uid,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "mixing_started_at": self.mixing_started_at,
            "mixing_finished_at": self.mixing_finished_at,
            "container_count": self.container_count,
            "notes": self.notes,
        }


@dataclass(slots=True)
class BatchMilestone:
    id: str
    batch_id: str
    event_type: str
    recorded_at: str
    detail: dict[str, Any] | None = None

    def to_attr_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "event_type": self.event_type,
            "detail": self.detail or {},
            "recorded_at": self.recorded_at,
        }


class BatchRepository:
    """Active + historical batches and append-only milestones."""

    def __init__(self, hass: HomeAssistant, path: Path | None = None) -> None:
        self._hass = hass
        self._path = path or sqlite_db.db_path_for_config_dir(hass.config.config_dir)
        self._conn = None

    async def async_setup(self) -> None:
        await self._hass.async_add_executor_job(self._setup_sync)

    def _setup_sync(self) -> None:
        self._conn = sqlite_db.connect(self._path)
        version = sqlite_db.apply_migrations(self._conn)
        _LOGGER.info("Communifarm batch SQLite ready at %s (schema v%s)", self._path, version)

    async def async_close(self) -> None:
        await self._hass.async_add_executor_job(self._close_sync)

    def _close_sync(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def async_ensure_batch(
        self,
        *,
        batch_id: str,
        site_id: str,
        environment_id: str,
        name: str,
        nfc_uid: str,
        created_at: str | None = None,
    ) -> BatchRecord:
        return await self._hass.async_add_executor_job(
            self._ensure_batch_sync,
            batch_id,
            site_id,
            environment_id,
            name,
            nfc_uid,
            created_at,
        )

    def _ensure_batch_sync(
        self,
        batch_id: str,
        site_id: str,
        environment_id: str,
        name: str,
        nfc_uid: str,
        created_at: str | None,
    ) -> BatchRecord:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM batches WHERE stable_id = ?", (batch_id,)
        ).fetchone()
        if row:
            return self._row_to_batch(row)
        when = created_at or datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO batches (
              stable_id, site_id, environment_id, name, nfc_uid, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (batch_id, site_id, environment_id, name, nfc_uid, BATCH_STATUS_ACTIVE, when),
        )
        self._conn.commit()
        return BatchRecord(
            id=batch_id,
            site_id=site_id,
            environment_id=environment_id,
            name=name,
            nfc_uid=nfc_uid,
            status=BATCH_STATUS_ACTIVE,
            created_at=when,
        )

    async def async_list_batches(self) -> list[BatchRecord]:
        return await self._hass.async_add_executor_job(self._list_batches_sync)

    def _list_batches_sync(self) -> list[BatchRecord]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM batches ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [self._row_to_batch(row) for row in rows]

    async def async_get_batch(self, batch_id: str) -> BatchRecord | None:
        return await self._hass.async_add_executor_job(self._get_batch_sync, batch_id)

    def _get_batch_sync(self, batch_id: str) -> BatchRecord | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM batches WHERE stable_id = ?", (batch_id,)
        ).fetchone()
        return self._row_to_batch(row) if row else None

    async def async_complete_batch(self, batch_id: str, completed_at: str) -> None:
        await self._hass.async_add_executor_job(
            self._complete_batch_sync, batch_id, completed_at
        )

    def _complete_batch_sync(self, batch_id: str, completed_at: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE batches
            SET status = ?, completed_at = ?
            WHERE stable_id = ?
            """,
            (BATCH_STATUS_COMPLETE, completed_at, batch_id),
        )
        self._conn.commit()

    async def async_mark_mixing_started(self, batch_id: str, when: str) -> None:
        await self._hass.async_add_executor_job(
            self._mark_mixing_started_sync, batch_id, when
        )

    def _mark_mixing_started_sync(self, batch_id: str, when: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE batches
            SET mixing_started_at = COALESCE(mixing_started_at, ?)
            WHERE stable_id = ?
            """,
            (when, batch_id),
        )
        self._conn.commit()

    async def async_mark_mixing_finished(self, batch_id: str, when: str) -> None:
        await self._hass.async_add_executor_job(
            self._mark_mixing_finished_sync, batch_id, when
        )

    def _mark_mixing_finished_sync(self, batch_id: str, when: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE batches
            SET mixing_finished_at = COALESCE(mixing_finished_at, ?)
            WHERE stable_id = ?
            """,
            (when, batch_id),
        )
        self._conn.commit()

    async def async_set_containers(
        self, batch_id: str, count: int, notes: str | None
    ) -> None:
        await self._hass.async_add_executor_job(
            self._set_containers_sync, batch_id, count, notes
        )

    def _set_containers_sync(self, batch_id: str, count: int, notes: str | None) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE batches
            SET container_count = ?, notes = COALESCE(?, notes)
            WHERE stable_id = ?
            """,
            (count, notes, batch_id),
        )
        self._conn.commit()

    async def async_has_milestone(self, batch_id: str, event_type: str) -> bool:
        return await self._hass.async_add_executor_job(
            self._has_milestone_sync, batch_id, event_type
        )

    def _has_milestone_sync(self, batch_id: str, event_type: str) -> bool:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT 1 FROM batch_milestones
            WHERE batch_id = ? AND event_type = ?
            LIMIT 1
            """,
            (batch_id, event_type),
        ).fetchone()
        return row is not None

    async def async_insert_milestone(
        self,
        *,
        batch_id: str,
        event_type: str,
        recorded_at: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> BatchMilestone:
        return await self._hass.async_add_executor_job(
            self._insert_milestone_sync,
            batch_id,
            event_type,
            recorded_at,
            detail,
        )

    def _insert_milestone_sync(
        self,
        batch_id: str,
        event_type: str,
        recorded_at: str | None,
        detail: dict[str, Any] | None,
    ) -> BatchMilestone:
        assert self._conn is not None
        when = recorded_at or datetime.now(tz=UTC).isoformat()
        created = datetime.now(tz=UTC).isoformat()
        stable = new_id("bms")
        self._conn.execute(
            """
            INSERT INTO batch_milestones (
              stable_id, batch_id, event_type, detail, recorded_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stable,
                batch_id,
                event_type,
                json.dumps(detail) if detail else None,
                when,
                created,
            ),
        )
        self._conn.commit()
        return BatchMilestone(
            id=stable,
            batch_id=batch_id,
            event_type=event_type,
            recorded_at=when,
            detail=detail,
        )

    async def async_list_milestones(self, batch_id: str) -> list[BatchMilestone]:
        return await self._hass.async_add_executor_job(
            self._list_milestones_sync, batch_id
        )

    def _list_milestones_sync(self, batch_id: str) -> list[BatchMilestone]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT stable_id, batch_id, event_type, detail, recorded_at
            FROM batch_milestones
            WHERE batch_id = ?
            ORDER BY recorded_at ASC, id ASC
            """,
            (batch_id,),
        ).fetchall()
        out: list[BatchMilestone] = []
        for row in rows:
            detail = None
            if row["detail"]:
                try:
                    detail = json.loads(row["detail"])
                except json.JSONDecodeError:
                    detail = {"raw": row["detail"]}
            out.append(
                BatchMilestone(
                    id=row["stable_id"],
                    batch_id=row["batch_id"],
                    event_type=row["event_type"],
                    recorded_at=row["recorded_at"],
                    detail=detail,
                )
            )
        return out

    @staticmethod
    def _row_to_batch(row: Any) -> BatchRecord:
        return BatchRecord(
            id=row["stable_id"],
            site_id=row["site_id"],
            environment_id=row["environment_id"],
            name=row["name"],
            nfc_uid=row["nfc_uid"],
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            mixing_started_at=row["mixing_started_at"],
            mixing_finished_at=row["mixing_finished_at"],
            container_count=row["container_count"],
            notes=row["notes"],
        )

    @staticmethod
    def format_batch_list_text(batches: list[BatchRecord]) -> str:
        if not batches:
            return "_No batches yet._"
        lines = [
            "| Status | Name | ID | Mix start | Mix finish | Containers |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
        for batch in batches:
            lines.append(
                f"| {batch.status} | {batch.name} | `{batch.id}` | "
                f"{batch.mixing_started_at or '—'} | "
                f"{batch.mixing_finished_at or '—'} | "
                f"{batch.container_count if batch.container_count is not None else '—'} |"
            )
        return "\n".join(lines)
