"""Pure dashboard model builder (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any

from ..const import (
    DASHBOARD_TITLE,
    DASHBOARD_VIEW_BATCHES,
    DASHBOARD_VIEW_HARVEST,
    DASHBOARD_VIEW_OVERVIEW,
    DASHBOARD_VIEW_POS,
    DASHBOARD_VIEW_PRODUCTION,
    DASHBOARD_VIEW_WEIGH,
    ENTITY_ALLOWLISTED_SWITCH,
    ENTITY_BATCH_LIST,
    ENTITY_BATCH_MILESTONES,
    ENTITY_BATCH_NFC_UID,
    ENTITY_BATCH_STAGE,
    ENTITY_BTN_COMPLETE_NEW_BATCH,
    ENTITY_BTN_COMPLETELY_MIXED,
    ENTITY_BTN_CONFIRM_CONTAINER_HARVEST,
    ENTITY_BTN_CONFIRM_FINAL_CONTAINER_HARVEST,
    ENTITY_BTN_DRY_WET_MIX,
    ENTITY_BTN_FIELD_CAPACITY,
    ENTITY_BTN_FINAL_HARVEST,
    ENTITY_BTN_HEAT_TREATED,
    ENTITY_BTN_INOCULATE,
    ENTITY_BTN_MOVE_FRUITING,
    ENTITY_BTN_MOVE_HARVEST,
    ENTITY_BTN_MOVE_INCUBATION,
    ENTITY_BTN_NFC_CHECKIN_HARVEST,
    ENTITY_BTN_PRODUCTION_START,
    ENTITY_BTN_RECORD_HARVEST,
    ENTITY_BTN_RECORD_SALE,
    ENTITY_BTN_RECORD_SALE_CLEANUP,
    ENTITY_BTN_SEPARATE_CONTAINERS,
    ENTITY_BTN_SETTLING,
    ENTITY_BTN_STORED_COOLING,
    ENTITY_BTN_WATER_ADDED,
    ENTITY_CONTAINER_COUNT,
    ENTITY_CONTAINER_TYPE,
    ENTITY_HARVEST_MASS_G,
    ENTITY_HEAT_TREATMENT,
    ENTITY_HUMIDITY_TARGET,
    ENTITY_LC_STIR_PLATE,
    ENTITY_NFC_CHECKIN,
    ENTITY_PAYMENT_METHOD,
    ENTITY_PRODUCTION_STATUS,
    ENTITY_RECIPE_SCALE,
    ENTITY_SALE_BUYER,
    ENTITY_SALE_LINE_AMOUNT,
    ENTITY_SALE_MASS_G,
    ENTITY_SALE_VENUE,
    ENTITY_SALES_STATUS,
    ENTITY_SUBSTRATE_G,
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
                self._production_view(state),
                self._harvest_view(state),
                self._pos_view(state),
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
                    "Weighing? **Weigh** · Mix history? **Batches** · "
                    "Inoculate? **Production** · Pick / fridge? **Harvest** · "
                    "Sell? **POS**."
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
                        "Complete mix process here. After cooling, use the "
                        "**Production** tab to inoculate culture into containers."
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
                            "name": "Production cycle start (legacy stub)",
                        },
                    ],
                },
            ],
        }

    def _production_view(self, state: CommunifarmState) -> dict[str, Any]:
        return {
            "title": "Production",
            "path": DASHBOARD_VIEW_PRODUCTION,
            "icon": "mdi:mushroom",
            "cards": [
                {
                    "type": "markdown",
                    "content": (
                        f"## Production\n"
                        f"Batch: **{state.batch.name}** (`{state.batch.id}`)\n\n"
                        "1. Acquire culture (service) → set container type + substrate g\n"
                        "2. **Inoculate** → incubation → fruiting → harvest\n"
                        "3. Final harvest completes the batch\n\n"
                        "**Placement:** call `ensure_placement_layout` once, then "
                        "`set_batch_location` / pass `zone_id` on inoculate/advance/harvest.\n"
                        "Culture/media: `set_culture_location`, `set_media_location`, "
                        "or optional `zone_id` on acquire/create/introduce.\n"
                        "Soft hints: inoculated/incubating → inoculation tent; "
                        "fruiting/harvesting → fruiting tent; pick → harvest fridge shelf; "
                        "culture storage → culture fridge; media prep → still-air cabinet.\n"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Status",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_PRODUCTION_STATUS}', 'progress_text') }}}}\n\n"
                        f"**Location:** "
                        f"{{{{ state_attr('{ENTITY_PRODUCTION_STATUS}', 'area_name') }}}} / "
                        f"{{{{ state_attr('{ENTITY_PRODUCTION_STATUS}', 'zone_name') }}}} "
                        f"(`{{{{ state_attr('{ENTITY_PRODUCTION_STATUS}', 'zone_id') }}}}`)"
                    ),
                },
                {
                    "type": "entities",
                    "title": "Inoculate inputs",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_CONTAINER_TYPE,
                            "name": "Container type",
                        },
                        {
                            "entity": ENTITY_CONTAINER_COUNT,
                            "name": "Container count",
                        },
                        {
                            "entity": ENTITY_SUBSTRATE_G,
                            "name": "Substrate g / container",
                        },
                        {
                            "entity": ENTITY_BTN_INOCULATE,
                            "name": "Inoculate batch",
                        },
                    ],
                },
                {
                    "type": "entities",
                    "title": "Lifecycle",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_BTN_MOVE_INCUBATION,
                            "name": "Move to incubation",
                        },
                        {
                            "entity": ENTITY_BTN_MOVE_FRUITING,
                            "name": "Move to fruiting",
                        },
                        {
                            "entity": ENTITY_BTN_MOVE_HARVEST,
                            "name": "Move to harvest",
                        },
                    ],
                },
                {
                    "type": "entities",
                    "title": "Harvest",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_HARVEST_MASS_G,
                            "name": "Harvest mass (g)",
                        },
                        {
                            "entity": ENTITY_BTN_RECORD_HARVEST,
                            "name": "Record harvest (batch)",
                        },
                        {
                            "entity": ENTITY_BTN_FINAL_HARVEST,
                            "name": "Final harvest (batch)",
                        },
                    ],
                },
            ],
        }

    def _harvest_view(self, state: CommunifarmState) -> dict[str, Any]:
        """Handheld NFC check-in + per-container harvest + fridge SOP."""
        return {
            "path": DASHBOARD_VIEW_HARVEST,
            "title": "Harvest",
            "icon": "mdi:basket-fill",
            "cards": [
                {
                    "type": "markdown",
                    "title": "Per-container harvest",
                    "content": (
                        f"Batch **{state.batch.name}** · NFC `{state.batch.nfc_uid}`\n\n"
                        "1. Scan the **block** with the handheld reader\n"
                        "2. Press **NFC check-in harvest**\n"
                        "3. Cut, weigh, enter mass\n"
                        "4. Press **Confirm container harvest** "
                        "(returns block to fruiting)\n"
                        "5. Repeat for ready containers\n\n"
                        f"{{{{ state_attr('{ENTITY_NFC_CHECKIN}', 'progress_text') }}}}"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Fridge / bagging (residential)",
                    "content": (
                        "| Step | Practice |\n"
                        "| --- | --- |\n"
                        "| After cut | Cool/dry — **do not wash** |\n"
                        "| Bag | Breathable paper / vented sale bag ASAP |\n"
                        "| Avoid | Sealed plastic (condensation pool) |\n"
                        "| Fridge | Main shelves, **not** crisper |\n"
                        "| Pack | Don't overpack; leave air gap |\n"
                        "| Target | Best quality 3–5 days |\n\n"
                        "`sale_pack` rows link to `harvest_id`; buyer/payment on **POS**."
                    ),
                },
                {
                    "type": "entities",
                    "title": "NFC + confirm",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_NFC_CHECKIN,
                            "name": "NFC check-in",
                        },
                        {
                            "entity": ENTITY_HARVEST_MASS_G,
                            "name": "Harvest mass (g)",
                        },
                        {
                            "entity": ENTITY_BTN_NFC_CHECKIN_HARVEST,
                            "name": "NFC check-in harvest",
                        },
                        {
                            "entity": ENTITY_BTN_CONFIRM_CONTAINER_HARVEST,
                            "name": "Confirm container harvest",
                        },
                        {
                            "entity": ENTITY_BTN_CONFIRM_FINAL_CONTAINER_HARVEST,
                            "name": "Confirm final container harvest",
                        },
                    ],
                },
            ],
        }

    def _pos_view(self, state: CommunifarmState) -> dict[str, Any]:
        """Point of sale — venue/buyer/payment + confirm; cleanup after return."""
        return {
            "path": DASHBOARD_VIEW_POS,
            "title": "POS",
            "icon": "mdi:point-of-sale",
            "cards": [
                {
                    "type": "markdown",
                    "title": "Point of sale",
                    "content": (
                        f"Batch **{state.batch.name}**\n\n"
                        "General sales tracking (not GAP). After payment:\n"
                        "1. Set venue, buyer, payment method\n"
                        "2. Enter mass (weigh-at-sale) **or** leave open packs "
                        "and Confirm uses the oldest open pack\n"
                        "3. Enter amount received\n"
                        "4. Press **Confirm sale**\n"
                        "5. At home: **Record sale cleanup**\n\n"
                        f"{{{{ state_attr('{ENTITY_SALES_STATUS}', 'progress_text') }}}}"
                    ),
                },
                {
                    "type": "entities",
                    "title": "Sale draft",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": ENTITY_SALE_VENUE, "name": "Venue"},
                        {"entity": ENTITY_SALE_BUYER, "name": "Buyer"},
                        {"entity": ENTITY_PAYMENT_METHOD, "name": "Payment"},
                        {"entity": ENTITY_SALE_MASS_G, "name": "Mass (g)"},
                        {
                            "entity": ENTITY_SALE_LINE_AMOUNT,
                            "name": "Amount received",
                        },
                        {
                            "entity": ENTITY_SALES_STATUS,
                            "name": "Sales status",
                        },
                    ],
                },
                {
                    "type": "entities",
                    "title": "Submit",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_BTN_RECORD_SALE,
                            "name": "Confirm sale",
                        },
                        {
                            "entity": ENTITY_BTN_RECORD_SALE_CLEANUP,
                            "name": "Record sale cleanup",
                        },
                    ],
                },
            ],
        }
