"""SQLite repository for labeled vents and tachometer readings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..domain.models import new_id
from ..domain.tachometer import (
    SOURCE_MANUAL,
    AirVent,
    TachometerReading,
    normalize_vent_label,
    validate_tach_unit,
    validate_tach_value,
    validate_vent_role,
)
from ..domain.validation import ValidationError
from .sqlite_repository import SqliteRepository

_LOGGER = logging.getLogger(__name__)


class TachometerRepository(SqliteRepository):
    """Manual air-exchange tachometer log. I/O stays off the event loop."""

    _ready_label = "Communifarm tachometer SQLite"

    async def async_upsert_vent(
        self,
        *,
        site_id: str,
        label: str,
        vent_role: str,
        climate_node_id: str | None = None,
        notes: str | None = None,
        vent_id: str | None = None,
    ) -> AirVent:
        return await self._hass.async_add_executor_job(
            self._locked,
            self._upsert_vent_sync,
            site_id,
            label,
            vent_role,
            climate_node_id,
            notes,
            vent_id,
        )

    def _upsert_vent_sync(
        self,
        site_id: str,
        label: str,
        vent_role: str,
        climate_node_id: str | None,
        notes: str | None,
        vent_id: str | None,
    ) -> AirVent:
        assert self._conn is not None
        clean_label = normalize_vent_label(label)
        clean_role = validate_vent_role(vent_role)
        when = datetime.now(tz=UTC).isoformat()
        existing = None
        if vent_id:
            existing = self._get_vent_sync(vent_id)
            if existing is None or existing.site_id != site_id:
                raise ValidationError(f"Unknown vent_id: {vent_id}")
        else:
            existing = self._find_active_by_label_sync(site_id, clean_label)

        if existing is None:
            vent = AirVent(
                id=new_id("vent"),
                site_id=site_id,
                label=clean_label,
                vent_role=clean_role,
                climate_node_id=climate_node_id or None,
                notes=notes,
                created_at=when,
            )
            self._conn.execute(
                """
                INSERT INTO air_vents (
                  stable_id, site_id, climate_node_id, label, vent_role,
                  notes, created_at, retired_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    vent.id,
                    vent.site_id,
                    vent.climate_node_id,
                    vent.label,
                    vent.vent_role,
                    vent.notes,
                    vent.created_at,
                ),
            )
            self._conn.commit()
            _LOGGER.info("Registered air vent %s (%s)", vent.label, vent.id)
            return vent

        self._conn.execute(
            """
            UPDATE air_vents
            SET label = ?, vent_role = ?, climate_node_id = ?, notes = ?,
                retired_at = NULL
            WHERE stable_id = ?
            """,
            (
                clean_label,
                clean_role,
                climate_node_id if climate_node_id is not None else existing.climate_node_id,
                notes if notes is not None else existing.notes,
                existing.id,
            ),
        )
        self._conn.commit()
        updated = self._get_vent_sync(existing.id)
        assert updated is not None
        return updated

    async def async_record_reading(
        self,
        *,
        site_id: str,
        value: float,
        unit: str,
        vent_id: str | None = None,
        vent_label: str | None = None,
        recorded_at: str | None = None,
        notes: str | None = None,
        source: str = SOURCE_MANUAL,
        vent_role: str = "other",
        climate_node_id: str | None = None,
    ) -> TachometerReading:
        return await self._hass.async_add_executor_job(
            self._locked,
            self._record_reading_sync,
            site_id,
            value,
            unit,
            vent_id,
            vent_label,
            recorded_at,
            notes,
            source,
            vent_role,
            climate_node_id,
        )

    def _record_reading_sync(
        self,
        site_id: str,
        value: float,
        unit: str,
        vent_id: str | None,
        vent_label: str | None,
        recorded_at: str | None,
        notes: str | None,
        source: str,
        vent_role: str,
        climate_node_id: str | None,
    ) -> TachometerReading:
        assert self._conn is not None
        clean_value = validate_tach_value(value)
        clean_unit = validate_tach_unit(unit)
        when = datetime.now(tz=UTC).isoformat()
        stamp = (recorded_at or "").strip() or when

        vent: AirVent | None = None
        if vent_id:
            vent = self._get_vent_sync(vent_id)
            if vent is None or vent.site_id != site_id:
                raise ValidationError(f"Unknown vent_id: {vent_id}")
        elif vent_label:
            vent = self._find_active_by_label_sync(site_id, normalize_vent_label(vent_label))
            if vent is None:
                vent = self._upsert_vent_sync(
                    site_id,
                    vent_label,
                    vent_role,
                    climate_node_id,
                    None,
                    None,
                )
        else:
            raise ValidationError("Provide vent_id or vent_label")

        reading = TachometerReading(
            id=new_id("tach"),
            vent_id=vent.id,
            site_id=site_id,
            value=clean_value,
            unit=clean_unit,
            recorded_at=stamp,
            source=(source or SOURCE_MANUAL).strip() or SOURCE_MANUAL,
            notes=notes,
            created_at=when,
            vent_label=vent.label,
        )
        self._conn.execute(
            """
            INSERT INTO tachometer_readings (
              stable_id, vent_id, site_id, value, unit, recorded_at,
              source, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reading.id,
                reading.vent_id,
                reading.site_id,
                reading.value,
                reading.unit,
                reading.recorded_at,
                reading.source,
                reading.notes,
                reading.created_at,
            ),
        )
        self._conn.commit()
        _LOGGER.info(
            "Tachometer %s %s on vent %s at %s",
            reading.value,
            reading.unit,
            vent.label,
            reading.recorded_at,
        )
        return reading

    async def async_list_vents(self, site_id: str) -> list[AirVent]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_vents_sync, site_id
        )

    def _list_vents_sync(self, site_id: str) -> list[AirVent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM air_vents
            WHERE site_id = ? AND retired_at IS NULL
            ORDER BY label COLLATE NOCASE
            """,
            (site_id,),
        ).fetchall()
        return [self._row_to_vent(row) for row in rows]

    async def async_list_recent_readings(
        self, site_id: str, *, limit: int = 20
    ) -> list[TachometerReading]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_recent_readings_sync, site_id, limit
        )

    def _list_recent_readings_sync(
        self, site_id: str, limit: int
    ) -> list[TachometerReading]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT r.*, v.label AS vent_label
            FROM tachometer_readings r
            JOIN air_vents v ON v.stable_id = r.vent_id
            WHERE r.site_id = ?
            ORDER BY r.recorded_at DESC, r.id DESC
            LIMIT ?
            """,
            (site_id, max(1, min(int(limit), 200))),
        ).fetchall()
        return [self._row_to_reading(row) for row in rows]

    async def async_snapshot(self, site_id: str) -> dict[str, Any]:
        vents = await self.async_list_vents(site_id)
        recent = await self.async_list_recent_readings(site_id, limit=20)
        last = recent[0] if recent else None
        return {
            "site_id": site_id,
            "vent_count": len(vents),
            "reading_count": len(recent),
            "vents": [
                {
                    "id": v.id,
                    "label": v.label,
                    "vent_role": v.vent_role,
                    "climate_node_id": v.climate_node_id,
                }
                for v in vents
            ],
            "recent_readings": [
                {
                    "id": r.id,
                    "vent_id": r.vent_id,
                    "vent_label": r.vent_label,
                    "value": r.value,
                    "unit": r.unit,
                    "recorded_at": r.recorded_at,
                    "source": r.source,
                }
                for r in recent
            ],
            "last_value": last.value if last else None,
            "last_unit": last.unit if last else None,
            "last_vent_label": last.vent_label if last else None,
            "last_recorded_at": last.recorded_at if last else None,
        }

    def _find_active_by_label_sync(self, site_id: str, label: str) -> AirVent | None:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT * FROM air_vents
            WHERE site_id = ? AND label = ? COLLATE NOCASE AND retired_at IS NULL
            LIMIT 1
            """,
            (site_id, label),
        ).fetchone()
        return self._row_to_vent(row) if row else None

    def _get_vent_sync(self, vent_id: str) -> AirVent | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM air_vents WHERE stable_id = ?",
            (vent_id,),
        ).fetchone()
        return self._row_to_vent(row) if row else None

    @staticmethod
    def _row_to_vent(row) -> AirVent:
        return AirVent(
            id=row["stable_id"],
            site_id=row["site_id"],
            label=row["label"],
            vent_role=row["vent_role"],
            climate_node_id=row["climate_node_id"],
            notes=row["notes"],
            created_at=row["created_at"],
            retired_at=row["retired_at"],
        )

    @staticmethod
    def _row_to_reading(row) -> TachometerReading:
        keys = row.keys()
        return TachometerReading(
            id=row["stable_id"],
            vent_id=row["vent_id"],
            site_id=row["site_id"],
            value=float(row["value"]),
            unit=row["unit"],
            recorded_at=row["recorded_at"],
            source=row["source"],
            notes=row["notes"],
            created_at=row["created_at"],
            vent_label=row["vent_label"] if "vent_label" in keys else None,
        )
