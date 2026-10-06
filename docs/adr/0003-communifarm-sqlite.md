# ADR 0003: Communifarm SQLite for process / analysis events

## Status

Accepted

## Context

Recording scale weights (NFC-selected ingredient + mass) is the first Communifarm-owned dataset for long-term grow analysis. Options considered:

| Option | Fit |
| --- | --- |
| HA Recorder / `home-assistant_v2.db` | Wrong owner — HA schema, entity-centric, weak stable Communifarm IDs, painful cloud export |
| HA `Store` JSON | Fine for config/profile; poor for append-only events and queries |
| **Communifarm SQLite file** | Matches storage skill; local, open source; same relational shape can later sync/migrate to cloud Postgres |
| Cloud DB first | Speculative infrastructure; blocked by project rules |

## Decision

1. Keep **HA Store** for mutable setup state (Site/Environment/profile/active batch pointer) — ADR 0001.
2. Add a **Communifarm-owned SQLite** database under the HA config dir (`communifarm/communifarm.db`) for process events and future aggregates.
3. **Master table `batches`**: one row per mix/grow batch (`stable_id`), with `status`, `lifecycle_phase`, `recipe_scale`, and mix timestamps. This is the FK hub for weigh-ins, milestones, and later production/sales stats.
4. **Mix weigh-ins `weight_events`**: append-only rows keyed by `batch_id`, always storing `recipe_scale` and `target_amount` for the ingredient line at record time.
5. **Milestones `batch_milestones`**: append-only process timeline keyed by `batch_id`.
6. **Culture media (schema v5)**: sibling hubs `media_batches` + `culture_lots` with `media_weight_events`, `media_milestones`, and `culture_events`. Expand/transfer always creates a new child culture lot; culture may enter media only when status is `media_ready` (or already `in_use`).
7. **Production inoculate (schema v6)**: `batches` gains culture/container/substrate/flush columns; `harvest_events` append-only flush weights; `culture_events.batch_id` links culture → production inoculate (no child culture lot for substrate).
8. **Placement locations (schema v7)**: `placement_areas` + `zones` under a site; `batches.zone_id` and optional `harvest_events.zone_id`; data-driven `area_kind` / `slot_kind` (default seed: fruiting/inoculation tents, culture/harvest fridges, still-air cabinet).
9. **Culture / media placement (schema v8)**: `culture_lots.zone_id` + `media_batches.zone_id`; services `set_culture_location` / `set_media_location`; optional `zone_id` on `acquire_culture` / `create_media_batch` / `introduce_culture`; events `culture_location_set` / `media_location_set`.
10. **Per-container NFC harvest (schema v9)**: `production_containers` (one NFC identity + flush/zone per block); `nfc_checkins` append-only handheld check-ins; `harvest_events.container_id`; `sale_packs` keyed by `harvest_id`. NFC tags store **stable IDs only**; SQLite is source of truth. Services `resolve_nfc`, `check_in`, `bind_nfc`, `record_container_harvest` (requires `confirm=true`).
11. **Point of sale (schema v10)**: `sales` + `sale_line_items` + `sale_cleanup_events`; `sale_packs.sold_sale_id` + status `sold`; services `record_sale` / `record_sale_cleanup` (sale requires `confirm=true`). General tracking only — not GAP/accounting compliance. Travel/depreciation deferred.
12. **Varieties + vessel state (schema v11)**: `varieties` catalog (seed mushroom names + custom); `culture_lots.variety_id`; forms include `grain_spawn`; LC/grain vessel statuses `colonizing`/`ready`/`drawing`/`exhausted` (+ contaminated/retired). One jar/vial = one culture row (UID). Services `create_variety` / `retire_variety` / `set_culture_status`; Culture dashboard tab.
13. Do **not** create custom tables inside Recorder’s database.
14. Cloud later: replicate/migrate the same relational model to an open-source server DB (e.g. PostgreSQL); keep domain repositories abstract so backends can swap.

## Consequences

- Weigh “Record” persists via Communifarm (service + scale button hook), not only ESPHome `last_recorded` text.
- SQLite I/O runs off the event loop (`async_add_executor_job`).
- Schema versioned with tested migrations (current: **v12**, climate tree in ADR 0004).
- Env metric rollups remain a later table family; raw high-frequency sensor history stays Recorder’s job.
- Selling / production statistics tables must FK `batches.stable_id` — do not invent parallel batch ids.
- Culture media must not reuse production `batches` rows for agar/LC prep.
- Harvest yield analysis uses `harvest_events` keyed by batch (and optionally `container_id`).
- Physical placement uses `zones.stable_id`; do not treat mutable area display names as permanent IDs.
- Culture lots and media batches share the same zone ID space as production batches.
- NFC chips must not encode mutable stage/location; resolve via `nfc_uid` → SQLite object.
- POS sales are general ops/finance tracking for analysis and tax-prep handoff — not GAP or formal books.