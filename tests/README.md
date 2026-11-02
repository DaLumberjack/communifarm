# tests

## Purpose

T0 pytest suites for domain, platforms, and services.

## How to use this directory

- Oracle = process docs + cea-quality-process — not current return values.
- Map `test_<area>.py` to the module under test; update case Markdown in the same change.

## Map

| path | layer | how / why |
|------|-------|-----------|
| `conftest.py` | `test` | Shared pytest fixtures for Communifarm. — T0 oracle from process docs; update case Markdown with behavior. |
| `README.md` | `test` | This directory map (dim1 Map + dim2 Feature index). |
| `test_batch_lifecycle.py` | `test` | Batch SQLite milestones + complete/new batch tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_climate.py` | `test` | Climate tree, inheritance, control decisions, schema v12 — T0/T2. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_climate_layout.py` | `test` | Operator floor plan: SVG, picture-elements, gauges — T0. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_config_flow.py` | `test` | Config flow tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_culture_process.py` | `test` | Culture process + media SQLite tests (T0). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_dashboard.py` | `test` | Dashboard builder tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_domain.py` | `test` | Domain model unit tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_e2e_local_report.py` | `test` | T0 tests for local E2E summary normalize + CI validate gate. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_entity_bases.py` | `test` | Frozen entity identity. Playwright and existing installs key off these ids. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_esp32dev_scale_contract.py` | `test` | Contract tests for esp32dev scale mock entity IDs. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_esphome_device_mocks.py` | `test` | Contract tests for Communifarm ESPHome HA mock packages and YAML layout. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_init.py` | `test` | Setup, unload, persistence, and service tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_intake_relocate.py` | `test` | Intake scan mode + purchase fields + relocate location select (T0). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_inventory_nfc.py` | `test` | Inventory NFC write / dual-lot UUID / water mapping coverage. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_manual_weigh.py` | `test` | Manual weigh Communifarm number → record_weight mass source (T0). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_mix_protocol.py` | `test` | Mix protocol checklist + water over-add + badge checkpoint. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_nfc_harvest.py` | `test` | NFC resolve / check-in + per-container harvest (schema v9) — T0. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_nfc_resolve.py` | `test` | NFC resolve / bind / check-in coverage beyond the harvest happy path. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_operator_personas.py` | `test` | Operator personas: 95% scan-first vs 40% dropdown-then-act (T0). Oracle: mixing-batch + production-inoculate process docs. 95% — last NFC /  — T0 oracle from process docs; update case Markdown with behavior. |
| `test_placement_inventory.py` | `test` | Production placement inventory + NFC-scoped lifecycle moves (T0). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_placement_locations.py` | `test` | Placement areas / zones (schema v7) — T0 tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_placement_locations_culture.py` | `test` | Culture / media placement zones (schema v8) — T0 tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_point_of_sale.py` | `test` | Point of sale / sales tracking (schema v10) — T0. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_production_inoculate.py` | `test` | Production inoculate domain + SQLite + dashboard tests (T0). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_provisioner.py` | `test` | Dashboard provisioner tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_recipe_session.py` | `test` | Weigh session / recipe scale unit tests. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_shipment_nfc_tags.py` | `test` | Shipment NFC tag pool — CF SQLite seed; sandbox mocks live in packages (T0). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_sqlite_close_lock.py` | `test` | SQLite close must hold DB_LOCK — concurrent close+query segfaults (CI 139). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_tachometer.py` | `test` | Tests for manual vent tachometer / air-exchange logging. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_validation.py` | `test` | Domain validation / sensor-validity unit tests (C1–C12 foundations). — T0 oracle from process docs; update case Markdown with behavior. |
| `test_varieties.py` | `test` | Varieties catalog + LC/grain vessel states (schema v11) — T0. — T0 oracle from process docs; update case Markdown with behavior. |
| `test_weight_repository.py` | `test` | Communifarm SQLite weight_events tests. — T0 oracle from process docs; update case Markdown with behavior. |

