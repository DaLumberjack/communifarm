# Communifarm SQLite (process / analysis data)

Long-term Communifarm events live in a Communifarm-owned SQLite file — not Home Assistant Recorder.

| Item | Value |
| --- | --- |
| Path | `<HA config>/communifarm/communifarm.db` |
| Schema | v8 |
| ADR | [0003-communifarm-sqlite.md](../adr/0003-communifarm-sqlite.md) |
| Services | `record_weight`, `record_batch_milestone`, `complete_and_new_batch`, `create_media_batch`, `record_media_weight`, `record_media_milestone`, `acquire_culture`, `introduce_culture`, `inoculate_batch`, `advance_production_stage`, `record_harvest`, `add_batch_note`, `set_check_reminder`, `ensure_placement_layout`, `set_batch_location`, `set_culture_location`, `set_media_location` |

## Why not Recorder?

Recorder is for entity history. Grow analysis needs Communifarm stable IDs (site/environment/batch/ingredient), append-only process events, and a schema we can sync to cloud Postgres later without fighting HA upgrades.

## Master batch hub (`batches`)

`batches.stable_id` is the **canonical batch id** (also the NFC UID by default). Every mix weigh-in, milestone, and (later) production/sales row should FK to it.

```text
batches (master)
  ├── weight_events.batch_id          # mix weigh-ins (scale + target per ingredient)
  ├── batch_milestones.batch_id       # process timeline
  ├── harvest_events.batch_id         # flush harvest weights (+ optional zone_id)
  ├── batches.zone_id                 # placement slot (v7)
  └── sales_lots.batch_id             # future sell-through stats

placement_areas (site tents / fridges / cabinets)
  └── zones.area_id                   # level / shelf slots

media_batches (culture media hub)
  ├── media_weight_events.media_batch_id
  ├── media_milestones.media_batch_id
  ├── culture_events.media_batch_id
  └── media_batches.zone_id           # placement slot (v8)

culture_lots (culture inventory)
  ├── culture_events.culture_id
  ├── culture_events.batch_id         # production inoculate link
  ├── culture_lots.parent_culture_id  # lineage; expand always creates a child
  └── culture_lots.zone_id            # placement slot (v8)
```

| Column | Purpose |
| --- | --- |
| `stable_id` | Public batch id (`batch_…`) — FK target |
| `status` | `active` \| `complete` |
| `lifecycle_phase` | Mix + production: `planned` → … → `cooling` → `inoculated` → `incubating` → `fruiting` → `harvesting` → `complete` |
| `recipe_scale` | Batch-level scale factor (0.1–10) used for this mix |
| `recipe_key` | Recipe id (`wood_lover`, …) |
| `mixing_started_at` / `mixing_finished_at` | Mix window |
| `container_count` | Split / production container count |
| `culture_id` | Culture lot that inoculated this batch (v6) |
| `container_type` | `block` \| `tub` \| `bag` \| `jar` \| `other` |
| `substrate_g_per_container` | Substrate mass per container (g) |
| `flush_count` / `max_flushes` | Harvest flush tracking (default max 3) |
| `expected_check_at` | Next operator check reminder |
| `zone_id` | Placement zone slot (v7; FK → `zones.stable_id`) |
| `nfc_uid` | Tag that follows the bag until container split |

Lifecycle phase advances when milestones are recorded (and on complete).

## Culture media hub (`media_batches` + `culture_lots`)

Sibling process family for agar / liquid culture prep. **Do not overload production `batches`.**

| Service | Purpose |
| --- | --- |
| `create_media_batch` | Start MEA agar (default) or honey/Karo LC prep; optional `zone_id` |
| `record_media_weight` | Recipe line amount (`g` / `ml`) with scale + target |
| `record_media_milestone` | `media_portioned` → `media_sterilized` → `media_ready` (pour plates **before** sterilize) |
| `acquire_culture` | Register lot (`wild` / `acquaintance` / `purchased`); optional `zone_id` |
| `introduce_culture` | Requires `media_ready` or `in_use`; **always** creates a new child `culture_lot`; optional child `zone_id` |
| `set_culture_location` | Set `culture_lots.zone_id`; event `culture_location_set` |
| `set_media_location` | Set `media_batches.zone_id`; event `media_location_set` |

