"""Pure dashboard model builder (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any

from ..const import (
    DASHBOARD_TITLE,
    ROLE_FAN,
    ROLE_HUMIDITY,
    ROLE_SWITCH,
    ROLE_TEMPERATURE,
)
from ..domain.models import CommunifarmState


class DashboardBuilder:
    """Build a mobile-first Lovelace view from Communifarm state."""

    def build(self, state: CommunifarmState, resolved: dict[str, str | None]) -> dict[str, Any]:
        """Return a Lovelace dashboard config dict.

        resolved maps role -> current entity_id (may be None).
        """
        cards: list[dict[str, Any]] = [
            {
                "type": "markdown",
                "content": (
                    f"## {state.environment.name}\n"
                    f"Site: **{state.site.name}**\n"
                    f"Batch: **{state.batch.name}** ({state.batch.stage})"
                ),
            }
        ]

        sensor_entities = [
            entity_id
            for role in (ROLE_TEMPERATURE, ROLE_HUMIDITY)
            if (entity_id := resolved.get(role))
        ]
        if sensor_entities:
            cards.append({"type": "entities", "title": "Environment", "entities": sensor_entities})

        cards.append(
            {
                "type": "entities",
                "title": "Targets",
                "entities": [
                    "number.communifarm_temperature_target",
                    "number.communifarm_humidity_target",
                ],
            }
        )

        actuator_entities = [
            entity_id
            for role in (ROLE_FAN, ROLE_SWITCH)
            if (entity_id := resolved.get(role))
        ]
        # Prefer Communifarm proxy switch when a switch binding exists.
        control_entities: list[str] = []
        if resolved.get(ROLE_SWITCH):
            control_entities.append("switch.communifarm_allowlisted_switch")
        if resolved.get(ROLE_FAN):
            control_entities.append(resolved[ROLE_FAN])  # type: ignore[arg-type]
        if not control_entities and actuator_entities:
            control_entities = actuator_entities
        if control_entities:
            cards.append(
                {"type": "entities", "title": "Controls", "entities": control_entities}
            )

        cards.append(
            {
                "type": "entities",
                "title": "Production",
                "entities": ["sensor.communifarm_batch_stage"],
            }
        )

        return {
            "title": DASHBOARD_TITLE,
            "views": [
                {
                    "title": state.environment.name,
                    "path": "overview",
                    "cards": cards,
                }
            ],
        }
