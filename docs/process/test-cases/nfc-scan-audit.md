# NFC scan audit / dual-write — test cases

Architecture: [nfc-schema.md](../../architecture/nfc-schema.md)

| case | oracle | T0 |
|------|--------|-----|
| Resolve unknown UID | Appends scan event; session `found=false`; no object qty change | `test_nfc_resolve.py` |
| Resolve inventory with amount | Session gets DB label + amount; lot amount unchanged | `test_resolve_audits_scan_and_fills_inventory_amount` |
| Confirm NFC write | Entity `nfc_uid` + pool `bound` + `bound_object_type` | `test_prepare_and_confirm_nfc_write_binds_chip` |
| bind_nfc dual-write | Entity + pool registry updated together | `test_bind_nfc_dual_writes_pool_and_entity` |
| Available pool chip | Bare resolve does **not** auto-bind | `test_resolve_does_not_auto_bind_available_pool_chip` |
| Bound pool drift | Resolve realigns `bound_object_id` / type | `test_resolve_aligns_drifted_bound_pool_row` |
| Register production block | Pool bound to container id/type | `test_shipment_nfc_tags` register path |
| Schema v19 | `nfc_scan_events` + `bound_object_type` | `test_sqlite_migration_v19_nfc_scan_events` |
| v18→v19 upgrade | Pool row preserved; scan table added | `test_migration_v18_to_v19_adds_scan_events_without_data_loss` |
| SQLite close race | Close under `DB_LOCK` (no CI exit 139) | `test_sqlite_close_lock.py` |
| Intake process modes | Conditional cards for mark vs purchase | `test_dashboard.py` Intake assertions |
