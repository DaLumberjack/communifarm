"""Pure dashboard model builder (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any

from ..const import (
    DASHBOARD_TITLE,
    DASHBOARD_VIEW_BATCHES,
    DASHBOARD_VIEW_OVERVIEW,
    DASHBOARD_VIEW_WEIGH,
    ENTITY_ALLOWLISTED_SWITCH,
    ENTITY_BATCH_LIST,
    ENTITY_BATCH_MILESTONES,
    ENTITY_BATCH_NFC_UID,
    ENTITY_BATCH_STAGE,
    ENTITY_BTN_COMPLETE_NEW_BATCH,
    ENTITY_BTN_COMPLETELY_MIXED,
    ENTITY_BTN_DRY_WET_MIX,
    ENTITY_BTN_FIELD_CAPACITY,
    ENTITY_BTN_HEAT_TREATED,
    ENTITY_BTN_PRODUCTION_START,
    ENTITY_BTN_SEPARATE_CONTAINERS,
    ENTITY_BTN_SETTLING,
    ENTITY_BTN_STORED_COOLING,
    ENTITY_BTN_WATER_ADDED,
    ENTITY_CONTAINER_COUNT,
    ENTITY_HEAT_TREATMENT,
    ENTITY_HUMIDITY_TARGET,
    ENTITY_LC_STIR_PLATE,
    ENTITY_RECIPE_SCALE,
    ENTITY_TEMPERATURE_TARGET,
    ENTITY_WEIGH_SESSION,
    ROLE_FAN,
    ROLE_HUMIDITY,
    ROLE_LC_STIR_PLATE,
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
                self._batches_view(state),
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
                    f"Batch: **{state.batch.name}** ({state.batch.stage})\n\n"
                    "Weighing? **Weigh** tab · Batch history? **Batches** tab."
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
                    "Values update live when you change the Targets controls.\n"
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
        if resolved.get(ROLE_LC_STIR_PLATE):
            control_entities.append(ENTITY_LC_STIR_PLATE)
        if resolved.get(ROLE_FAN):
            control_entities.append(resolved[ROLE_FAN])  # type: ignore[arg-type]
        if not control_entities:
            actuator_entities = [
                entity_id
                for role in (ROLE_FAN, ROLE_SWITCH, ROLE_LC_STIR_PLATE)
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
                "entities": [ENTITY_BATCH_STAGE, ENTITY_BATCH_NFC_UID],
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
                        "First recorded ingredient **auto-starts dry mixing**.\n"
                        "1. Set recipe scale if needed\n"
                        "2. Scan NFC (or pick ingredient)\n"
                        "3. Tare → add material → Record\n"
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
                    "type": "entities",
                    "title": "Mix milestones (weigh)",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": ENTITY_BTN_WATER_ADDED, "name": "Added water"},
                        {
                            "entity": ENTITY_BTN_DRY_WET_MIX,
                            "name": "Started dry/wet mix",
                        },
                        {"entity": ENTITY_BTN_SETTLING, "name": "Settling"},
                        {
                            "entity": ENTITY_BTN_FIELD_CAPACITY,
                            "name": "Reached field capacity",
                        },
                    ],
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

    def _batches_view(self, state: CommunifarmState) -> dict[str, Any]:
        return {
            "title": "Batches",
            "path": DASHBOARD_VIEW_BATCHES,
            "icon": "mdi:basket-fill",
            "cards": [
                {
                    "type": "markdown",
                    "content": (
                        f"## Batches\n"
                        f"Active: **{state.batch.name}** (`{state.batch.id}`)\n\n"
                        "Complete the current mix batch and start a new NFC UID when ready."
                    ),
                },
                {
                    "type": "entities",
                    "title": "Active batch",
                    "show_header_toggle": False,
                    "entities": [
                        ENTITY_BATCH_STAGE,
                        ENTITY_BATCH_NFC_UID,
                        {
                            "entity": ENTITY_BTN_COMPLETE_NEW_BATCH,
                            "name": "Complete batch & start new",
                        },
                    ],
                },
                {
                    "type": "markdown",
                    "title": "Batch list",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_BATCH_LIST}', 'list_text') }}}}"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Active milestones",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_BATCH_MILESTONES}', 'progress_text') }}}}"
                    ),
                },
                {
                    "type": "entities",
                    "title": "Post-weigh process",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_BTN_COMPLETELY_MIXED,
                            "name": "Completely mixed",
                        },
                        {
                            "entity": ENTITY_CONTAINER_COUNT,
                            "name": "Container count",
                        },
                        {
                            "entity": ENTITY_BTN_SEPARATE_CONTAINERS,
                            "name": "Separated into containers",
                        },
                        {
                            "entity": ENTITY_HEAT_TREATMENT,
                            "name": "Sterilize / pasteurize",
                        },
                        {
                            "entity": ENTITY_BTN_HEAT_TREATED,
                            "name": "Record heat treatment",
                        },
                        {
                            "entity": ENTITY_BTN_STORED_COOLING,
                            "name": "Stored for cooling",
                        },
                        {
                            "entity": ENTITY_BTN_PRODUCTION_START,
                            "name": "Production cycle start (stub)",
                        },
                    ],
                },
            ],
        }