Hard gate: introducing culture into a planned/weighing/sterilizing media batch is rejected.

LC mason jars: lid expects syringe port + breathability port; stir bar in jar; milestones `lc_stir_started` / `lc_stir_stopped` after inoculate. Drawing LC into a separate container creates a new child culture lot.

Bound stir plate: role `lc_stir_plate` → CF proxy `switch.communifarm_lc_stir_plate`. Toggling the proxy forwards to the bound HA switch and appends `lc_stir_*` milestones on `active_media_batch_id` (set when `create_media_batch` runs).

Default recipes: `mea_agar_500`, `honey_lc_500` (see workspace `docs/intake/mushroom data/culture-recipes.md`).

## Production inoculate (schema v6+)

Culture → substrate containers (independent of mix recipe). See [production-inoculate.md](../process/production-inoculate.md).

| Service | Purpose |
| --- | --- |
| `inoculate_batch` | Link active culture lot; set container type/count + substrate g/container; optional `zone_id` |
| `advance_production_stage` | `incubating` → `fruiting` → `harvesting`; optional `zone_id` |
| `record_harvest` | Flush mass (g); `is_final` completes batch; optional harvest `zone_id` |
| `add_batch_note` / `set_check_reminder` | Notes + HA notification |

`harvest_events` rows FK `batches.stable_id`. Dashboard **Production** tab drives the flow.

## Placement locations (schema v7–v8)

Site → PlacementArea → Zone. See [placement-locations.md](../process/placement-locations.md).

| Service | Purpose |
| --- | --- |
| `ensure_placement_layout` | Seed default tents/fridges/cabinets + 24 zones (idempotent) |
| `set_batch_location` | Set `batches.zone_id` |
| `set_culture_location` | Set `culture_lots.zone_id` (v8) |
| `set_media_location` | Set `media_batches.zone_id` (v8) |

Soft stage / form / media-status → area_kind hints only (no hard reject in MVP).

## Mix weigh-ins (`weight_events`)

One row per recorded ingredient weigh for a batch. **Scale factor and target weight are columns on every row.**

| Column | Purpose |
| --- | --- |
| `batch_id` | FK → `batches.stable_id` |
| `ingredient_key` / `ingredient_label` | NFC/recipe ingredient |
| `mass_g` | Recorded mass |
| `recipe_scale` | Scale factor **at record time** (0.1–10) |
| `target_amount` | Scaled recipe target for that ingredient line |
| `unit` | Recipe unit (`g`, `qts`, …) |
| `nfc_uid` | Optional tag snapshot |
| `recorded_at` / `created_at` | ISO timestamps |

## Milestones (`batch_milestones`)

Append-only process events (`dry_mixing_started`, `water_added`, `heat_treated`, …). First successful weigh auto-inserts `dry_mixing_started`.

## Weigh session UI

| Entity | Purpose |
| --- | --- |
| `sensor.communifarm_weigh_session` | Session table includes **Target** + recorded; attrs carry `recipe_scale` |
| `number.communifarm_recipe_scale` | Updates Store **and** master `batches.recipe_scale` |
| `sensor.communifarm_batch_list` | Master list with phase + scale + mix times |
| `sensor.communifarm_batch_milestones` | Timeline for active batch |

## Validity rules (operator-usable)

| Case | Behavior |
| --- | --- |
| `mass_g` &lt; 0, NaN, Inf | **Reject** — no SQLite row; `last_reject` on session |
| `mass_g` &gt; 100 kg (bench capacity) | **Warn** `over_capacity` — row stored for audit |
| Large jump without tare | **Warn** `unstable_reading` |
| Same mass, different ingredient | **Warn** `stuck_reading` |
| First record without tare | **Warn** `tare_skipped` |
| Ingredient set, NFC empty | **Warn** `missing_nfc` |
| Names / ingredient / NFC UID over length | **Reject** (readability limits) |
| Every 50th record | **Warn** `calibration_due` |
| Temp/humidity outside absolute sensor range | Environment status `degraded` |

## Cloud later

Keep this relational shape; replicate or migrate to open-source cloud DB (e.g. PostgreSQL). Do not invent a second local store for the same events. Future `production_cycles` / `sales_lots` tables must reference `batches.stable_id`.