## Feature index

| keywords / features | path |
|---------------------|------|
| conftest, test, auto_enable_custom_integrations, sample_state, mock_config_entry, bypass_dashboard | `conftest.py` |
| test batch lifecycle, test, test_first_weight_auto_starts_dry_mixing, test_weigh_milestone_and_complete_new_batch, test_batch_list_sensor_shows_latest_ten_only, test_active_inoculum_select_registers, batch, lifecycle, SQLite | `test_batch_lifecycle.py` |
| test climate, test, NOW_DARK, NOW_LIGHT, NOW_GREEN_ON, NOW_GREEN_OFF, test_operator_layout_parents_and_control_flags, test_reject_temperature_target_out_of_range, test_local_median_ignores_stale_and_one_sensor_is_enough, test_indoor_inherits_parent_outdoor_does_not, test_too_hot_uses_cooler_parent_air_before_ac, test_too_hot_external_air_will_not_help_uses_ac | `test_climate.py` |
| test climate layout, test, test_svg_names_the_operator_rooms, test_png_matches_the_outdoor_and_fruiting_ink, test_drawing_devices_are_the_labeled_marks, test_numbered_probe_lands_on_the_center_dot, test_sensor_overlay_uses_the_same_point_as_the_svg_slots, test_layout_and_status_tabs_without_bindings, test_bound_fan_and_gauges, test_indoor_gauge_is_tight_and_outdoor_is_wide, climate, layout | `test_climate_layout.py` |
| test config flow, test, test_user_flow_creates_entry, test_single_instance_abort, config, flow | `test_config_flow.py` |
| test culture process, test, test_lc_recipe_expects_mason_ports_and_stir_bar, test_lc_stir_milestone_keeps_media_ready, test_bound_stir_plate_records_cf_milestone, test_mea_recipe_lines, test_gate_rejects_planned_media, test_gate_allows_ready_and_in_use, test_child_lot_is_new_identity, test_sqlite_migration_v5_creates_culture_tables, test_introduce_rejects_before_media_ready, test_introduce_creates_child_after_media_ready | `test_culture_process.py` |
| test dashboard, test, test_dashboard_includes_bound_sensors_and_batch, test_dashboard_weigh_tab_redirects_to_mix, test_dashboard_current_settings_use_live_entity_templates, test_dashboard_targets_card_is_interactive, test_dashboard_includes_mix_and_intake_tabs, test_dashboard_production_has_placement_sections, test_dashboard_includes_batches_tab, test_dashboard_omits_missing_optional_controls, dashboard | `test_dashboard.py` |
| test domain, test, test_profile_validation_rejects_bad_humidity, test_batch_transition_and_events, test_suggest_role_from_device_class, test_state_roundtrip, domain | `test_domain.py` |
| test e2e local report, test, test_extract_tests_is_order_independent, test_build_summary_and_validate_green, test_validate_rejects_sha_mismatch_and_failures, test_validate_rejects_missing_required_suite, test_validate_rejects_empty_suite, test_sha_binding_allows_summary_only_child_tip, test_cli_summarize_and_validate, e2e, local, report | `test_e2e_local_report.py` |
| test entity bases, test, EXPECTED_ENTITIES, DRAWING_ENTITIES, test_platform_entities_keep_identity_and_base, entity, bases, Playwright | `test_entity_bases.py` |
| test esp32dev scale contract, test, test_public_entities_use_esp32dev_prefix, test_recipe_ingredients_cover_wood_lover_lines, test_nfc_uid_map_points_at_recipe_ingredients, test_package_yaml_mentions_public_entities, esp32dev, scale, contract | `test_esp32dev_scale_contract.py` |
| test esphome device mocks, test, REPO, PACKAGES, ESPHOME, test_tent_sensor_package_exposes_public_surface, test_sensor_calibration_package_is_reusable, test_aio868_package_exposes_machine_switches, test_nfc_reader_package_exposes_scan_and_write_surfaces, test_esphome_device_files_exist, test_esphome_packages_cover_roles_and_boards, test_kincony_board_package_does_not_publish_gpio_maps | `test_esphome_device_mocks.py` |
| test init, test, test_setup_unload_and_entities, test_repository_roundtrip, test_upgrade_preserves_state, test_batch_transition_service, test_temperature_target_update, test_adjust_targets_minus_one_then_plus_one, test_allowlisted_switch_tracks_underlying_state, init | `test_init.py` |
| test intake relocate, test, test_create_inventory_lot_persists_purchase_fields, test_scan_mode_registers_production_block, test_badge_rejects_empty_nfc_clearly, intake, relocate | `test_intake_relocate.py` |
| test inventory nfc, test, test_water_labels_map_to_recipe_key, test_ndef_identity_roundtrip_stable_ref, isolated_db, test_create_inventory_lot_new_uuid_same_name, test_prepare_and_confirm_nfc_write_binds_chip, test_confirm_nfc_write_rejects_without_prepare, inventory, nfc | `test_inventory_nfc.py` |
| test manual weigh, test, test_resolve_manual_omit_uses_scale, test_resolve_manual_ge_zero_wins_including_zero, test_resolve_rejects_when_neither_available, test_record_weight_uses_manual_when_scale_zero_after_tare, test_record_weight_manual_zero_is_not_in_recipe, test_record_weight_rejects_when_scale_dead_and_manual_omit, manual, weigh | `test_manual_weigh.py` |
| test mix protocol, test, test_wood_lover_includes_water_10200, test_water_pours_sum_toward_target, test_mix_protocol_focus_shows_now_last_next, test_mix_protocol_requires_dry_weigh_before_milestones, test_record_weight_rejects_water_overadd, test_badge_completes_next_mix_milestone, test_relocate_requires_location_then_allows_batch_nfc, test_badge_rejects_when_drys_not_weighed, mix, protocol | `test_mix_protocol.py` |
| test nfc harvest, test, test_require_confirm, test_build_containers_for_inoculate, test_apply_container_harvest_returns_to_fruiting, test_apply_container_harvest_final_completes, test_sqlite_migration_v9_containers, test_dashboard_includes_harvest_tab, test_nfc_resolve_checkin_container_harvest, nfc, harvest | `test_nfc_harvest.py` |
| test nfc resolve, test, test_domain_nfc_validators_and_markdown, test_resolve_unknown_and_entity_uid, test_resolve_batch_culture_media_and_bind, test_checkin_move_batch_and_container_zone, test_checkin_move_culture_and_media, test_nfc_repository_insert_checkin_direct, test_sqlite_migration_v19_nfc_scan_events, test_resolve_audits_scan_and_fills_inventory_amount, test_nfc_bind_pool_align_rules, test_bind_nfc_dual_writes_pool_and_entity | `test_nfc_resolve.py` |
| test operator personas, test, test_persona_95_scan_then_press_moves_only_scanned_bag, test_persona_40_dropdown_scan_then_press_moves_selected_bag, test_persona_95_no_scan_press_moves_entire_batch, test_persona_40_non_container_tag_does_not_scope_to_one_bag, test_persona_badge_rejects_when_checkpoints_done_use_relocate, operator, personas, NFC, batch | `test_operator_personas.py` |
| test placement inventory, test, test_format_placement_empty, test_format_placement_table, test_relocate_lands_containers_in_storage_section, test_advance_with_bag_nfc_moves_only_that_container, placement, inventory, NFC | `test_placement_inventory.py` |
| test placement locations, test, test_default_layout_counts, test_validate_zone_index, test_suggest_area_kind_for_production_stage, test_sqlite_migration_v7_placement, test_ensure_default_layout_persists, test_set_batch_location_persists, test_inoculate_with_zone_id, test_harvest_with_zone_id, placement, locations | `test_placement_locations.py` |
| test placement locations culture, test, test_suggest_area_kind_for_culture_form, test_suggest_area_kind_for_media_status, test_sqlite_migration_v8_culture_media_zones, test_acquire_culture_with_zone_id, test_set_culture_location_moves_lot, test_create_media_batch_with_zone_id, test_set_media_location, test_reject_unknown_zone_id, placement, locations | `test_placement_locations_culture.py` |
| test point of sale, test, test_validate_payment_method, test_sqlite_migration_v10_sales, test_dashboard_includes_pos_tab, test_record_sale_weigh_at_sale_updates_db_and_sensor, test_record_sale_prepacked_pack, test_record_sale_requires_confirm, test_record_sale_cleanup, point, sale | `test_point_of_sale.py` |
| test production inoculate, test, test_stage_transitions_locked, test_gate_rejects_inoculate_during_wet_mix, test_gate_rejects_inoculate_after_fruiting, test_gate_allows_inoculate_from_cooling, test_culture_lot_nfc_uid_defaults_to_stable_id, test_validate_inoculate_requires_substrate, test_advance_gate, test_harvest_gate, test_format_production_markdown, test_sqlite_migration_v6_adds_production_columns | `test_production_inoculate.py` |
| test provisioner, test, test_provision_creates_storage_dashboard_and_saves, test_live_dashboards_collection_unwraps_websocket_handler, provisioner | `test_provisioner.py` |
| test recipe session, test, test_clamp_recipe_scale, test_weigh_session_progress_scaled_targets_and_status, recipe, session | `test_recipe_session.py` |
| test shipment nfc tags, test, test_seed_shipment_tags_fills_pool_and_inventory, test_register_production_block_uses_seeded_tag_source, test_apply_tag_source_scan_and_badge_use_select, test_import_nfc_requires_existing_entity, shipment, nfc, tags, SQLite | `test_shipment_nfc_tags.py` |
| test sqlite close lock, test, test_close_serializes_against_in_flight_query, test_query_after_close_raises_repository_closed, test_migration_v18_to_v19_adds_scan_events_without_data_loss, sqlite, close, lock | `test_sqlite_close_lock.py` |
| test tachometer, test, test_schema_v13_creates_tachometer_tables, test_domain_validators_reject_bad_inputs, test_domain_dicts_round_trip_fields, test_upsert_vent_and_record_reading_with_timestamp, test_upsert_updates_existing_vent_by_label_and_id, test_record_by_label_creates_vent, test_record_requires_vent_identity_and_rejects_bad_ids, test_rejects_negative_value, test_actions_and_services_record_and_update_sensor, test_actions_wrap_validation_errors | `test_tachometer.py` |
| test validation, test, test_c1_reject_negative_mass, test_c1_reject_nan_mass, test_happy_typical_mass, test_c2_warn_over_bench_capacity, test_c3_warn_unstable_step_without_tare, test_c3_no_unstable_warn_when_tared, test_c4_warn_stuck_reading_across_ingredients, test_c5_warn_tare_skipped_on_first_record, test_c6_session_marks_under_and_over, test_c7_environment_out_of_absolute_range | `test_validation.py` |
| test varieties, test, test_sqlite_migration_v11_varieties, test_dashboard_includes_culture_tab, test_seed_varieties_and_custom_crud, test_acquire_lc_and_grain_with_variety_and_status, varieties | `test_varieties.py` |
| test weight repository, test, test_ingredient_key_slug, test_sqlite_migration_creates_weight_events, test_db_lock_is_reentrant, test_weight_repository_roundtrip, test_record_weight_service_persists, test_record_weight_rejects_negative_mass, test_record_weight_warns_over_capacity, test_record_weight_warns_missing_nfc, test_environment_status_degraded_on_bad_sensor, weight | `test_weight_repository.py` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
