# domain

## Purpose

Pure domain models and process rules — no Home Assistant imports.

## How to use this directory

- Open when changing process rules, bounds, NFC dual-write contract, or batch/inventory math.
- Keep pure: no `hass`, entity IDs, or service-call syntax.
- Pair with `../storage/` for persistence and `*_actions.py` adapters for HA wiring.
- Skill: architecture + testing; NFC → nfc-database.

## Map

| path | layer | how / why |
|------|-------|-----------|
| `__init__.py` | `domain` | Communifarm domain package. — Edit for pure process/rules; add T0 tests; no HA imports. |
| `batch_milestones.py` | `domain` | Batch mix / process milestone types (pure domain). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `climate.py` | `domain` | Climate tree: parent rooms, child tents, optional sensors (no Home Assistant). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `climate_control.py` | `domain` | Pure climate decisions. No Home Assistant imports and no GPIO. — Edit for pure process/rules; add T0 tests; no HA imports. |
| `climate_drawing.py` | `domain` | Sensors and machines inked on the operator schematic. The drawing labels outdoor T, RH, and P, the general-room AC, heater, fresh-air intake — Edit for pure process/rules; add T0 tests; no HA imports. |
| `climate_layout.py` | `domain` | Fixed operator floor plan for picture-elements overlays. Coordinates are a schematic of one site, not a scale drawing. A later editor can re — Edit for pure process/rules; add T0 tests; no HA imports. |
| `climate_units.py` | `domain` | Authored metric and imperial ranges for gauges. Control math stays in Celsius. Lovelace gauge min/max are whatever unit Home Assistant is di — Edit for pure process/rules; add T0 tests; no HA imports. |
| `container.py` | `domain` | Per-container production units (blocks/tubs/bags) under a batch. — Edit for pure process/rules; add T0 tests; no HA imports. |
| `culture.py` | `domain` | Culture lots + media prep (pure domain, no Home Assistant). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `inventory.py` | `domain` | Inventory lots and NDEF identity payloads (stable refs; SQLite is source of truth). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `location.py` | `domain` | Placement areas and zones (pure domain — data-driven area kinds). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `mix_protocol.py` | `domain` | Ordered mix-batch protocol checklist (pure domain). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `models.py` | `domain` | Pure domain models for Communifarm (no Home Assistant imports). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `nfc.py` | `domain` | NFC resolve / check-in (tag holds stable ID only; SQLite is source of truth). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `nfc_bind.py` | `domain` | Dual-write contract: entity ``nfc_uid`` + ``nfc_tag_pool`` registry. Physical tags may seed identity on first bind (NDEF / chip). After that — Edit for pure process/rules; add T0 tests; no HA imports. |
| `ops_schedule.py` | `domain` | Ops scheduling: projected next moves and priority alarms (pure domain). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `placement_inventory.py` | `domain` | Production placement inventory — bags/boxes by area kind (pure domain). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `production.py` | `domain` | Production inoculate / incubate / fruit / harvest (pure domain). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `README.md` | `domain` | This directory map (dim1 Map + dim2 Feature index). |
| `recipe.py` | `domain` | Default recipes and weigh-session progress (pure domain). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `sale.py` | `domain` | Point-of-sale domain models (general tracking — not GAP/accounting compliance). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `shipment_tags.py` | `domain` | All-in-one shipment NFC pack — known chip UIDs Communifarm ships with. These are stable physical-tag identities (not HA entity IDs). Seeding — Edit for pure process/rules; add T0 tests; no HA imports. |
| `tachometer.py` | `domain` | Manual fan tachometer / air-exchange vent measurements. — Edit for pure process/rules; add T0 tests; no HA imports. |
| `validation.py` | `domain` | Human-usable bounds and sensor-validity assessment (pure domain). — Edit for pure process/rules; add T0 tests; no HA imports. |
| `weight.py` | `domain` | Weight / material process events (pure domain, no Home Assistant). — Edit for pure process/rules; add T0 tests; no HA imports. |

## Feature index

