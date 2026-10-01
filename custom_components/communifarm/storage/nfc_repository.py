"""SQLite repository for NFC check-ins and cross-object resolve."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.core import HomeAssistant

from ..domain.nfc import (
    OBJECT_BATCH,
    OBJECT_CONTAINER,
    OBJECT_CULTURE,
    OBJECT_MEDIA,
    OBJECT_UNKNOWN,
    NfcCheckin,
    NfcResolution,
)
from .container_repository import ContainerRepository


class NfcRepository:
    """Resolve NFC UIDs across Communifarm objects and append check-ins."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        container_repo: ContainerRepository,
        batch_repo: Any,
        culture_repo: Any,
    ) -> None:
        self._hass = hass
        self._containers = container_repo
        self._batches = batch_repo
        self._cultures = culture_repo
        self._conn = None

    def bind_connection(self, conn: Any) -> None:
        self._conn = conn

    async def async_resolve(self, nfc_uid: str) -> NfcResolution:
        return await self._hass.async_add_executor_job(self._resolve_sync, nfc_uid)

    def _resolve_sync(self, nfc_uid: str) -> NfcResolution:
        # Prefer containers (per-block tags) over batch-level tags.
        cont = self._containers._get_by_nfc_sync(nfc_uid)
        if cont is not None:
            return NfcResolution(
                nfc_uid=nfc_uid,
                object_type=OBJECT_CONTAINER,
                object_id=cont.id,
                label=f"{cont.container_type} #{cont.container_index}",
                batch_id=cont.batch_id,
                zone_id=cont.zone_id,
                lifecycle_phase=cont.lifecycle_phase,
                flush_count=cont.flush_count,
                max_flushes=cont.max_flushes,
                found=True,
                detail={
                    "container_index": cont.container_index,
                    "container_type": cont.container_type,
                    "status": cont.status,
                },
            )

        batch = self._batches._get_batch_sync(nfc_uid)
        if batch is None:
            # Also match batches.nfc_uid when different from stable_id.
            batch = self._find_batch_by_nfc_sync(nfc_uid)
        if batch is not None:
            return NfcResolution(
                nfc_uid=nfc_uid,
                object_type=OBJECT_BATCH,
                object_id=batch.id,
                label=batch.name,
                batch_id=batch.id,
                zone_id=batch.zone_id,
                lifecycle_phase=batch.lifecycle_phase,
                flush_count=batch.flush_count,
                max_flushes=batch.max_flushes,
                found=True,
            )

        culture = self._find_culture_by_nfc_sync(nfc_uid)
        if culture is not None:
            return NfcResolution(
                nfc_uid=nfc_uid,
                object_type=OBJECT_CULTURE,
                object_id=culture.id,
                label=culture.name,
                zone_id=getattr(culture, "zone_id", None),
                found=True,
                detail={"form": culture.form, "status": culture.status},
            )

        media = self._find_media_by_nfc_sync(nfc_uid)
        if media is not None:
            return NfcResolution(
                nfc_uid=nfc_uid,
                object_type=OBJECT_MEDIA,
                object_id=media.id,
                label=media.name,
                zone_id=getattr(media, "zone_id", None),
                found=True,
                detail={"status": media.status, "recipe_key": media.recipe_key},
            )

        return NfcResolution(
            nfc_uid=nfc_uid,
            object_type=OBJECT_UNKNOWN,
            found=False,
        )

    def _find_batch_by_nfc_sync(self, nfc_uid: str) -> Any | None:
        conn = getattr(self._batches, "_conn", None)
        if conn is None:
            return None
        row = conn.execute(
            "SELECT * FROM batches WHERE nfc_uid = ? LIMIT 1", (nfc_uid,)
        ).fetchone()
        if row is None:
            return None
        return self._batches._row_to_batch(row)

    def _find_culture_by_nfc_sync(self, nfc_uid: str) -> Any | None:
        conn = getattr(self._cultures, "_conn", None)
        if conn is None:
            return None
        row = conn.execute(
            "SELECT * FROM culture_lots WHERE nfc_uid = ? LIMIT 1", (nfc_uid,)
        ).fetchone()
        if row is None:
            return None
        return self._cultures._row_to_culture(row)

    def _find_media_by_nfc_sync(self, nfc_uid: str) -> Any | None:
        conn = getattr(self._cultures, "_conn", None)
        if conn is None:
            return None
        row = conn.execute(
            "SELECT * FROM media_batches WHERE nfc_uid = ? LIMIT 1", (nfc_uid,)
        ).fetchone()
        if row is None:
            return None
        return self._cultures._row_to_media(row)

    async def async_insert_checkin(self, event: NfcCheckin) -> NfcCheckin:
        return await self._hass.async_add_executor_job(
            self._insert_checkin_sync, event
        )

    def _insert_checkin_sync(self, event: NfcCheckin) -> NfcCheckin:
        conn = getattr(self._batches, "_conn", None)
        assert conn is not None
        created = event.recorded_at
        detail_json = json.dumps(event.detail) if event.detail else None
        conn.execute(
            """
            INSERT INTO nfc_checkins (
              stable_id, nfc_uid, object_type, object_id, activity,
              zone_id, detail, recorded_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.nfc_uid,
                event.object_type,
                event.object_id,
                event.activity,
                event.zone_id,
                detail_json,
                event.recorded_at,
                created,
            ),
        )
        conn.commit()
        return event
