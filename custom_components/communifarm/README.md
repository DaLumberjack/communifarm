# communifarm

## Purpose

Installable Communifarm HA integration: platforms, adapters, domain, storage.

## How to use this directory

- Platforms (`sensor.py`, …) = HA entities; `*_actions.py` = service adapters; `domain/` = pure logic.
- Config/onboarding → `config_flow.py` + onboarding/dashboards skills.
- Always run T0 for this package; UI → testing/playwright.md.

## Map

| path | layer | how / why |
|------|-------|-----------|
| `dashboard/` | `ui` | Enter for ui work — read `dashboard/README.md` (Feature index → Map). |
| `domain/` | `domain` | Enter for domain work — read `domain/README.md` (Feature index → Map). |
| `fixtures/` | `fixture` | Enter for fixture work — read `fixtures/README.md` (Feature index → Map). |
| `storage/` | `storage` | Enter for storage work — read `storage/README.md` (Feature index → Map). |
| `translations/` | `dir` | Child map — read `translations/README.md` before exploring. |
| `__init__.py` | `config` | The Communifarm integration. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `batch_actions.py` | `adapter` | Batch milestone / complete-and-new application helpers. — HA service/action bridge — keep domain calls thin; test via services. |
| `binary_sensor.py` | `platform` | Binary sensor platform — preset float on the climate schematic. — HA entity platform — bind capabilities; avoid domain leakage of entity IDs as PKs. |
| `button.py` | `platform` | Button platform — mix / batch / production milestone actions. — HA entity platform — bind capabilities; avoid domain leakage of entity IDs as PKs. |
| `climate_actions.py` | `adapter` | Home Assistant adapter for climate layout, ticks, and entity commands. — HA service/action bridge — keep domain calls thin; test via services. |
| `climate_entities.py` | `adapter` | Preset entities for the sensors and machines drawn on the schematic. — HA service/action bridge — keep domain calls thin; test via services. |
| `config_flow.py` | `config` | Config flow for Communifarm onboarding. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `const.py` | `config` | Constants for the Communifarm integration. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `culture_actions.py` | `adapter` | Culture / media application helpers (services). — HA service/action bridge — keep domain calls thin; test via services. |
| `entity.py` | `config` | Shared Communifarm entity plumbing. Two levels only: this base, then one platform base in the platform module. Subclasses override behavior. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `inventory_actions.py` | `adapter` | Inventory lot create / NFC write prepare / badge mix-step helpers. — HA service/action bridge — keep domain calls thin; test via services. |
| `location_actions.py` | `adapter` | Placement layout and batch location application helpers. — HA service/action bridge — keep domain calls thin; test via services. |
| `manifest.json` | `config` | config file `manifest.json`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `nfc_actions.py` | `adapter` | NFC resolve / check-in application helpers (handheld scanner pull model). — HA service/action bridge — keep domain calls thin; test via services. |
| `number.py` | `platform` | Number platform for Communifarm profile targets and dashboard drafts. — HA entity platform — bind capabilities; avoid domain leakage of entity IDs as PKs. |
| `production_actions.py` | `adapter` | Production inoculate / stage / harvest application helpers. — HA service/action bridge — keep domain calls thin; test via services. |
| `README.md` | `ops` | This directory map (dim1 Map + dim2 Feature index). |
| `sale_actions.py` | `adapter` | Point-of-sale application helpers. — HA service/action bridge — keep domain calls thin; test via services. |
| `select.py` | `platform` | Select platform — heat treatment, production, culture, and sale drafts. — HA entity platform — bind capabilities; avoid domain leakage of entity IDs as PKs. |
| `sensor.py` | `platform` | Sensor platform for Communifarm. — HA entity platform — bind capabilities; avoid domain leakage of entity IDs as PKs. |
| `services.yaml` | `config` | config file `services.yaml`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `strings.json` | `config` | config file `strings.json`. — Onboarding/setup surface — pair with onboarding + dashboards skills. |
| `switch.py` | `platform` | Switch platform — allowlisted proxies for bound switch entities. — HA entity platform — bind capabilities; avoid domain leakage of entity IDs as PKs. |
| `tachometer_actions.py` | `adapter` | Home Assistant adapter for manual vent tachometer logging. — HA service/action bridge — keep domain calls thin; test via services. |
| `text.py` | `platform` | Text platform — variety name + Intake purchase / machine / employee drafts. — HA entity platform — bind capabilities; avoid domain leakage of entity IDs as PKs. |

## Feature index

