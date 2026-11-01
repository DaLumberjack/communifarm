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
    DASHBOARD_VIEW_MIX,
    DASHBOARD_VIEW_NFC_WRITE,
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
    ENTITY_BTN_APPLY_TAG_SOURCE,
    ENTITY_BTN_COMPLETE_NEW_BATCH,
    ENTITY_BTN_COMPLETELY_MIXED,
    ENTITY_BTN_CONFIRM_NFC_WRITE,
    ENTITY_BTN_CREATE_INVENTORY_LOT,
    ENTITY_BTN_CREATE_VARIETY,
    ENTITY_BTN_DRY_WET_MIX,
    ENTITY_BTN_DRYS_COMBINED,
    ENTITY_BTN_FIELD_CAPACITY,
    ENTITY_BTN_FINAL_HARVEST,
    ENTITY_BTN_HEAT_TREATED,
    ENTITY_BTN_IMPORT_NFC_FROM_ENTITY,
    ENTITY_BTN_INOCULATE,
    ENTITY_BTN_MIX_STEP_FROM_BADGE,
    ENTITY_BTN_MOVE_FRUITING,
    ENTITY_BTN_MOVE_HARVEST,
    ENTITY_BTN_MOVE_INCUBATION,
    ENTITY_BTN_PREPARE_NFC_WRITE,
    ENTITY_BTN_PRODUCTION_START,
    ENTITY_BTN_RECORD_HARVEST,
    ENTITY_BTN_RECORD_SALE,
    ENTITY_BTN_RECORD_SALE_CLEANUP,
    ENTITY_BTN_RECORD_WATER_POUR,
    ENTITY_BTN_REGISTER_PRODUCTION_BLOCK,
    ENTITY_BTN_RELOCATE_STERILE,
    ENTITY_BTN_REMAINING_WATER,
    ENTITY_BTN_RETIRE_VARIETY,
    ENTITY_BTN_SEED_SHIPMENT_TAGS,
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
    ENTITY_FIELD_CAPACITY,
    ENTITY_HARVEST_MASS_G,
    ENTITY_HEAT_TREATMENT,
    ENTITY_HUMIDITY_TARGET,
    ENTITY_INTAKE_AMOUNT,
    ENTITY_INTAKE_AMOUNT_UNIT,
    ENTITY_INTAKE_COST,
    ENTITY_INTAKE_EMPLOYEE_LABEL,
    ENTITY_INTAKE_MACHINE_LABEL,
    ENTITY_INTAKE_PAYMENT,
    ENTITY_INTAKE_PROCESS_MODE,
    ENTITY_INTAKE_PURCHASE_DATE,
    ENTITY_INTAKE_PURCHASE_LOCATION,
    ENTITY_INTAKE_RECEIPT,
    ENTITY_INTAKE_TAG_UID,
    ENTITY_INTAKE_TRACKED,
    ENTITY_INTAKE_ZONE,
    ENTITY_LC_STIR_PLATE,
    ENTITY_MANUAL_WEIGH_G,
    ENTITY_MIX_PROTOCOL,
    ENTITY_NFC_SCAN_MODE,
    ENTITY_NFC_WRITE_LABEL,
    ENTITY_NFC_WRITE_OBJECT_TYPE,
    ENTITY_NFC_WRITE_STATUS,
    ENTITY_PAYMENT_METHOD,
    ENTITY_PLACEMENT_COLD_STORAGE,
    ENTITY_PLACEMENT_FRUITING_TENT,
    ENTITY_PLACEMENT_INOCULATION_TENT,
    ENTITY_PLACEMENT_STORAGE,
    ENTITY_PRODUCTION_STATUS,
    ENTITY_RECIPE_SCALE,
    ENTITY_RELOCATE_ZONE,
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
                self._mix_view(state),
                self._nfc_write_view(state),
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
                    "Batch mixing? **Mix** · Tagging / purchases? **Intake** · "
                    "History? **Batches** · "
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
        """Legacy path — mixing lives on Mix."""
        return {
            "title": "Weigh",
            "path": DASHBOARD_VIEW_WEIGH,
            "icon": "mdi:scale-balance",
            "cards": [
                {
                    "type": "markdown",
                    "content": (
                        f"## Moved to **Mix**\n"
                        f"Batch: **{state.batch.name}** ({state.batch.stage})\n\n"
                        "The standalone mixing process (drys → wets → field capacity "
                        "→ bag → sterilize) is on the **Mix** tab: "
                        "`/communifarm/mix`.\n"
                    ),
                },
            ],
        }

    def _mix_view(self, state: CommunifarmState) -> dict[str, Any]:
        """Standalone mix process: focus → drys → wets → finish."""
        return {
            "title": "Mix",
            "path": DASHBOARD_VIEW_MIX,
            "icon": "mdi:blender",
            "cards": [
                {
                    "type": "markdown",
                    "content": (
                        f"## Mixing batch\n"
                        f"Batch: **{state.batch.name}** ({state.batch.stage})\n"
                        f"Batch NFC: `{state.batch.nfc_uid}`\n\n"
                        "Scroll top → bottom: **drys**, then **wets**, then "
                        "**finish** when field capacity is met.\n"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Focus — now / last / next",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_MIX_PROTOCOL}', 'focus_text') }}}}"
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
                            "entity": ENTITY_MIX_PROTOCOL,
                            "name": "Mix protocol",
                        },
                    ],
                },
                {
                    "type": "entities",
                    "title": "NFC / badge (sandbox)",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_INTAKE_TAG_UID,
                            "name": "Tag source",
                        },
                        {
                            "entity": ENTITY_BTN_APPLY_TAG_SOURCE,
                            "name": "Scan NFC tag",
                        },
                        {
                            "entity": ENTITY_BTN_MIX_STEP_FROM_BADGE,
                            "name": "Badge: complete next checkpoint",
                        },
                    ],
                },
                {
                    "type": "markdown",
                    "content": (
                        "Last step (**relocate**): pick **Storage** shelf → "
                        "**Relocate for sterilization** (bags land in Storage "
                        "awaiting culture) — not the badge button.\n"
                        "Earlier checkpoints: Tag source → `nfc-employee-01` → "
                        "Scan NFC tag → Badge."
                    ),
                },
                # --- DRY SECTION ---
                {
                    "type": "markdown",
                    "content": (
                        "## 1 · Dry ingredients\n"
                        "Scan NFC or pick ingredient → Tare → add → **Record weight**.\n"
                        "After tare the scale reads **0** until mass is added. "
                        "Broken scale / sandbox: set **Manual weigh (g)** "
                        "(−1 = use scale, 0 = not in recipe)."
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Dry progress",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_WEIGH_SESSION}', 'dry_progress_text') }}}}"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Live reading",
                    "content": (
                        "| | |\n"
                        "| --- | ---: |\n"
                        f"| Effective (g) | "
                        f"{{{{ state_attr('{ENTITY_WEIGH_SESSION}', 'effective_mass_g') }}}} |\n"
                        f"| Source | "
                        f"{{{{ state_attr('{ENTITY_WEIGH_SESSION}', 'mass_source') }}}} |\n"
                        f"| Scale (g) | "
                        f"{{{{ states('{ENTITY_ESP32DEV_CALIBRATED_G}') }}}} |\n"
                        f"| Manual (g) | "
                        f"{{{{ states('{ENTITY_MANUAL_WEIGH_G}') }}}} |\n"
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
                    "title": "Scale (drys)",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_ESP32DEV_CALIBRATED_G,
                            "name": "Scale mass (g)",
                        },
                        {
                            "entity": ENTITY_MANUAL_WEIGH_G,
                            "name": "Manual weigh (g) (−1 = scale)",
                        },
                        {
                            "entity": ENTITY_ESP32DEV_CALIBRATED_SENSOR,
                            "name": "Calibrated sensor",
                        },
                        {"entity": ENTITY_ESP32DEV_TARE, "name": "Tare"},
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
                {
                    "type": "entities",
                    "title": "Dry checkpoint",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_BTN_DRYS_COMBINED,
                            "name": "Mix all drys together",
                        },
                    ],
                },
                # --- WET SECTION ---
                {
                    "type": "markdown",
                    "content": (
                        "## 2 · Water / wets\n"
                        "Water target **10200 g** (pours sum). "
                        "**Location tare** the mix vessel → add pour → "
                        "**Record water pour**. Then incorporate / remaining / "
                        "field capacity."
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Water progress",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_WEIGH_SESSION}', 'wet_progress_text') }}}}"
                    ),
                },
                {
                    "type": "entities",
                    "title": "Scale (water pours)",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_ESP32DEV_CALIBRATED_G,
                            "name": "Scale mass (g)",
                        },
                        {
                            "entity": ENTITY_MANUAL_WEIGH_G,
                            "name": "Manual weigh (g) (−1 = scale)",
                        },
                        {
                            "entity": ENTITY_ESP32DEV_LOCATION_TARE,
                            "name": "Location tare (mix vessel)",
                        },
                        {
                            "entity": ENTITY_ESP32DEV_SELECTED_INGREDIENT,
                            "name": "Water type (optional)",
                        },
                        {
                            "entity": ENTITY_BTN_RECORD_WATER_POUR,
                            "name": "Record water pour",
                        },
                    ],
                },
                {
                    "type": "entities",
                    "title": "Wet checkpoints",
                    "show_header_toggle": False,
                    "entities": [
                        {
                            "entity": ENTITY_BTN_WATER_ADDED,
                            "name": "First water pour done",
                        },
                        {
                            "entity": ENTITY_BTN_DRY_WET_MIX,
                            "name": "Incorporate",
                        },
                        {
                            "entity": ENTITY_BTN_REMAINING_WATER,
                            "name": "Remaining water done",
                        },
                        {
                            "entity": ENTITY_BTN_SETTLING,
                            "name": "Incorporate remaining",
                        },
                        {
                            "entity": ENTITY_FIELD_CAPACITY,
                            "name": "Field capacity reading",
                        },
                        {
                            "entity": ENTITY_BTN_FIELD_CAPACITY,
                            "name": "Reached field capacity",
                        },
                    ],
                },
                # --- FINISH SECTION ---
                {
                    "type": "markdown",
                    "content": (
                        "## 3 · Finish\n"
                        "Completely mixed → bag/bin → scan **at least one** "
                        "bag/bin NFC → **Relocate for sterilization** "
                        "(documents the whole batch moved)."
                    ),
                },
                {
                    "type": "entities",
                    "title": "Finish checkpoints",
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
                            "name": "Bag / bin",
                        },
                        {
                            "entity": ENTITY_RELOCATE_ZONE,
                            "name": "Sterilization-ready location",
                        },
                        {
                            "entity": ENTITY_BTN_RELOCATE_STERILE,
                            "name": "Relocate for sterilization",
                        },
                    ],
                },
                {
                    "type": "markdown",
                    "content": (
                        "### Relocate\n"
                        "1. Pick **Sterilization-ready location**.\n"
                        "2. Optional: scan a bag/bin (or leave blank to use the "
                        "active **batch NFC**).\n"
                        "3. Press **Relocate for sterilization** — documents the "
                        "whole batch moved.\n"
                        "To tag bags first: **Intake** → scan mode "
                        "`register_production_block` or Bag/bin write section."
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Full checklist",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_MIX_PROTOCOL}', 'progress_text') }}}}"
                    ),
                },
            ],
        }

    def _nfc_write_view(self, state: CommunifarmState) -> dict[str, Any]:
        """Intake: same entities; process mode toggles which card groups show."""

        def _when_process(*modes: str) -> dict[str, Any]:
            return {
                "condition": "or",
                "conditions": [
                    {
                        "condition": "state",
                        "entity": ENTITY_INTAKE_PROCESS_MODE,
                        "state": mode,
                    }
                    for mode in modes
                ],
            }

        process_picker = {
            "type": "entities",
            "title": "Process",
            "show_header_toggle": False,
            "entities": [
                {
                    "entity": ENTITY_INTAKE_PROCESS_MODE,
                    "name": (
                        "Mode — combined (bootstrap) / mark_tags / purchase_intake"
                    ),
                },
            ],
        }
        header = {
            "type": "markdown",
            "content": (
                f"## Intake\n"
                f"Site: **{state.site.name}** · Batch: **{state.batch.name}**\n\n"
                "SQLite is source of truth after bind. NDEF seeds identity on write.\n"
                "Use **Process** mode to focus mark-tags vs purchase without leaving "
                "this page (`combined` keeps both for fast kit bootstrap)."
            ),
        }
        banner_combined = {
            "type": "conditional",
            "conditions": [
                {
                    "condition": "state",
                    "entity": ENTITY_INTAKE_PROCESS_MODE,
                    "state": "combined",
                }
            ],
            "card": {
                "type": "markdown",
                "content": (
                    "### Process: **combined** (bootstrap)\n"
                    "Shipment pool, NFC marking, and purchase intake on one page."
                ),
            },
        }
        banner_mark = {
            "type": "conditional",
            "conditions": [
                {
                    "condition": "state",
                    "entity": ENTITY_INTAKE_PROCESS_MODE,
                    "state": "mark_tags",
                }
            ],
            "card": {
                "type": "markdown",
                "content": (
                    "### Process: **mark tags**\n"
                    "Bind physical chips (employee / location / bag / machine). "
                    "Purchase fields are hidden."
                ),
            },
        }
        banner_purchase = {
            "type": "conditional",
            "conditions": [
                {
                    "condition": "state",
                    "entity": ENTITY_INTAKE_PROCESS_MODE,
                    "state": "purchase_intake",
                }
            ],
            "card": {
                "type": "markdown",
                "content": (
                    "### Process: **purchase intake**\n"
                    "Create inventory lots from purchases. NFC write chrome is hidden "
                    "unless you switch back to mark_tags or combined."
                ),
            },
        }
        mark_cards = [
            {
                "type": "entities",
                "title": "Shipment / tag pool",
                "show_header_toggle": False,
                "entities": [
                    {
                        "entity": ENTITY_BTN_SEED_SHIPMENT_TAGS,
                        "name": "Seed kit NFC tags into Communifarm DB",
                    },
                    {
                        "entity": ENTITY_BTN_IMPORT_NFC_FROM_ENTITY,
                        "name": "Import UID from existing last-scan entity",
                    },
                    {
                        "entity": ENTITY_INTAKE_TAG_UID,
                        "name": "Tag source (last scanned or DB chip)",
                    },
                ],
            },
            {
                "type": "entities",
                "title": "Scanner mode",
                "show_header_toggle": False,
                "entities": [
                    {
                        "entity": ENTITY_NFC_SCAN_MODE,
                        "name": "Scan mode (register_production_block binds next UID)",
                    },
                    {
                        "entity": ENTITY_BTN_REGISTER_PRODUCTION_BLOCK,
                        "name": "Register tag source as production block",
                    },
                    {
                        "entity": ENTITY_CONTAINER_TYPE,
                        "name": "Container type for new blocks",
                    },
                    {
                        "entity": ENTITY_INTAKE_ZONE,
                        "name": "Default place location",
                    },
                ],
            },
            {
                "type": "markdown",
                "content": (
                    "## Location tag\n"
                    "Pick zone → set tag type `location` → prepare → write → confirm."
                ),
            },
            {
                "type": "entities",
                "title": "Location write",
                "show_header_toggle": False,
                "entities": [
                    {"entity": ENTITY_INTAKE_ZONE, "name": "Zone to tag"},
                    {
                        "entity": ENTITY_NFC_WRITE_OBJECT_TYPE,
                        "name": "Tag type (use location)",
                    },
                ],
            },
            {
                "type": "markdown",
                "content": (
                    "## Bag / bin (production block)\n"
                    "Scan mode `register_production_block`, or tag type `container`."
                ),
            },
            {
                "type": "entities",
                "title": "Bag / bin write",
                "show_header_toggle": False,
                "entities": [
                    {
                        "entity": ENTITY_NFC_WRITE_OBJECT_TYPE,
                        "name": "Tag type (use container)",
                    },
                    {
                        "entity": ENTITY_CONTAINER_TYPE,
                        "name": "Bag / block / tub…",
                    },
                    {
                        "entity": ENTITY_INTAKE_ZONE,
                        "name": "Place at (optional)",
                    },
                ],
            },
            {
                "type": "markdown",
                "content": (
                    "## Machine / batch / culture / employee\n"
                    "Set tag type accordingly. Culture uses **Active inoculum**."
                ),
            },
            {
                "type": "entities",
                "title": "Other write targets",
                "show_header_toggle": False,
                "entities": [
                    {
                        "entity": ENTITY_INTAKE_MACHINE_LABEL,
                        "name": "Machine label",
                    },
                    {
                        "entity": ENTITY_ACTIVE_INOCULUM,
                        "name": "Active culture (for culture tags)",
                    },
                    {
                        "entity": ENTITY_INTAKE_EMPLOYEE_LABEL,
                        "name": "Employee badge label",
                    },
                ],
            },
            {
                "type": "entities",
                "title": "Write actions",
                "show_header_toggle": False,
                "entities": [
                    {
                        "entity": ENTITY_BTN_PREPARE_NFC_WRITE,
                        "name": "Prepare NDEF write",
                    },
                    {
                        "entity": ENTITY_BTN_CONFIRM_NFC_WRITE,
                        "name": "Confirm write (bind chip UID)",
                    },
                    {
                        "entity": ENTITY_NFC_WRITE_STATUS,
                        "name": "Write status",
                    },
                ],
            },
            {
                "type": "markdown",
                "title": "Pending NDEF",
                "content": (
                    f"{{{{ state_attr('{ENTITY_NFC_WRITE_STATUS}', 'progress_text') }}}}"
                ),
            },
        ]
        purchase_cards = [
            {
                "type": "markdown",
                "content": (
                    "## Asset / inventory purchase\n"
                    "Type + purchase row → create lot. Mark the chip in "
                    "**mark_tags** or **combined** when ready."
                ),
            },
            {
                "type": "entities",
                "title": "Asset purchase",
                "show_header_toggle": False,
                "entities": [
                    {
                        "entity": ENTITY_NFC_WRITE_OBJECT_TYPE,
                        "name": "Tag type (use inventory)",
                    },
                    {
                        "entity": ENTITY_NFC_WRITE_LABEL,
                        "name": "Asset / ingredient",
                    },
                    {"entity": ENTITY_INTAKE_AMOUNT, "name": "Amount"},
                    {"entity": ENTITY_INTAKE_AMOUNT_UNIT, "name": "Unit"},
                    {"entity": ENTITY_INTAKE_COST, "name": "Cost"},
                    {
                        "entity": ENTITY_INTAKE_PAYMENT,
                        "name": "Payment (account / cash)",
                    },
                    {
                        "entity": ENTITY_INTAKE_PURCHASE_LOCATION,
                        "name": "Purchase location",
                    },
                    {"entity": ENTITY_INTAKE_TRACKED, "name": "Tracked"},
                    {
                        "entity": ENTITY_INTAKE_RECEIPT,
                        "name": "Receipt tracked",
                    },
                    {
                        "entity": ENTITY_INTAKE_PURCHASE_DATE,
                        "name": "Purchase date",
                    },
                    {
                        "entity": ENTITY_BTN_CREATE_INVENTORY_LOT,
                        "name": "Create inventory lot (new UUID)",
                    },
                ],
            },
        ]
        cards: list[dict[str, Any]] = [
            header,
            process_picker,
            banner_combined,
            banner_mark,
            banner_purchase,
        ]
        for card in mark_cards:
            cards.append(
                {
                    "type": "conditional",
                    "conditions": [_when_process("combined", "mark_tags")],
                    "card": card,
                }
            )
        for card in purchase_cards:
            cards.append(
                {
                    "type": "conditional",
                    "conditions": [_when_process("combined", "purchase_intake")],
                    "card": card,
                }
            )
        return {
            "title": "Intake",
            "path": DASHBOARD_VIEW_NFC_WRITE,
            "icon": "mdi:clipboard-text",
            "cards": cards,
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
                        "History and heat/cooling. Live mix protocol is on **Mix**."
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
                        "1. After Mix **Relocate**, bags appear under **Storage** "
                        "(awaiting culture)\n"
                        "2. Culture tab → **Active inoculum** → **Inoculate**\n"
                        "3. Lifecycle moves: optional bag NFC (Tag source) moves "
                        "that bag; no scan moves the whole active batch\n"
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
                    "type": "markdown",
                    "title": "Storage",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_PLACEMENT_STORAGE}', 'progress_text') }}}}"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Cold storage",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_PLACEMENT_COLD_STORAGE}', 'progress_text') }}}}"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Fruiting tent",
                    "content": (
                        f"{{{{ state_attr('{ENTITY_PLACEMENT_FRUITING_TENT}', 'progress_text') }}}}"
                    ),
                },
                {
                    "type": "markdown",
                    "title": "Inoculation tent",
                    "content": (
                        "{{ state_attr('"
                        f"{ENTITY_PLACEMENT_INOCULATION_TENT}"
                        "', 'progress_text') }}"
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
                            "entity": ENTITY_INTAKE_TAG_UID,
                            "name": "Tag source (optional bag for moves)",
                        },
                        {
                            "entity": ENTITY_BTN_APPLY_TAG_SOURCE,
                            "name": "Scan NFC tag",
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
