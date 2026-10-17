"""SQLite repository for climate nodes, bindings, and command intents."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..domain.climate import (
    DEFAULT_HUMIDITY_DEADBAND,
    DEFAULT_TEMP_DEADBAND_C,
    KIND_GENERAL_ROOM,
    KIND_SPECS,
    PHOTOPERIOD_HOURS,
    PLACEMENT_AREA_CLIMATE_KIND,
    ClimateBinding,
    ClimateNode,
    build_operator_layout,
    validate_climate_node,
)
from ..domain.climate_control import ControlIntent
from ..domain.climate_settings import (
    SCOPE_NODE,
    SETTING_CO2_PPM_TARGET,
    SETTING_SCOPES,
    validate_setting,
)
from ..domain.models import new_id
from ..domain.validation import ValidationError
from .sqlite_repository import SqliteRepository

_LOGGER = logging.getLogger(__name__)


class ClimateRepository(SqliteRepository):
    """Climate tree under a site. I/O stays off the event loop."""

    _ready_label = "Communifarm climate SQLite"

    async def async_ensure_operator_layout(
        self,
        site_id: str,
        *,
        general_room_id: str,
        general_room_name: str,
        general_temperature_target: float,
        general_humidity_target: float,
    ) -> list[ClimateNode]:
        return await self._hass.async_add_executor_job(
            self._locked,
            self._ensure_operator_layout_sync,
            site_id,
            general_room_id,
            general_room_name,
            general_temperature_target,
            general_humidity_target,
        )

    def _ensure_operator_layout_sync(
        self,
        site_id: str,
        general_room_id: str,
        general_room_name: str,
        general_temperature_target: float,
        general_humidity_target: float,
    ) -> list[ClimateNode]:
        assert self._conn is not None
        existing = self._list_nodes_sync(site_id, False)
        if existing:
            self._apply_preset_targets_sync(existing)
            self._link_placement_sync(site_id, existing)
            self._conn.commit()
            return self._list_nodes_sync(site_id, True)

        nodes = build_operator_layout(
            site_id,
            general_room_id=general_room_id,
            general_room_name=general_room_name,
            general_temperature_target=general_temperature_target,
            general_humidity_target=general_humidity_target,
        )
        when = datetime.now(tz=UTC).isoformat()
        for node in nodes:
            validate_climate_node(node)
            self._insert_node_sync(node, when)
            node.created_at = when
        self._link_placement_sync(site_id, nodes)
        self._conn.commit()
        _LOGGER.info(
            "Seeded climate layout for site %s: %s nodes", site_id, len(nodes)
        )
        return nodes

    def _apply_preset_targets_sync(self, nodes: list[ClimateNode]) -> None:
        """Refresh repository defaults while preserving separate user overrides."""
        assert self._conn is not None
        for node in nodes:
            spec = KIND_SPECS.get(node.kind)
            if spec is None:
                continue
            temperature = (
                node.temperature_target
                if node.kind == KIND_GENERAL_ROOM
                else spec.temperature_target
            )
            humidity = (
                node.humidity_target
                if node.kind == KIND_GENERAL_ROOM
                else spec.humidity_target
            )
            light_hours = (
                PHOTOPERIOD_HOURS[spec.photoperiod_preset]
                if spec.photoperiod_preset
                else (None, None)
            )
            self._conn.execute(
                """
                UPDATE climate_nodes
                SET temperature_target = ?, humidity_target = ?,
                    co2_ppm_target = ?, temp_deadband = ?,
                    humidity_deadband = ?, photoperiod_preset = ?,
                    light_hours_on = ?, light_hours_off = ?
                WHERE stable_id = ?
                """,
                (
                    temperature,
                    humidity,
                    spec.co2_ppm_target,
                    DEFAULT_TEMP_DEADBAND_C,
                    DEFAULT_HUMIDITY_DEADBAND,
                    spec.photoperiod_preset,
                    light_hours[0],
                    light_hours[1],
                    node.id,
                ),
            )

    async def async_list_nodes(self, site_id: str) -> list[ClimateNode]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_nodes_sync, site_id
        )

    def _list_nodes_sync(
        self, site_id: str, apply_overrides: bool = True
    ) -> list[ClimateNode]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM climate_nodes
            WHERE site_id = ?
            ORDER BY id ASC
            """,
            (site_id,),
        ).fetchall()
        nodes = [_row_to_node(row) for row in rows]
        if apply_overrides:
            self._apply_node_overrides_sync(nodes)
        return nodes

    def _apply_node_overrides_sync(self, nodes: list[ClimateNode]) -> None:
        assert self._conn is not None
        by_id = {node.id: node for node in nodes}
        rows = self._conn.execute(
            """
            SELECT scope_id, setting_key, value
            FROM climate_setting_overrides
            WHERE scope_type = ?
            """,
            (SCOPE_NODE,),
        ).fetchall()
        for row in rows:
            node = by_id.get(row["scope_id"])
            if node is None or not hasattr(node, row["setting_key"]):
                continue
            value: float | None = float(row["value"])
            if row["setting_key"] == SETTING_CO2_PPM_TARGET and value <= 0:
                value = None
            setattr(node, row["setting_key"], value)
            validate_climate_node(node)

    async def async_get_setting_overrides(
        self, scope_type: str, scope_id: str
    ) -> dict[str, float]:
        return await self._hass.async_add_executor_job(
            self._locked, self._get_setting_overrides_sync, scope_type, scope_id
        )

    def _get_setting_overrides_sync(
        self, scope_type: str, scope_id: str
    ) -> dict[str, float]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT setting_key, value
            FROM climate_setting_overrides
            WHERE scope_type = ? AND scope_id = ?
            """,
            (scope_type, scope_id),
        ).fetchall()
        return {row["setting_key"]: float(row["value"]) for row in rows}

    async def async_set_setting_override(
        self, scope_type: str, scope_id: str, setting_key: str, value: float
    ) -> None:
        await self._hass.async_add_executor_job(
            self._locked,
            self._set_setting_override_sync,
            scope_type,
            scope_id,
            setting_key,
            value,
        )

    def _set_setting_override_sync(
        self, scope_type: str, scope_id: str, setting_key: str, value: float
    ) -> None:
        assert self._conn is not None
        if scope_type not in SETTING_SCOPES:
            raise ValidationError(f"unsupported climate setting scope: {scope_type}")
        number = validate_setting(scope_type, setting_key, value)
        self._conn.execute(
            """
            INSERT INTO climate_setting_overrides (
              scope_type, scope_id, setting_key, value, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, scope_id, setting_key)
            DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (
                scope_type,
                scope_id,
                setting_key,
                number,
                datetime.now(tz=UTC).isoformat(),
            ),
        )
        self._conn.commit()

    async def async_clear_setting_overrides(
        self, scope_type: str, scope_id: str
    ) -> None:
        await self._hass.async_add_executor_job(
            self._locked, self._clear_setting_overrides_sync, scope_type, scope_id
        )

    def _clear_setting_overrides_sync(self, scope_type: str, scope_id: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            DELETE FROM climate_setting_overrides
            WHERE scope_type = ? AND scope_id = ?
            """,
            (scope_type, scope_id),
        )
        self._conn.commit()

    async def async_list_bindings(self, site_id: str) -> list[ClimateBinding]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_bindings_sync, site_id
        )

    def _list_bindings_sync(self, site_id: str) -> list[ClimateBinding]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT b.* FROM climate_bindings AS b
            JOIN climate_nodes AS n ON n.stable_id = b.node_id
            WHERE n.site_id = ?
            ORDER BY b.id ASC
            """,
            (site_id,),
        ).fetchall()
        return [_row_to_binding(row) for row in rows]

    async def async_upsert_binding(self, binding: ClimateBinding) -> ClimateBinding:
        return await self._hass.async_add_executor_job(
            self._locked, self._upsert_binding_sync, binding
        )

    def _upsert_binding_sync(self, binding: ClimateBinding) -> ClimateBinding:
        assert self._conn is not None
        if binding.role is None or not str(binding.role).strip():
            raise ValidationError("climate binding role is required")
        if not binding.entity_entry_id or not str(binding.entity_entry_id).strip():
            raise ValidationError("entity_entry_id is required")
        when = datetime.now(tz=UTC).isoformat()
        row = self._conn.execute(
            """
            SELECT stable_id FROM climate_bindings
            WHERE node_id = ? AND role = ? AND entity_entry_id = ?
            """,
            (binding.node_id, binding.role, binding.entity_entry_id),
        ).fetchone()
        waste = 1 if binding.waste_heat_to_parent else 0
        if row:
            self._conn.execute(
                """
                UPDATE climate_bindings
                SET entity_id = ?, waste_heat_to_parent = ?, zone_id = ?
                WHERE stable_id = ?
                """,
                (binding.entity_id, waste, binding.zone_id, row["stable_id"]),
            )
            binding.id = row["stable_id"]
        else:
            if not binding.id:
                binding.id = new_id("cbind")
            self._conn.execute(
                """
                INSERT INTO climate_bindings (
                  stable_id, node_id, role, entity_entry_id, entity_id,
                  waste_heat_to_parent, zone_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    binding.id,
                    binding.node_id,
                    binding.role,
                    binding.entity_entry_id,
                    binding.entity_id,
                    waste,
                    binding.zone_id,
                    when,
                ),
            )
            binding.created_at = when
        self._conn.commit()
        return binding

    async def async_insert_intents(
        self, intents: list[ControlIntent], recorded_at: str
    ) -> None:
        await self._hass.async_add_executor_job(
            self._locked, self._insert_intents_sync, intents, recorded_at
        )

    def _insert_intents_sync(
        self, intents: list[ControlIntent], recorded_at: str
    ) -> None:
        assert self._conn is not None
        for intent in intents:
            self._conn.execute(
                """
                INSERT INTO climate_intents (
                  stable_id, node_id, role, entity_id, turn_on, reason, zone_id,
                  recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("intent"),
                    intent.node_id,
                    intent.role,
                    intent.entity_id,
                    1 if intent.turn_on else 0,
                    intent.reason,
                    intent.zone_id,
                    recorded_at,
                ),
            )
        if intents:
            self._conn.commit()

    async def async_list_recent_intents(self, limit: int = 20) -> list[dict[str, Any]]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_recent_intents_sync, limit
        )

    def _list_recent_intents_sync(self, limit: int) -> list[dict[str, Any]]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT node_id, role, entity_id, turn_on, reason, zone_id, recorded_at
            FROM climate_intents
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [
            {
                "node_id": row["node_id"],
                "role": row["role"],
                "entity_id": row["entity_id"],
                "turn_on": bool(row["turn_on"]),
                "reason": row["reason"],
                "zone_id": row["zone_id"],
                "recorded_at": row["recorded_at"],
            }
            for row in rows
        ]

    def _insert_node_sync(self, node: ClimateNode, when: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO climate_nodes (
              stable_id, site_id, parent_id, name, kind, enclosure, control_enabled,
              temperature_target, humidity_target, co2_ppm_target, temp_deadband,
              humidity_deadband, photoperiod_preset, light_hours_on, light_hours_off,
              created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node.id,
                node.site_id,
                node.parent_id,
                node.name,
                node.kind,
                node.enclosure,
                1 if node.control_enabled else 0,
                node.temperature_target,
                node.humidity_target,
                node.co2_ppm_target,
                node.temp_deadband,
                node.humidity_deadband,
                node.photoperiod_preset,
                node.light_hours_on,
                node.light_hours_off,
                when,
            ),
        )

    def _link_placement_sync(self, site_id: str, nodes: list[ClimateNode]) -> None:
        assert self._conn is not None
        by_kind = {node.kind: node.id for node in nodes}
        for area_kind, climate_kind in PLACEMENT_AREA_CLIMATE_KIND.items():
            node_id = by_kind.get(climate_kind)
            if not node_id:
                continue
            self._conn.execute(
                """
                UPDATE placement_areas
                SET climate_id = ?
                WHERE site_id = ? AND area_kind = ? AND climate_id IS NULL
                """,
                (node_id, site_id, area_kind),
            )


def _row_to_node(row: Any) -> ClimateNode:
    return ClimateNode(
        id=row["stable_id"],
        site_id=row["site_id"],
        parent_id=row["parent_id"],
        name=row["name"],
        kind=row["kind"],
        enclosure=row["enclosure"],
        control_enabled=bool(row["control_enabled"]),
        temperature_target=row["temperature_target"],
        humidity_target=row["humidity_target"],
        co2_ppm_target=row["co2_ppm_target"],
        temp_deadband=float(row["temp_deadband"]),
        humidity_deadband=float(row["humidity_deadband"]),
        photoperiod_preset=row["photoperiod_preset"],
        light_hours_on=row["light_hours_on"],
        light_hours_off=row["light_hours_off"],
        created_at=row["created_at"],
    )


def _row_to_binding(row: Any) -> ClimateBinding:
    return ClimateBinding(
        id=row["stable_id"],
        node_id=row["node_id"],
        role=row["role"],
        entity_entry_id=row["entity_entry_id"],
        entity_id=row["entity_id"],
        waste_heat_to_parent=bool(row["waste_heat_to_parent"]),
        zone_id=row["zone_id"] if "zone_id" in row.keys() else None,
        created_at=row["created_at"],
    )
