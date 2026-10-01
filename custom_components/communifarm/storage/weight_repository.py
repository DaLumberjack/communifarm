"""SQLite repository for Communifarm weight / material events."""

from __future__ import annotations

from datetime import UTC, datetime

from ..domain.weight import WeightEvent
from .sqlite_repository import SqliteRepository


class WeightEventRepository(SqliteRepository):
    """Append-only weight events for local analysis and future cloud sync."""

    _ready_label = "Communifarm SQLite"


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
