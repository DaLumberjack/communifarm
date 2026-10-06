"""Pure dashboard model builder (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any

from ..const import (
    CLIMATE_LAYOUT_IMAGE,
    DASHBOARD_TITLE,
    DASHBOARD_VIEW_BATCHES,
    DASHBOARD_VIEW_CLIMATE_LAYOUT,
    DASHBOARD_VIEW_CLIMATE_STATUS,
    DASHBOARD_VIEW_CULTURE,
    DASHBOARD_VIEW_HARVEST,
    DASHBOARD_VIEW_OVERVIEW,
    DASHBOARD_VIEW_POS,
    DASHBOARD_VIEW_PRODUCTION,
    DASHBOARD_VIEW_WEIGH,
    ENTITY_ACQUIRE_FORM,
    ENTITY_ACQUIRE_SOURCE,
    ENTITY_ACTIVE_CULTURE_ID,
    ENTITY_ACTIVE_INOCULUM,
    ENTITY_ALLOWLISTED_SWITCH,
    ENTITY_BATCH_LIST,
    ENTITY_BATCH_MILESTONES,
    ENTITY_BATCH_NFC_UID,
    ENTITY_BATCH_STAGE,
    ENTITY_BTN_ACQUIRE_CULTURE,
    ENTITY_BTN_COMPLETE_NEW_BATCH,
    ENTITY_BTN_COMPLETELY_MIXED,
    ENTITY_BTN_CREATE_VARIETY,
    ENTITY_BTN_DRY_WET_MIX,
    ENTITY_BTN_FIELD_CAPACITY,
    ENTITY_BTN_FINAL_HARVEST,
    ENTITY_BTN_HEAT_TREATED,
    ENTITY_BTN_INOCULATE,
    ENTITY_BTN_MOVE_FRUITING,
    ENTITY_BTN_MOVE_HARVEST,
    ENTITY_BTN_MOVE_INCUBATION,
    ENTITY_BTN_PRODUCTION_START,
    ENTITY_BTN_RECORD_HARVEST,
    ENTITY_BTN_RECORD_SALE,
    ENTITY_BTN_RECORD_SALE_CLEANUP,
    ENTITY_BTN_RETIRE_VARIETY,
    ENTITY_BTN_SELECT_INOCULUM_NFC,
    ENTITY_BTN_SEPARATE_CONTAINERS,
    ENTITY_BTN_SET_CULTURE_STATUS,
    ENTITY_BTN_SETTLING,
    ENTITY_BTN_STORED_COOLING,
    ENTITY_BTN_WATER_ADDED,
    ENTITY_CATALOG_VARIETY,
    ENTITY_CLIMATE_STATUS,
    ENTITY_CONTAINER_COUNT,
    ENTITY_CONTAINER_TYPE,
    ENTITY_CULTURE_INVENTORY,
    ENTITY_CULTURE_VESSEL_STATUS,
    ENTITY_HARVEST_MASS_G,
    ENTITY_HEAT_TREATMENT,
    ENTITY_HUMIDITY_TARGET,
    ENTITY_LC_STIR_PLATE,
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
    ENTITY_VARIETY_LIST,
    ENTITY_VARIETY_NAME,
    ENTITY_WEIGH_SESSION,
    ROLE_FAN,
    ROLE_HUMIDITY,
    ROLE_LC_STIR_PLATE,
    ROLE_SWITCH,
    ROLE_TEMPERATURE,
)
from ..domain.climate_layout import OverlayPoint, overlay_prefix
from ..domain.climate_units import UNIT_METRIC, gauge_bounds
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
    """Build Lovelace views from Communifarm state."""

    def build(
        self,
        state: CommunifarmState,
        resolved: dict[str, str | None],
        climate_points: list[OverlayPoint] | None = None,
        unit_system: str = UNIT_METRIC,
    ) -> dict[str, Any]:
        """Return a Lovelace dashboard config dict.

        resolved maps role -> current entity_id (may be None).
        climate_points are bound entities placed on the operator schematic.
        unit_system is Home Assistant's current choice, metric unless it is °F.
        """
        points = list(climate_points or [])
        self._unit_system = unit_system
        return {
            "title": DASHBOARD_TITLE,
            "views": [
                self._overview_view(state, resolved),
                self._climate_layout_view(points),
                self._climate_status_view(points),
                self._weigh_view(state),
                self._batches_view(state),
                self._culture_view(state),
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
                    "Floor plan? **Layout** · Gauges and fans? **Climate** · "
                    "Weighing? **Weigh** · Mix history? **Batches** · "
                    "Culture / varieties? **Culture** · "
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
                "type": "markdown",
                "title": "Climate",
                "content": (
                    "Rooms and tents. An indoor room with no sensor uses the parent "
                    "reading. Machines stay off when that reading is missing.\n\n"
                    "Setup places the sensors and machines drawn on the layout. "
                    "`bind_climate_role` swaps one of those for a real device.\n\n"
                    f"{{{{ state_attr('{ENTITY_CLIMATE_STATUS}', 'summary') }}}}"
                ),
            }
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

    def _culture_view(self, state: CommunifarmState) -> dict[str, Any]:
        """Variety catalog + one-UID-per-vessel culture inventory."""
        return {
            "path": DASHBOARD_VIEW_CULTURE,
            "title": "Culture",
            "icon": "mdi:flask",
            "cards": [
                {
                    "type": "markdown",
                    "title": "Culture / inoculum",
                    "content": (
                        f"Batch **{state.batch.name}**\n\n"
                        "Each LC jar / grain bag / vial is **one row** with a stable UID. "
                        "Display name is the **mushroom variety** "
                        "(Chestnut, Blue oyster, …).\n\n"
                        "Vessel states (LC & grain): "
                        "`colonizing` → `ready` → `drawing` → `exhausted` "
                        "(+ `contaminated` / `retired`).\n\n"
                        f"{{{{ state_attr('{ENTITY_VARIETY_LIST}', 'list_text') }}}}"
                    ),
                },
                {
                    "type": "entities",
                    "title": "Variety catalog",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_VARIETY_NAME,
                            "name": "New variety name",
                        },
                        {
                            "entity": ENTITY_BTN_CREATE_VARIETY,
                            "name": "Create variety",
                        },
                        {
                            "entity": ENTITY_CATALOG_VARIETY,
                            "name": "Catalog variety",
                        },
                        {
                            "entity": ENTITY_BTN_RETIRE_VARIETY,
                            "name": "Retire custom variety",
                        },
                    ],
                },
                {
                    "type": "entities",
                    "title": "Acquire vessel",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_CATALOG_VARIETY,
                            "name": "Variety",
                        },
                        {
                            "entity": ENTITY_ACQUIRE_FORM,
                            "name": "Form (LC / grain / …)",
                        },
                        {
                            "entity": ENTITY_ACQUIRE_SOURCE,
                            "name": "Source",
                        },
                        {
                            "entity": ENTITY_BTN_ACQUIRE_CULTURE,
                            "name": "Acquire culture vessel",
                        },
                    ],
                },
                {
                    "type": "entities",
                    "title": "Vessel status",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_ACTIVE_INOCULUM,
                            "name": "Active inoculum",
                        },
                        {
                            "entity": ENTITY_CULTURE_VESSEL_STATUS,
                            "name": "New status",
                        },
                        {
                            "entity": ENTITY_BTN_SET_CULTURE_STATUS,
                            "name": "Set culture vessel status",
                        },
                    ],
                },
                {
                    "type": "markdown",
                    "title": "Inventory",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_CULTURE_INVENTORY}', 'list_text') }}}}"
                    ),
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
                        "1. Register varieties / vessels on **Culture** tab, then pick "
                        "**Active inoculum** (variety · form · status · UID) or NFC scan\n"
                        "2. Set container type + substrate g → **Inoculate** → "
                        "incubation → fruiting → harvest\n"
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
                            "entity": ENTITY_ACTIVE_INOCULUM,
                            "name": "Active inoculum",
                        },
                        {
                            "entity": ENTITY_ACTIVE_CULTURE_ID,
                            "name": "Active culture id",
                        },
                        {
                            "entity": ENTITY_BTN_SELECT_INOCULUM_NFC,
                            "name": "Select inoculum from NFC",
                        },
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
                self._batch_harvest_entities_card(),
            ],
        }

    @staticmethod
    def _batch_harvest_entities_card() -> dict[str, Any]:
        """Shared batch harvest controls — Production and Harvest tabs stay in sync."""
        return {
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
        }

    def _harvest_view(self, state: CommunifarmState) -> dict[str, Any]:
        """Batch harvest (same entities as Production) + fridge SOP; NFC later."""
        return {
            "path": DASHBOARD_VIEW_HARVEST,
            "title": "Harvest",
            "icon": "mdi:basket-fill",
            "cards": [
                {
                    "type": "markdown",
                    "title": "Batch harvest",
                    "content": (
                        f"Batch **{state.batch.name}** (`{state.batch.id}`)\n\n"
                        "Same controls as **Production → Harvest** "
                        "(shared entities — pick/pack stays on this tab).\n\n"
                        "1. Batch must be **fruiting** or **harvesting** "
                        "(advance on **Production**)\n"
                        "2. Set **Harvest mass (g)**\n"
                        "3. **Record harvest (batch)** for a flush, or "
                        "**Final harvest (batch)** to complete\n\n"
                        f"{{{{ state_attr('{ENTITY_PRODUCTION_STATUS}', 'progress_text') }}}}"
                    ),
                },
                self._batch_harvest_entities_card(),
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
                        "`sale_pack` rows link to `harvest_id`; buyer/payment on **POS**.\n\n"
                        "Per-container NFC check-in stays available as services "
                        "(`check_in` / `record_container_harvest`); UI wiring later."
                    ),
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

    def _climate_layout_view(self, points: list[OverlayPoint]) -> dict[str, Any]:
        """Picture-elements floor plan. Unbound rooms stay as ink on the SVG."""
        elements: list[dict[str, Any]] = [
            self._overlay_element(point) for point in points
        ]
        if not elements:
            elements.append(
                {
                    "type": "state-label",
                    "entity": ENTITY_CLIMATE_STATUS,
                    "prefix": "Climate ",
                    "style": {
                        "left": "78%",
                        "top": "7%",
                        "transform": "translate(-50%, -50%)",
                        "color": "#e7f2f8",
                        "font-size": "12px",
                    },
                }
            )
        return {
            "title": "Layout",
            "path": DASHBOARD_VIEW_CLIMATE_LAYOUT,
            "icon": "mdi:floor-plan",
            "panel": True,
            "cards": [
                {
                    "type": "vertical-stack",
                    "cards": [
                        {
                            "type": "markdown",
                            "content": (
                                "Desktop floor plan. A phone layout comes later. "
                                "Room positions stay fixed until a layout editor exists."
                            ),
                        },
                        {
                            "type": "picture-elements",
                            "image": CLIMATE_LAYOUT_IMAGE,
                            "elements": elements,
                        },
                    ],
                }
            ],
        }

    def _climate_status_view(self, points: list[OverlayPoint]) -> dict[str, Any]:
        """Gauges, 24h history, and machine on/off. No card for an unbound role."""
        sensors = [point for point in points if point.is_sensor]
        machines = [point for point in points if not point.is_sensor]
        cards: list[dict[str, Any]] = [
            {
                "type": "markdown",
                "content": (
                    "## Climate status\n"
                    "- Yellow, then red, means the reading is above the target.\n"
                    "- A cold room still shows its number here.\n"
                    "- Indoor gauges sit close to the target.\n"
                    "- Outdoor gauges use a wider window.\n\n"
                    f"{{{{ state_attr('{ENTITY_CLIMATE_STATUS}', 'summary') }}}}"
                ),
            }
        ]
        if not points:
            cards.append(
                {
                    "type": "markdown",
                    "title": "Nothing bound yet",
                    "content": (
                        "The labeled sensors and machines are placed at setup. "
                        "`bind_climate_role` replaces one with hardware you already have. "
                        "Empty slots stay off this tab so you do not get a dead gauge."
                    ),
                }
            )
        if sensors:
            cards.append(
                {
                    "type": "history-graph",
                    "title": "Last 24 hours",
                    "hours_to_show": 24,
                    "entities": [point.entity_id for point in sensors],
                }
            )
        gauges = [card for point in sensors if (card := self._gauge_card(point))]
        for chunk in _chunks(gauges, 3):
            if len(chunk) == 1:
                cards.append(chunk[0])
            else:
                cards.append({"type": "horizontal-stack", "cards": chunk})
        if machines:
            cards.append(
                {
                    "type": "entities",
                    "title": "Machines",
                    "state_color": True,
                    "entities": [
                        {
                            "entity": point.entity_id,
                            "name": f"{point.node_name} {point.role.replace('_', ' ')}",
                        }
                        for point in machines
                    ],
                }
            )
        return {
            "title": "Climate",
            "path": DASHBOARD_VIEW_CLIMATE_STATUS,
            "icon": "mdi:gauge",
            "cards": cards,
        }

    @staticmethod
    def _overlay_element(point: OverlayPoint) -> dict[str, Any]:
        label = point.node_name
        short = point.role.replace("_", " ")
        if point.slot:
            short = f"{short} {point.slot + 1}"
        style: dict[str, Any] = {
            "left": point.left,
            "top": point.top,
            "transform": "translate(-50%, -50%)",
        }
        if point.is_sensor:
            style.update(
                {
                    "font-size": "13px",
                    "color": "#f4f7f5",
                    "background": "rgba(0,0,0,0.55)",
                    "padding": "0 2px",
                    "border-radius": "2px",
                    "line-height": "1.1",
                    "white-space": "nowrap",
                }
            )
            return {
                "type": "state-label",
                "entity": point.entity_id,
                "prefix": overlay_prefix(point),
                "style": style,
            }
        return {
            "type": "state-icon",
            "entity": point.entity_id,
            "title": f"{label} {short}",
            "style": style,
        }

    def _gauge_card(self, point: OverlayPoint) -> dict[str, Any] | None:
        bounds = gauge_bounds(
            kind=point.kind,
            role=point.role,
            temperature_target=point.temperature_target,
            humidity_target=point.humidity_target,
            co2_ppm_target=point.co2_ppm_target,
            system=self._unit_system,
        )
        if bounds is None:
            return None
        minimum, maximum, target, band = bounds
        card: dict[str, Any] = {
            "type": "gauge",
            "entity": point.entity_id,
            "name": f"{point.node_name} {point.role.replace('_', ' ')}",
            "min": round(minimum, 1),
            "max": round(maximum, 1),
            "needle": True,
        }
        severity = _gauge_severity(target, band, minimum, maximum)
        if severity is not None:
            card["severity"] = severity
        return card


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _gauge_severity(
    target: float | None, band: float, minimum: float, maximum: float
) -> dict[str, float] | None:
    """Yellow then red above the target. Home Assistant colors from the threshold up."""
    if target is None:
        return None
    yellow = float(target) + float(band)
    red = float(target) + max(float(band) * 3, float(band) + 1)
    if yellow >= maximum:
        yellow = maximum - 2
    red = min(maximum, red)
    if yellow >= red or yellow <= minimum:
        return None
    return {"green": minimum, "yellow": round(yellow, 1), "red": round(red, 1)}
