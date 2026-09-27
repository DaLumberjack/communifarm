"""Pure dashboard model builder (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any

from ..const import (
    DASHBOARD_TITLE,
    DASHBOARD_VIEW_OVERVIEW,
    DASHBOARD_VIEW_WEIGH,
    ENTITY_ALLOWLISTED_SWITCH,
    ENTITY_BATCH_NFC_UID,
    ENTITY_BATCH_STAGE,
    ENTITY_HUMIDITY_TARGET,
    ENTITY_RECIPE_SCALE,
    ENTITY_TEMPERATURE_TARGET,
    ENTITY_WEIGH_SESSION,
    ROLE_FAN,
    ROLE_HUMIDITY,
    ROLE_SWITCH,
    ROLE_TEMPERATURE,
)
from ..domain.models import CommunifarmState
from ..fixtures.esp32dev_scale import (
    ENTITY_ESP32DEV_CALIBRATED_G,
    ENTITY_ESP32DEV_CALIBRATED_SENSOR,
    ENTITY_ESP32DEV_LAST_RECORDED,
    ENTITY_ESP32DEV_LOCATION_TARE,
    ENTITY_ESP32DEV_RECORD_WEIGHT,
    ENTITY_ESP32DEV_SELECTED_INGREDIENT,
    ENTITY_ESP32DEV_TARE,
)


class DashboardBuilder:
    """Build a mobile-first Lovelace dashboard from Communifarm state."""

    def build(self, state: CommunifarmState, resolved: dict[str, str | None]) -> dict[str, Any]:
        """Return a Lovelace dashboard config dict.

        resolved maps role -> current entity_id (may be None).
        """
        return {
            "title": DASHBOARD_TITLE,
            "views": [
                self._overview_view(state, resolved),
                self._weigh_view(state),
            ],
        }

    def _overview_view(
        self, state: CommunifarmState, resolved: dict[str, str | None]
    ) -> dict[str, Any]:
        cards: list[dict[str, Any]] = [
            {
                "type": "markdown",
                "content": (
                    f"## {state.environment.name}\n"
                    f"Site: **{state.site.name}**\n"
                    f"Batch: **{state.batch.name}** ({state.batch.stage})"
                ),
            },
            {
                "type": "markdown",
                "title": "Current settings",
                "content": (
                    "Adjust targets below — no need to open Settings → Devices & services.\n\n"
                    "| Setting | Target |\n"
                    "| --- | ---: |\n"
                    f"| Temperature | "
                    f"{{{{ states('{ENTITY_TEMPERATURE_TARGET}') }}}} °C |\n"
                    f"| Humidity | "
                    f"{{{{ states('{ENTITY_HUMIDITY_TARGET}') }}}} % |\n\n"
                    "Values update live when you change the Targets controls.\n\n"
                    "Weighing? Open the **Weigh** tab."
                ),
            },
        ]

        sensor_entities = [
            entity_id
            for role in (ROLE_TEMPERATURE, ROLE_HUMIDITY)
            if (entity_id := resolved.get(role))
        ]
        if sensor_entities:
            cards.append(
                {"type": "entities", "title": "Environment", "entities": sensor_entities}
            )

        cards.append(
            {
                "type": "entities",
                "title": "Targets",
                "show_header_toggle": False,
                "entities": [
                    {
                        "entity": ENTITY_TEMPERATURE_TARGET,
                        "name": "Temperature target",
                        "secondary_info": "last-changed",
                    },
                    {
                        "entity": ENTITY_HUMIDITY_TARGET,
                        "name": "Humidity target",
                        "secondary_info": "last-changed",
                    },
                ],
            }
        )

        control_entities: list[str] = []
        if resolved.get(ROLE_SWITCH):
            control_entities.append(ENTITY_ALLOWLISTED_SWITCH)
        if resolved.get(ROLE_FAN):
            control_entities.append(resolved[ROLE_FAN])  # type: ignore[arg-type]
        if not control_entities:
            actuator_entities = [
                entity_id
                for role in (ROLE_FAN, ROLE_SWITCH)
                if (entity_id := resolved.get(role))
            ]
            control_entities = actuator_entities
        if control_entities:
            cards.append(
                {"type": "entities", "title": "Controls", "entities": control_entities}
            )

        cards.append(
            {
                "type": "entities",
                "title": "Production",
                "entities": [ENTITY_BATCH_STAGE],
            }
        )

        return {
            "title": state.environment.name,
            "path": DASHBOARD_VIEW_OVERVIEW,
            "icon": "mdi:home",
            "cards": cards,
        }

    def _weigh_view(self, state: CommunifarmState) -> dict[str, Any]:
        """Activity tab for scale tare / NFC ingredient / record during weighing."""
        return {
            "title": "Weigh",
            "path": DASHBOARD_VIEW_WEIGH,
            "icon": "mdi:scale-balance",
            "cards": [
                {
                    "type": "markdown",
                    "content": (
                        f"## Weigh station\n"
                        f"Batch: **{state.batch.name}** ({state.batch.stage})\n"
                        f"NFC UID: `{state.batch.nfc_uid}`\n\n"
                        "1. Set recipe scale if needed\n"
                        "2. Scan NFC (or pick ingredient)\n"
                        "3. Tare → add material → Record\n"
                        "Session progress below comes from Communifarm SQLite.\n"
                    ),
                },
                {
                    "type": "entities",
                    "title": "Recipe scale",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_RECIPE_SCALE,
                            "name": "Scale factor (0.1×–10×)",
                        },
                        {
                            "entity": ENTITY_BATCH_NFC_UID,
                            "name": "Batch NFC UID",
                        },
                        {
                            "entity": ENTITY_WEIGH_SESSION,
                            "name": "Session progress",
                        },
                    ],
                },
                {
                    "type": "markdown",
                    "title": "This session",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_WEIGH_SESSION}', 'progress_text') }}}}"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Live reading",
                    "content": (
                        "| | |\n"
                        "| --- | ---: |\n"
                        f"| Current (g) | "
                        f"{{{{ states('{ENTITY_ESP32DEV_CALIBRATED_G}') }}}} |\n"
                        f"| Gross | "
                        f"{{{{ states('{ENTITY_ESP32DEV_CALIBRATED_SENSOR}') }}}} |\n"
                        f"| Selected | "
                        f"{{{{ states('{ENTITY_ESP32DEV_SELECTED_INGREDIENT}') }}}} |\n"
                        "| Last recorded | "
                        "{{ states('input_text.esp32dev_last_recorded') }} |\n"
                    ),
                },
                {
                    "type": "entities",
                    "title": "Ingredient (NFC)",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_ESP32DEV_SELECTED_INGREDIENT,
                            "name": "Selected ingredient",
                        }
                    ],
                },
                {
                    "type": "entities",
                    "title": "Scale",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_ESP32DEV_CALIBRATED_G,
                            "name": "Current mass (g)",
                        },
                        {
                            "entity": ENTITY_ESP32DEV_CALIBRATED_SENSOR,
                            "name": "Calibrated sensor",
                        },
                        {"entity": ENTITY_ESP32DEV_TARE, "name": "Tare"},
                        {
                            "entity": ENTITY_ESP32DEV_LOCATION_TARE,
                            "name": "Location tare",
                        },
                        {
                            "entity": ENTITY_ESP32DEV_RECORD_WEIGHT,
                            "name": "Record weight",
                        },
                        {
                            "entity": ENTITY_ESP32DEV_LAST_RECORDED,
                            "name": "Last recorded (g)",
                        },
                    ],
                },
            ],
        }
