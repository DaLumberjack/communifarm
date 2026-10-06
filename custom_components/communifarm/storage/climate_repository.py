"""SQLite repository for climate nodes, bindings, and command intents."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..domain.climate import (
    KIND_GENERAL_ROOM,
    KIND_SPECS,
    PLACEMENT_AREA_CLIMATE_KIND,
    ClimateBinding,
    ClimateNode,
    build_operator_layout,
    validate_climate_node,
)
from ..domain.climate_control import ControlIntent
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
        existing = self._list_nodes_sync(site_id)
        if existing:
            self._apply_preset_targets_sync(existing)
            self._link_placement_sync(site_id, existing)
            self._conn.commit()
            return existing

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
        """Move tent targets onto the current preset. The general room stays the profile."""
        assert self._conn is not None
        for node in nodes:
            if node.kind == KIND_GENERAL_ROOM:
                continue
            spec = KIND_SPECS.get(node.kind)
            if spec is None:
                continue
            if (
                node.temperature_target == spec.temperature_target
                and node.humidity_target == spec.humidity_target
            ):
                continue
            self._conn.execute(
                """
                UPDATE climate_nodes
                SET temperature_target = ?, humidity_target = ?
                WHERE stable_id = ?
                """,
                (spec.temperature_target, spec.humidity_target, node.id),
            )
            node.temperature_target = spec.temperature_target
            node.humidity_target = spec.humidity_target

    async def async_list_nodes(self, site_id: str) -> list[ClimateNode]:
        return await self._hass.async_add_executor_job(
            self._locked, self._list_nodes_sync, site_id
        )

    def _list_nodes_sync(self, site_id: str) -> list[ClimateNode]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM climate_nodes
            WHERE site_id = ?
            ORDER BY id ASC
            """,
            (site_id,),
        ).fetchall()
        return [_row_to_node(row) for row in rows]

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
                SET entity_id = ?, waste_heat_to_parent = ?
                WHERE stable_id = ?
                """,
                (binding.entity_id, waste, row["stable_id"]),
            )
            binding.id = row["stable_id"]
        else:
            if not binding.id:
                binding.id = new_id("cbind")
            self._conn.execute(
                """
                INSERT INTO climate_bindings (
                  stable_id, node_id, role, entity_entry_id, entity_id,
                  waste_heat_to_parent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    binding.id,
                    binding.node_id,
                    binding.role,
                    binding.entity_entry_id,
                    binding.entity_id,
                    waste,
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
                  stable_id, node_id, role, entity_id, turn_on, reason, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("intent"),
                    intent.node_id,
                    intent.role,
                    intent.entity_id,
                    1 if intent.turn_on else 0,
                    intent.reason,
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
            SELECT node_id, role, entity_id, turn_on, reason, recorded_at
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
        created_at=row["created_at"],
    )
