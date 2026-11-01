# NFC scan audit / dual-write — test cases

Architecture: [nfc-schema.md](../../architecture/nfc-schema.md)

| case | oracle | T0 |
|------|--------|-----|
| Resolve unknown UID | Appends scan event; session `found=false`; no object qty change | `test_nfc_resolve.py` |
| Resolve inventory with amount | Session gets DB label + amount; lot amount unchanged | `test_resolve_audits_scan_and_fills_inventory_amount` |
| Confirm NFC write | Entity `nfc_uid` + pool `bound` + `bound_object_type` | `test_prepare_and_confirm_nfc_write_binds_chip` |
| Register production block | Pool bound to container id/type | `test_shipment_nfc_tags` register path |
| Schema v19 | `nfc_scan_events` + `bound_object_type` | `test_sqlite_migration_v19_nfc_scan_events` |
| Intake process modes | Conditional cards for mark vs purchase | `test_dashboard.py` Intake assertions |