| keywords / features | path |
|---------------------|------|
| domain, init | `__init__.py` |
| batch milestones, domain, MILESTONE_DRY_MIXING_STARTED, MILESTONE_DRYS_COMBINED, MILESTONE_WATER_ADDED, MILESTONE_DRY_WET_MIX_STARTED, MILESTONE_REMAINING_WATER_ADDED, MILESTONE_SETTLING_STARTED, MILESTONE_FIELD_CAPACITY_REACHED, MILESTONE_COMPLETELY_MIXED, MILESTONE_CONTAINERS_SEPARATED, MILESTONE_RELOCATED_FOR_STERILIZATION | `batch_milestones.py` |
| climate, domain, ENCLOSURE_INDOOR, ENCLOSURE_OUTDOOR, ENCLOSURES, SOURCE_LOCAL, SOURCE_INHERITED, SOURCE_NONE, KIND_OUTDOOR, KIND_GENERAL_ROOM, KIND_CULTURE_PREP, KIND_INOCULATION | `climate.py` |
| climate control, domain, ObservedState, ControlIntent, ControlDecision, light_should_be_on, decide_control, format_decision_summary, climate, control | `climate_control.py` |
| climate drawing, domain, PLATFORM_SENSOR, PLATFORM_SWITCH, PLATFORM_BINARY_SENSOR, DOT_KINDS, DOT_SLOTS, DrawingDevice, drawing_devices, drawing_object_id, drawing_entity_id, drawing_name | `climate_drawing.py` |
| climate layout, domain, VIEW_W, VIEW_H, SENSOR_ROLES, ACTUATOR_ROLES, ROLE_LABEL, RoomFrame, OverlayPoint, room_frames, percent_left, percent_top | `climate_layout.py` |
| climate units, domain, UNIT_METRIC, UNIT_US, UnitPair, pick, unit_system_for_temperature_symbol, PRESET_TEMPERATURE, INDOOR_TEMP_HALF, OUTDOOR_TEMP_MIN, OUTDOOR_TEMP_MAX, TEMP_DEADBAND | `climate_units.py` |
| container, domain, CONTAINER_STATUS_ACTIVE, CONTAINER_STATUS_COMPLETE, ProductionContainer, SalePack, build_containers_for_inoculate, apply_container_harvest, require_confirm, validate_sale_pack_mass, rebind_container_nfc, batch | `container.py` |
| culture, domain, SOURCE_WILD, SOURCE_ACQUAINTANCE, SOURCE_PURCHASED, SOURCE_TYPES, FORM_LIQUID_CULTURE, FORM_AGAR, FORM_SPORES, FORM_GRAIN_SPAWN, CULTURE_FORMS, VESSEL_FORMS | `culture.py` |
| inventory, domain, OBJECT_INVENTORY, OBJECT_EMPLOYEE, OBJECT_LOCATION, OBJECT_CONTAINER, OBJECT_BATCH, OBJECT_CULTURE, OBJECT_MACHINE, NFC_WRITE_OBJECT_TYPES, SCAN_MODE_NORMAL, SCAN_MODE_REGISTER_BLOCK | `inventory.py` |
| location, domain, SLOT_LEVEL, SLOT_SHELF, SLOT_GRID, SLOT_KINDS, AREA_FRUITING_TENT, AREA_INOCULATION_TENT, AREA_CULTURE_LAB, AREA_STORAGE, AREA_COLD_STORAGE, AREA_GENERAL_ENV | `location.py` |
| mix protocol, domain, MIX_PROTOCOL_STEPS, MixProtocolStep, DRY_SECTION_KEYS, WET_SECTION_KEYS, FINISH_SECTION_KEYS, MixProtocolProgress, dry_recipe_line_count, build_mix_protocol_progress, next_open_milestone, mix | `mix_protocol.py` |
| models, domain, new_id, Site, Environment, EntityBinding, EnvironmentalProfile, ProcessEvent, ProductionBatch, CommunifarmState, suggest_role_from_entity | `models.py` |
| nfc, domain, OBJECT_CONTAINER, OBJECT_BATCH, OBJECT_CULTURE, OBJECT_MEDIA, OBJECT_INVENTORY, OBJECT_EMPLOYEE, OBJECT_LOCATION, OBJECT_MACHINE, OBJECT_UNKNOWN, NFC_OBJECT_TYPES | `nfc.py` |
| nfc bind, domain, SCAN_SOURCE_RESOLVE, SCAN_SOURCE_CHECK_IN, SCAN_SOURCE_BIND, SCAN_SOURCE_CONFIRM_WRITE, PoolBindTarget, pool_should_align_on_resolve, pool_unbind_fields, nfc, bind | `nfc_bind.py` |
| ops schedule, AlarmEvent, ProjectedMove, OpsQueue, evaluate_ops, project_next_move, P2, P3, dwell | `ops_schedule.py` |
| placement inventory, domain, PLACEMENT_DASHBOARD_KINDS, PlacementContainerRow, format_placement_inventory_markdown, filter_rows_for_area_kind, placement, inventory | `placement_inventory.py` |
| production, domain, CONTAINER_BLOCK, CONTAINER_TUB, CONTAINER_BAG, CONTAINER_JAR, CONTAINER_OTHER, PRODUCTION_CONTAINERS, DEFAULT_MAX_FLUSHES, STAGE_INOCULATED, STAGE_INCUBATING, STAGE_FRUITING | `production.py` |
| recipe, domain, DEFAULT_RECIPE_SCALE_MIN, DEFAULT_RECIPE_SCALE_MAX, DEFAULT_RECIPE_SCALE, RecipeLine, WOOD_LOVER_RECIPE, LineProgress, WeighSessionProgress, clamp_recipe_scale, build_weigh_session_progress | `recipe.py` |
| sale, domain, PAYMENT_CASH, PAYMENT_CHECK, PAYMENT_VENMO, PAYMENT_DIGITAL, PAYMENT_OTHER, PAYMENT_METHODS, PACK_STATUS_OPEN, PACK_STATUS_SOLD, DEFAULT_CURRENCY, CLEANUP_CLEANED | `sale.py` |
| shipment tags, domain, STATUS_AVAILABLE, STATUS_BOUND, STATUS_RESERVED, DEFAULT_SHIPMENT_ID, ShipmentTagSpec, DEFAULT_SHIPMENT_TAGS, shipment, tags, NFC | `shipment_tags.py` |
| tachometer, domain, VENT_ROLE_INTAKE, VENT_ROLE_EXHAUST, VENT_ROLE_CIRCULATION, VENT_ROLE_OTHER, VENT_ROLES, UNIT_RPM, UNIT_CFM, UNIT_FPM, TACH_UNITS, SOURCE_MANUAL | `tachometer.py` |
| validation, domain, MAX_NAME_LENGTH, MAX_INGREDIENT_LABEL_LENGTH, MAX_NFC_UID_LENGTH, MASS_REJECT_BELOW_G, BENCH_CAPACITY_G, UNSTABLE_STEP_G, STUCK_EPSILON_G, ALLOWED_RECIPE_UNITS, CLOSE_BAND_PCT, TEMP_SENSOR_MIN_C | `validation.py` |
| weight, domain, MANUAL_WEIGH_OMIT_G, ResolvedWeighMass, resolve_weigh_mass_g, ingredient_key_from_label, WeightEvent | `weight.py` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