| keywords / features | path |
|---------------------|------|
| dashboard, ui | `dashboard/` |
| domain | `domain/` |
| fixtures, fixture | `fixtures/` |
| storage | `storage/` |
| translations, dir | `translations/` |
| config, CONFIG_SCHEMA, TRANSITION_SCHEMA, RECORD_WEIGHT_SCHEMA, RECORD_MILESTONE_SCHEMA, COMPLETE_NEW_BATCH_SCHEMA, CREATE_MEDIA_BATCH_SCHEMA, RECORD_MEDIA_WEIGHT_SCHEMA, RECORD_MEDIA_MILESTONE_SCHEMA, ACQUIRE_CULTURE_SCHEMA, CREATE_VARIETY_SCHEMA, RETIRE_VARIETY_SCHEMA | `__init__.py` |
| batch actions, adapter, ALLOWED_MANUAL, async_record_milestone, async_ensure_dry_mixing_started, async_complete_and_new_batch, batch, actions | `batch_actions.py` |
| binary sensor, platform, async_setup_entry, binary, sensor | `binary_sensor.py` |
| button, platform, CommunifarmButton, CommunifarmMilestoneButton, CommunifarmAdvanceStageButton, async_setup_entry, CommunifarmFieldCapacityButton, CommunifarmRelocateSterileButton, CommunifarmRecordWaterPourButton, CommunifarmCreateInventoryLotButton, CommunifarmPrepareNfcWriteButton, CommunifarmConfirmNfcWriteButton | `button.py` |
| climate actions, adapter, async_ensure_climate_layout, async_bind_climate_role, async_tick_climate, climate, actions | `climate_actions.py` |
| climate entities, adapter, CommunifarmDrawingSensor, CommunifarmDrawingSwitch, CommunifarmDrawingBinarySensor, drawing_sensor_entities, drawing_switch_entities, drawing_binary_entities, climate, entities | `climate_entities.py` |
| config flow, config, CommunifarmConfigFlow, CommunifarmOptionsFlow, flow | `config_flow.py` |
| const, config, DOMAIN, VERSION, CONF_SITE_NAME, CONF_ENVIRONMENT_NAME, CONF_BATCH_NAME, CONF_TEMPERATURE_ENTITY, CONF_HUMIDITY_ENTITY, CONF_FAN_ENTITY, CONF_SWITCH_ENTITY, CONF_STIR_PLATE_ENTITY | `const.py` |
| culture actions, adapter, async_set_active_inoculum, async_select_inoculum_from_nfc_scan, async_create_media_batch, async_record_media_weight, async_record_media_milestone, async_create_variety, async_retire_variety, async_set_culture_status, async_acquire_culture, async_introduce_culture | `culture_actions.py` |
| entity, config, CommunifarmEntity | `entity.py` |
| inventory actions, adapter, format_tag_source_option, parse_tag_source_option, resolve_tag_source_uid, new_pending_nfc_write, async_create_inventory_lot, async_create_employee_badge, async_prepare_nfc_write, async_confirm_nfc_write, async_list_zone_option_labels, async_list_tag_source_options | `inventory_actions.py` |
| location actions, adapter, async_ensure_default_layout, async_set_batch_location, async_first_zone_for_area_kind, async_ensure_storage_zone, async_list_locations, async_resolve_location_attrs, location, actions, batch | `location_actions.py` |
| manifest, config | `manifest.json` |
| nfc actions, adapter, new_nfc_session, async_dual_write_pool_bind, async_resolve_nfc, async_check_in, async_bind_nfc, nfc, actions | `nfc_actions.py` |
| number, platform, CommunifarmNumber, CommunifarmProfileNumber, CommunifarmBucketNumber, async_setup_entry, CommunifarmTemperatureTarget, CommunifarmHumidityTarget, CommunifarmRecipeScale | `number.py` |
| production actions, adapter, async_inoculate_batch, async_advance_production_stage, async_placement_inventory_rows, async_placement_section, async_record_container_harvest, async_record_harvest, async_add_batch_note, async_set_check_reminder, async_production_summary, production_summary_markdown | `production_actions.py` |
| sale actions, adapter, async_record_sale, async_record_sale_cleanup, async_sales_summary, sales_summary_markdown, sale, actions | `sale_actions.py` |
| select, platform, CommunifarmSelect, CommunifarmBucketSelect, async_setup_entry, CommunifarmTagSourceSelect, CommunifarmZoneSelect, CommunifarmActiveInoculumSelect, CommunifarmCatalogVarietySelect | `select.py` |
| sensor, platform, CommunifarmSensor, async_setup_entry, CommunifarmBatchStageSensor, CommunifarmEnvironmentStatusSensor, CommunifarmBatchNfcUidSensor, CommunifarmWeighSessionSensor, CommunifarmMixProtocolSensor, CommunifarmNfcWriteStatusSensor, CommunifarmFieldCapacitySensor, CommunifarmBatchListSensor | `sensor.py` |
| services, config, transition_batch, record_weight, record_batch_milestone, complete_and_new_batch, create_media_batch, record_media_weight, record_media_milestone, acquire_culture, create_variety, retire_variety | `services.yaml` |
| strings, config | `strings.json` |
| switch, platform, CommunifarmSwitch, async_setup_entry, CommunifarmAllowlistedSwitch, CommunifarmLcStirPlateSwitch | `switch.py` |
| tachometer actions, adapter, async_upsert_air_vent, async_record_tachometer, async_refresh_tachometer_snapshot, tachometer, actions | `tachometer_actions.py` |
| text, platform, CommunifarmText, CommunifarmBucketText, async_setup_entry, CommunifarmVarietyNameText | `text.py` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
