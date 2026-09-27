# Communifarm SQLite (process / analysis data)

Long-term Communifarm events live in a Communifarm-owned SQLite file — not Home Assistant Recorder.

| Item | Value |
| --- | --- |
| Path | `<HA config>/communifarm/communifarm.db` |
| Schema | v4 |
| ADR | [0003-communifarm-sqlite.md](../adr/0003-communifarm-sqlite.md) |
| Services | `record_weight`, `record_batch_milestone`, `complete_and_new_batch` |

## Why not Recorder?

Recorder is for entity history. Grow analysis needs Communifarm stable IDs (site/environment/batch/ingredient), append-only process events, and a schema we can sync to cloud Postgres later without fighting HA upgrades.

## Master batch hub (`batches`)

`batches.stable_id` is the **canonical batch id** (also the NFC UID by default). Every mix weigh-in, milestone, and (later) production/sales row should FK to it.

```text
batches (master)
  ├── weight_events.batch_id          # mix weigh-ins (scale + target per ingredient)
  ├── batch_milestones.batch_id       # process timeline
  ├── production_cycles.batch_id      # future grow stats
  └── sales_lots.batch_id             # future sell-through stats
```

| Column | Purpose |
| --- | --- |
| `stable_id` | Public batch id (`batch_…`) — FK target |
| `status` | `active` \| `complete` |
| `lifecycle_phase` | Category: `planned` → `dry_mixing` → … → `in_production` → `complete` |
| `recipe_scale` | Batch-level scale factor (0.1–10) used for this mix |
| `recipe_key` | Recipe id (`wood_lover`, …) |
| `mixing_started_at` / `mixing_finished_at` | Mix window |
| `container_count` | Split count (MVP) |
| `nfc_uid` | Tag that follows the bag until container split |

Lifecycle phase advances when milestones are recorded (and on complete).

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
