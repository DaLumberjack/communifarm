# Communifarm SQLite (process / analysis data)

Long-term Communifarm events (starting with **weigh-ins**) live in a Communifarm-owned SQLite file — not Home Assistant Recorder.

| Item | Value |
| --- | --- |
| Path | `<HA config>/communifarm/communifarm.db` |
| First table | `weight_events` |
| ADR | [0003-communifarm-sqlite.md](../adr/0003-communifarm-sqlite.md) |
| Service | `communifarm.record_weight` |
| Auto hook | Pressing `button.esp32dev_record_weight` also inserts a row |

## Why not Recorder?

Recorder is for entity history. Grow analysis needs Communifarm stable IDs (site/environment/batch/ingredient), append-only process events, and a schema we can sync to cloud Postgres later without fighting HA upgrades.

## Weigh session UI

| Entity | Purpose |
| --- | --- |
| `sensor.communifarm_weigh_session` | `N/M lines recorded` + `progress_text` / `lines` attrs from SQLite |
| `number.communifarm_recipe_scale` | 0.1×–10× recipe multiplier (Store) |
| `sensor.communifarm_batch_nfc_uid` | Batch UID for NFC (defaults to `batch.id`) |

Weigh dashboard tab shows scaled targets vs recorded amounts for the **active batch** only (latest event per ingredient). Colored gauges for closeness are deferred.

Session sensor also exposes calibration **warnings** / **last_reject** (negative mass rejected; over-capacity / stuck / missing NFC / tare skipped accepted with alert).

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

## weight_events (schema v2)

| Column | Purpose |
| --- | --- |
| `stable_id` | Public event id (`wgt_…`) |
| `site_id` / `environment_id` / `batch_id` | Communifarm stable refs |
| `ingredient_key` / `ingredient_label` | NFC/recipe ingredient |
| `mass_g` | Recorded mass |
| `nfc_uid` | Optional tag snapshot |
| `source_entity_id` | Entity used for the reading (not a permanent key) |
| `recorded_at` / `created_at` | ISO timestamps |
| `recipe_scale` | Scale factor at record time (0.1–10) |
| `target_amount` | Scaled recipe target for that line |

## Cloud later

Keep this relational shape; replicate or migrate to open-source cloud DB (e.g. PostgreSQL). Do not invent a second local store for the same events.
