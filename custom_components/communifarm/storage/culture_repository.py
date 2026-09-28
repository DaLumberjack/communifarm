"""SQLite repository for culture lots and media prep batches."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.culture import (
    EVENT_CULTURE_ACQUIRED,
    EVENT_CULTURE_INTRODUCED,
    EVENT_MEDIA_BATCH_CREATED,
    MEDIA_STATUS_IN_USE,
    MEDIA_STATUS_PLANNED,
    MEDIA_STATUS_READY,
    MILESTONE_MEDIA_READY,
    MILESTONE_MEDIA_STERILIZED,
    MILESTONE_TO_MEDIA_STATUS,
    MILESTONE_WEIGHING_STARTED,
    CultureEvent,
    CultureLot,
    MediaBatch,
    MediaWeightEvent,
    assert_media_accepts_culture,
    child_culture_from_parent,
)
from ..domain.models import new_id
from . import sqlite_db

_LOGGER = logging.getLogger(__name__)


class CultureRepository:
    """Culture inventory + media prep hubs and append-only events."""

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
        _LOGGER.info("Communifarm culture SQLite ready at %s (schema v%s)", self._path, version)

    async def async_close(self) -> None:
        await self._hass.async_add_executor_job(self._close_sync)

    def _close_sync(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- Culture lots ---

    async def async_insert_culture(self, lot: CultureLot) -> CultureLot:
        return await self._hass.async_add_executor_job(self._insert_culture_sync, lot)

    def _insert_culture_sync(self, lot: CultureLot) -> CultureLot:
        assert self._conn is not None
        created = datetime.now(tz=UTC).isoformat()
        acquired = lot.acquired_at or created
        self._conn.execute(
            """
            INSERT INTO culture_lots (
              stable_id, site_id, environment_id, name, source_type, form, container,
              strain_label, parent_culture_id, status, acquired_at, created_at,
              nfc_uid, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lot.id,
                lot.site_id,
                lot.environment_id,
                lot.name,
                lot.source_type,
                lot.form,
                lot.container,
                lot.strain_label,
                lot.parent_culture_id,
                lot.status,
                acquired,
                created,
                lot.nfc_uid,
                lot.notes,
            ),
        )
        self._conn.commit()
        lot.acquired_at = acquired
        return lot

    async def async_get_culture(self, culture_id: str) -> CultureLot | None:
        return await self._hass.async_add_executor_job(self._get_culture_sync, culture_id)

    def _get_culture_sync(self, culture_id: str) -> CultureLot | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM culture_lots WHERE stable_id = ?", (culture_id,)
        ).fetchone()
        return self._row_to_culture(row) if row else None

    async def async_list_cultures(self) -> list[CultureLot]:
        return await self._hass.async_add_executor_job(self._list_cultures_sync)

    def _list_cultures_sync(self) -> list[CultureLot]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM culture_lots ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [self._row_to_culture(row) for row in rows]

    # --- Media batches ---

    async def async_insert_media_batch(self, batch: MediaBatch) -> MediaBatch:
        return await self._hass.async_add_executor_job(self._insert_media_batch_sync, batch)

    def _insert_media_batch_sync(self, batch: MediaBatch) -> MediaBatch:
        assert self._conn is not None
        created = batch.created_at or datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO media_batches (
              stable_id, site_id, environment_id, name, recipe_key, media_form,
              vessel_type, recipe_scale, status, vessel_count, sterilized_at,
              ready_at, created_at, nfc_uid, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch.id,
                batch.site_id,
                batch.environment_id,
                batch.name,
                batch.recipe_key,
                batch.media_form,
                batch.vessel_type,
                float(batch.recipe_scale),
                batch.status or MEDIA_STATUS_PLANNED,
                batch.vessel_count,
                batch.sterilized_at,
                batch.ready_at,
                created,
                batch.nfc_uid,
                batch.notes,
            ),
        )
        self._conn.commit()
        batch.created_at = created
        return batch

    async def async_list_media_batches(self) -> list[MediaBatch]:
        return await self._hass.async_add_executor_job(self._list_media_batches_sync)

    def _list_media_batches_sync(self) -> list[MediaBatch]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM media_batches ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [self._row_to_media(row) for row in rows]

    async def async_get_media_batch(self, media_batch_id: str) -> MediaBatch | None:
        return await self._hass.async_add_executor_job(
            self._get_media_batch_sync, media_batch_id
        )

    def _get_media_batch_sync(self, media_batch_id: str) -> MediaBatch | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM media_batches WHERE stable_id = ?", (media_batch_id,)
        ).fetchone()
        return self._row_to_media(row) if row else None

    async def async_set_media_status(
        self,
        media_batch_id: str,
        status: str,
        *,
        sterilized_at: str | None = None,
        ready_at: str | None = None,
    ) -> None:
        await self._hass.async_add_executor_job(
            self._set_media_status_sync,
            media_batch_id,
            status,
            sterilized_at,
            ready_at,
        )

    def _set_media_status_sync(
        self,
        media_batch_id: str,
        status: str,
        sterilized_at: str | None,
        ready_at: str | None,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE media_batches
            SET status = ?,
                sterilized_at = COALESCE(?, sterilized_at),
                ready_at = COALESCE(?, ready_at)
            WHERE stable_id = ?
            """,
            (status, sterilized_at, ready_at, media_batch_id),
        )
        self._conn.commit()

    # --- Media weights ---

    async def async_insert_media_weight(self, event: MediaWeightEvent) -> MediaWeightEvent:
        return await self._hass.async_add_executor_job(self._insert_media_weight_sync, event)

    def _insert_media_weight_sync(self, event: MediaWeightEvent) -> MediaWeightEvent:
        assert self._conn is not None
        created = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO media_weight_events (
              stable_id, site_id, environment_id, media_batch_id,
              ingredient_key, ingredient_label, amount, unit,
              recipe_scale, target_amount, source_entity_id,
              recorded_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.site_id,
                event.environment_id,
                event.media_batch_id,
                event.ingredient_key,
                event.ingredient_label,
                float(event.amount),
                event.unit,
                event.recipe_scale,
                event.target_amount,
                event.source_entity_id,
                event.recorded_at,
                created,
            ),
        )
        self._conn.commit()
        return event

    async def async_list_media_weights(self, media_batch_id: str) -> list[MediaWeightEvent]:
        return await self._hass.async_add_executor_job(
            self._list_media_weights_sync, media_batch_id
        )

    def _list_media_weights_sync(self, media_batch_id: str) -> list[MediaWeightEvent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM media_weight_events
            WHERE media_batch_id = ?
            ORDER BY recorded_at ASC, id ASC
            """,
            (media_batch_id,),
        ).fetchall()
        return [self._row_to_media_weight(row) for row in rows]

    # --- Media milestones ---

    async def async_insert_media_milestone(
        self,
        *,
        media_batch_id: str,
        event_type: str,
        recorded_at: str,
        detail: dict[str, Any] | None = None,
    ) -> str:
        return await self._hass.async_add_executor_job(
            self._insert_media_milestone_sync,
            media_batch_id,
            event_type,
            recorded_at,
            detail,
        )

    def _insert_media_milestone_sync(
        self,
        media_batch_id: str,
        event_type: str,
        recorded_at: str,
        detail: dict[str, Any] | None,
    ) -> str:
        assert self._conn is not None
        stable_id = new_id("mmil")
        created = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO media_milestones (
              stable_id, media_batch_id, event_type, detail, recorded_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stable_id,
                media_batch_id,
                event_type,
                json.dumps(detail) if detail else None,
                recorded_at,
                created,
            ),
        )
        status = MILESTONE_TO_MEDIA_STATUS.get(event_type)
        if status:
            sterilized_at = recorded_at if event_type == MILESTONE_MEDIA_STERILIZED else None
            ready_at = recorded_at if event_type == MILESTONE_MEDIA_READY else None
            self._conn.execute(
                """
                UPDATE media_batches
                SET status = ?,
                    sterilized_at = COALESCE(?, sterilized_at),
                    ready_at = COALESCE(?, ready_at)
                WHERE stable_id = ?
                """,
                (status, sterilized_at, ready_at, media_batch_id),
            )
        self._conn.commit()
        return stable_id

    async def async_has_media_milestone(self, media_batch_id: str, event_type: str) -> bool:
        return await self._hass.async_add_executor_job(
            self._has_media_milestone_sync, media_batch_id, event_type
        )

    def _has_media_milestone_sync(self, media_batch_id: str, event_type: str) -> bool:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT 1 FROM media_milestones
            WHERE media_batch_id = ? AND event_type = ?
            LIMIT 1
            """,
            (media_batch_id, event_type),
        ).fetchone()
        return row is not None

    # --- Culture events ---

    async def async_insert_culture_event(self, event: CultureEvent) -> CultureEvent:
        return await self._hass.async_add_executor_job(
            self._insert_culture_event_sync, event
        )

    def _insert_culture_event_sync(self, event: CultureEvent) -> CultureEvent:
        assert self._conn is not None
        created = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO culture_events (
              stable_id, event_type, culture_id, child_culture_id, media_batch_id,
              detail, recorded_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.event_type,
                event.culture_id,
                event.child_culture_id,
                event.media_batch_id,
                json.dumps(event.detail) if event.detail else None,
                event.recorded_at,
                created,
            ),
        )
        self._conn.commit()
        return event

    async def async_list_culture_events_for_media(
        self, media_batch_id: str
    ) -> list[CultureEvent]:
        return await self._hass.async_add_executor_job(
            self._list_culture_events_for_media_sync, media_batch_id
        )

    def _list_culture_events_for_media_sync(
        self, media_batch_id: str
    ) -> list[CultureEvent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM culture_events
            WHERE media_batch_id = ?
            ORDER BY recorded_at ASC, id ASC
            """,
            (media_batch_id,),
        ).fetchall()
        return [self._row_to_culture_event(row) for row in rows]

    # --- Composite flows ---

    async def async_acquire_culture(self, lot: CultureLot) -> CultureLot:
        """Persist a new culture lot and CultureAcquired event."""
        return await self._hass.async_add_executor_job(self._acquire_culture_sync, lot)

    def _acquire_culture_sync(self, lot: CultureLot) -> CultureLot:
        lot = self._insert_culture_sync(lot)
        when = lot.acquired_at or datetime.now(tz=UTC).isoformat()
        self._insert_culture_event_sync(
            CultureEvent(
                event_type=EVENT_CULTURE_ACQUIRED,
                culture_id=lot.id,
                recorded_at=when,
                detail={
                    "source_type": lot.source_type,
                    "form": lot.form,
                    "container": lot.container,
                },
            )
        )
        return lot

    async def async_create_media_batch(self, batch: MediaBatch) -> MediaBatch:
        return await self._hass.async_add_executor_job(self._create_media_batch_sync, batch)

    def _create_media_batch_sync(self, batch: MediaBatch) -> MediaBatch:
        batch = self._insert_media_batch_sync(batch)
        when = batch.created_at or datetime.now(tz=UTC).isoformat()
        self._insert_culture_event_sync(
            CultureEvent(
                event_type=EVENT_MEDIA_BATCH_CREATED,
                media_batch_id=batch.id,
                recorded_at=when,
                detail={
                    "recipe_key": batch.recipe_key,
                    "media_form": batch.media_form,
                    "vessel_type": batch.vessel_type,
                },
            )
        )
        return batch

    async def async_introduce_culture(
        self,
        *,
        parent_culture_id: str,
        media_batch_id: str,
        child_name: str | None = None,
        child_form: str | None = None,
        child_container: str | None = None,
        recorded_at: str | None = None,
    ) -> tuple[CultureLot, CultureEvent]:
        """Gate on media ready, create child lot, append CultureIntroduced."""
        return await self._hass.async_add_executor_job(
            self._introduce_culture_sync,
            parent_culture_id,
            media_batch_id,
            child_name,
            child_form,
            child_container,
            recorded_at,
        )

    def _introduce_culture_sync(
        self,
        parent_culture_id: str,
        media_batch_id: str,
        child_name: str | None,
        child_form: str | None,
        child_container: str | None,
        recorded_at: str | None,
    ) -> tuple[CultureLot, CultureEvent]:
        parent = self._get_culture_sync(parent_culture_id)
        if parent is None:
            raise ValueError(f"unknown culture_id: {parent_culture_id}")
        media = self._get_media_batch_sync(media_batch_id)
        if media is None:
            raise ValueError(f"unknown media_batch_id: {media_batch_id}")
        assert_media_accepts_culture(media.status)

        when = recorded_at or datetime.now(tz=UTC).isoformat()
        child = child_culture_from_parent(
            parent,
            name=child_name,
            form=child_form,
            container=child_container,
            acquired_at=when,
        )
        child = self._insert_culture_sync(child)
        event = self._insert_culture_event_sync(
            CultureEvent(
                event_type=EVENT_CULTURE_INTRODUCED,
                culture_id=parent.id,
                child_culture_id=child.id,
                media_batch_id=media.id,
                recorded_at=when,
                detail={
                    "parent_form": parent.form,
                    "child_form": child.form,
                    "media_recipe_key": media.recipe_key,
                },
            )
        )
        if media.status == MEDIA_STATUS_READY:
            self._set_media_status_sync(media.id, MEDIA_STATUS_IN_USE, None, None)
        return child, event

    async def async_ensure_weighing_started(
        self, media_batch_id: str, recorded_at: str
    ) -> None:
        if await self.async_has_media_milestone(media_batch_id, MILESTONE_WEIGHING_STARTED):
            return
        await self.async_insert_media_milestone(
            media_batch_id=media_batch_id,
            event_type=MILESTONE_WEIGHING_STARTED,
            recorded_at=recorded_at,
        )

    @staticmethod
    def _row_to_culture(row: Any) -> CultureLot:
        return CultureLot(
            id=row["stable_id"],
            site_id=row["site_id"],
            environment_id=row["environment_id"],
            name=row["name"],
            source_type=row["source_type"],
            form=row["form"],
            container=row["container"],
            strain_label=row["strain_label"] or "",
            parent_culture_id=row["parent_culture_id"],
            status=row["status"],
            acquired_at=row["acquired_at"],
            nfc_uid=row["nfc_uid"],
            notes=row["notes"],
        )

    @staticmethod
    def _row_to_media(row: Any) -> MediaBatch:
        return MediaBatch(
            id=row["stable_id"],
            site_id=row["site_id"],
            environment_id=row["environment_id"],
            name=row["name"],
            recipe_key=row["recipe_key"],
            media_form=row["media_form"],
            vessel_type=row["vessel_type"],
            recipe_scale=float(row["recipe_scale"] or 1.0),
            status=row["status"],
            vessel_count=row["vessel_count"],
            sterilized_at=row["sterilized_at"],
            ready_at=row["ready_at"],
            nfc_uid=row["nfc_uid"],
            notes=row["notes"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_media_weight(row: Any) -> MediaWeightEvent:
        return MediaWeightEvent(
            id=row["stable_id"],
            site_id=row["site_id"],
            environment_id=row["environment_id"],
            media_batch_id=row["media_batch_id"],
            amount=float(row["amount"]),
            unit=row["unit"],
            recorded_at=row["recorded_at"],
            ingredient_key=row["ingredient_key"],
            ingredient_label=row["ingredient_label"],
            recipe_scale=row["recipe_scale"],
            target_amount=row["target_amount"],
            source_entity_id=row["source_entity_id"],
        )

    @staticmethod
    def _row_to_culture_event(row: Any) -> CultureEvent:
        detail: dict[str, Any] = {}
        raw = row["detail"]
        if raw:
            detail = json.loads(raw)
        return CultureEvent(
            id=row["stable_id"],
            event_type=row["event_type"],
            culture_id=row["culture_id"],
            child_culture_id=row["child_culture_id"],
            media_batch_id=row["media_batch_id"],
            detail=detail,
            recorded_at=row["recorded_at"],
        )
