"""SQLite repository for Communifarm batches and mix milestones."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.batch_milestones import (
    BATCH_STATUS_ACTIVE,
    BATCH_STATUS_COMPLETE,
    DEFAULT_RECIPE_KEY,
    PHASE_PLANNED,
)
from ..domain.models import new_id
from ..domain.production import DEFAULT_MAX_FLUSHES, HarvestEvent, InoculateSpec
from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BatchRecord:
    """Master batch row — hub FK for weigh-ins, milestones, future production/sales."""

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
    recipe_scale: float = 1.0
    lifecycle_phase: str = PHASE_PLANNED
    recipe_key: str = DEFAULT_RECIPE_KEY
    culture_id: str | None = None
    container_type: str | None = None
    substrate_g_per_container: float | None = None
    inoculum_amount: float | None = None
    inoculum_unit: str | None = None
    expected_check_at: str | None = None
    flush_count: int = 0
    max_flushes: int = DEFAULT_MAX_FLUSHES
    inoculated_at: str | None = None
    zone_id: str | None = None

    def to_attr_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nfc_uid": self.nfc_uid,
            "status": self.status,
            "lifecycle_phase": self.lifecycle_phase,
            "recipe_scale": self.recipe_scale,
            "recipe_key": self.recipe_key,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "mixing_started_at": self.mixing_started_at,
            "mixing_finished_at": self.mixing_finished_at,
            "container_count": self.container_count,
            "notes": self.notes,
            "culture_id": self.culture_id,
            "container_type": self.container_type,
            "substrate_g_per_container": self.substrate_g_per_container,
            "inoculum_amount": self.inoculum_amount,
            "inoculum_unit": self.inoculum_unit,
            "expected_check_at": self.expected_check_at,
            "flush_count": self.flush_count,
            "max_flushes": self.max_flushes,
            "inoculated_at": self.inoculated_at,
            "zone_id": self.zone_id,
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
        recipe_scale: float = 1.0,
        recipe_key: str = DEFAULT_RECIPE_KEY,
        lifecycle_phase: str = PHASE_PLANNED,
    ) -> BatchRecord:
        return await self._hass.async_add_executor_job(
            self._ensure_batch_sync,
            batch_id,
            site_id,
            environment_id,
            name,
            nfc_uid,
            created_at,
            recipe_scale,
            recipe_key,
            lifecycle_phase,
        )

    def _ensure_batch_sync(
        self,
        batch_id: str,
        site_id: str,
        environment_id: str,
        name: str,
        nfc_uid: str,
        created_at: str | None,
        recipe_scale: float,
        recipe_key: str,
        lifecycle_phase: str,
    ) -> BatchRecord:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM batches WHERE stable_id = ?", (batch_id,)
        ).fetchone()
        if row:
            # Keep scale in sync when the operator changes the dashboard control.
            self._conn.execute(
                """
                UPDATE batches
                SET recipe_scale = ?, name = ?, nfc_uid = ?
                WHERE stable_id = ? AND status = ?
                """,
                (float(recipe_scale), name, nfc_uid, batch_id, BATCH_STATUS_ACTIVE),
            )
            self._conn.commit()
            refreshed = self._conn.execute(
                "SELECT * FROM batches WHERE stable_id = ?", (batch_id,)
            ).fetchone()
            return self._row_to_batch(refreshed)
        when = created_at or datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO batches (
              stable_id, site_id, environment_id, name, nfc_uid, status, created_at,
              recipe_scale, lifecycle_phase, recipe_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                site_id,
                environment_id,
                name,
                nfc_uid,
                BATCH_STATUS_ACTIVE,
                when,
                float(recipe_scale),
                lifecycle_phase,
                recipe_key,
            ),
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
            recipe_scale=float(recipe_scale),
            lifecycle_phase=lifecycle_phase,
            recipe_key=recipe_key,
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
            SET status = ?, completed_at = ?, lifecycle_phase = ?
            WHERE stable_id = ?
            """,
            (BATCH_STATUS_COMPLETE, completed_at, "complete", batch_id),
        )
        self._conn.commit()

    async def async_set_lifecycle_phase(self, batch_id: str, phase: str) -> None:
        await self._hass.async_add_executor_job(
            self._set_lifecycle_phase_sync, batch_id, phase
        )

    def _set_lifecycle_phase_sync(self, batch_id: str, phase: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE batches SET lifecycle_phase = ? WHERE stable_id = ?",
            (phase, batch_id),
        )
        self._conn.commit()

    async def async_set_recipe_scale(self, batch_id: str, recipe_scale: float) -> None:
        await self._hass.async_add_executor_job(
            self._set_recipe_scale_sync, batch_id, recipe_scale
        )

    def _set_recipe_scale_sync(self, batch_id: str, recipe_scale: float) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE batches SET recipe_scale = ? WHERE stable_id = ?",
            (float(recipe_scale), batch_id),
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

    async def async_set_zone(self, batch_id: str, zone_id: str | None) -> None:
        await self._hass.async_add_executor_job(
            self._set_zone_sync, batch_id, zone_id
        )

    def _set_zone_sync(self, batch_id: str, zone_id: str | None) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE batches SET zone_id = ? WHERE stable_id = ?",
            (zone_id, batch_id),
        )
        self._conn.commit()

    async def async_apply_inoculate(
        self,
        *,
        batch_id: str,
        spec: InoculateSpec,
        inoculated_at: str,
        lifecycle_phase: str,
        zone_id: str | None = None,
    ) -> BatchRecord:
        return await self._hass.async_add_executor_job(
            self._apply_inoculate_sync,
            batch_id,
            spec,
            inoculated_at,
            lifecycle_phase,
            zone_id,
        )

    def _apply_inoculate_sync(
        self,
        batch_id: str,
        spec: InoculateSpec,
        inoculated_at: str,
        lifecycle_phase: str,
        zone_id: str | None,
    ) -> BatchRecord:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE batches
            SET culture_id = ?,
                container_type = ?,
                container_count = ?,
                substrate_g_per_container = ?,
                inoculum_amount = ?,
                inoculum_unit = ?,
                expected_check_at = COALESCE(?, expected_check_at),
                flush_count = 0,
                max_flushes = ?,
                inoculated_at = ?,
                lifecycle_phase = ?,
                notes = COALESCE(?, notes),
                zone_id = COALESCE(?, zone_id)
            WHERE stable_id = ?
            """,
            (
                spec.culture_id,
                spec.container_type,
                spec.container_count,
                spec.substrate_g_per_container,
                spec.inoculum_amount,
                spec.inoculum_unit,
                spec.expected_check_at,
                spec.max_flushes,
                inoculated_at,
                lifecycle_phase,
                spec.notes,
                zone_id,
                batch_id,
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM batches WHERE stable_id = ?", (batch_id,)
        ).fetchone()
        assert row is not None
        return self._row_to_batch(row)

    async def async_insert_harvest(self, event: HarvestEvent) -> HarvestEvent:
        return await self._hass.async_add_executor_job(
            self._insert_harvest_sync, event
        )

    def _insert_harvest_sync(self, event: HarvestEvent) -> HarvestEvent:
        assert self._conn is not None
        created = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO harvest_events (
              stable_id, batch_id, flush_number, mass_g, is_final, notes,
              recorded_at, created_at, zone_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.batch_id,
                event.flush_number,
                event.mass_g,
                1 if event.is_final else 0,
                event.notes,
                event.recorded_at,
                created,
                event.zone_id,
            ),
        )
        self._conn.execute(
            """
            UPDATE batches
            SET flush_count = ?
            WHERE stable_id = ?
            """,
            (event.flush_number, event.batch_id),
        )
        self._conn.commit()
        return event

    async def async_list_harvests(self, batch_id: str) -> list[HarvestEvent]:
        return await self._hass.async_add_executor_job(
            self._list_harvests_sync, batch_id
        )

    def _list_harvests_sync(self, batch_id: str) -> list[HarvestEvent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT stable_id, batch_id, flush_number, mass_g, is_final, notes,
                   recorded_at, zone_id
            FROM harvest_events
            WHERE batch_id = ?
            ORDER BY flush_number ASC, recorded_at ASC, id ASC
            """,
            (batch_id,),
        ).fetchall()
        return [
            HarvestEvent(
                id=row["stable_id"],
                batch_id=row["batch_id"],
                flush_number=int(row["flush_number"]),
                mass_g=float(row["mass_g"]),
                is_final=bool(row["is_final"]),
                notes=row["notes"],
                recorded_at=row["recorded_at"],
                zone_id=row["zone_id"] if "zone_id" in row.keys() else None,
            )
            for row in rows
        ]

    async def async_set_expected_check_at(
        self, batch_id: str, expected_check_at: str | None
    ) -> None:
        await self._hass.async_add_executor_job(
            self._set_expected_check_at_sync, batch_id, expected_check_at
        )

    def _set_expected_check_at_sync(
        self, batch_id: str, expected_check_at: str | None
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE batches SET expected_check_at = ? WHERE stable_id = ?",
            (expected_check_at, batch_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_batch(row: Any) -> BatchRecord:
        keys = row.keys() if hasattr(row, "keys") else []

        def _opt(col: str) -> Any:
            return row[col] if col in keys else None

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
            recipe_scale=float(row["recipe_scale"])
            if "recipe_scale" in keys and row["recipe_scale"] is not None
            else 1.0,
            lifecycle_phase=(
                row["lifecycle_phase"]
                if "lifecycle_phase" in keys and row["lifecycle_phase"]
                else PHASE_PLANNED
            ),
            recipe_key=(
                row["recipe_key"]
                if "recipe_key" in keys and row["recipe_key"]
                else DEFAULT_RECIPE_KEY
            ),
            culture_id=_opt("culture_id"),
            container_type=_opt("container_type"),
            substrate_g_per_container=(
                float(row["substrate_g_per_container"])
                if "substrate_g_per_container" in keys
                and row["substrate_g_per_container"] is not None
                else None
            ),
            inoculum_amount=(
                float(row["inoculum_amount"])
                if "inoculum_amount" in keys and row["inoculum_amount"] is not None
                else None
            ),
            inoculum_unit=_opt("inoculum_unit"),
            expected_check_at=_opt("expected_check_at"),
            flush_count=int(row["flush_count"] or 0)
            if "flush_count" in keys
            else 0,
            max_flushes=int(row["max_flushes"] or DEFAULT_MAX_FLUSHES)
            if "max_flushes" in keys
            else DEFAULT_MAX_FLUSHES,
            inoculated_at=_opt("inoculated_at"),
            zone_id=_opt("zone_id"),
        )

    @staticmethod
    def format_batch_list_text(batches: list[BatchRecord]) -> str:
        if not batches:
            return "_No batches yet._"
        lines = [
            "| Status | Phase | Scale | Name | ID | Mix start | Mix finish | Containers |",
            "| --- | --- | ---: | --- | --- | --- | --- | ---: |",
        ]
        for batch in batches:
            lines.append(
                f"| {batch.status} | {batch.lifecycle_phase} | "
                f"×{batch.recipe_scale:g} | {batch.name} | `{batch.id}` | "
                f"{batch.mixing_started_at or '—'} | "
                f"{batch.mixing_finished_at or '—'} | "
                f"{batch.container_count if batch.container_count is not None else '—'} |"
            )
        return "\n".join(lines)
