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

## weight_events (v1)

| Column | Purpose |
| --- | --- |
| `stable_id` | Public event id (`wgt_…`) |
| `site_id` / `environment_id` / `batch_id` | Communifarm stable refs |
| `ingredient_key` / `ingredient_label` | NFC/recipe ingredient |
| `mass_g` | Recorded mass |
| `nfc_uid` | Optional tag snapshot |
| `source_entity_id` | Entity used for the reading (not a permanent key) |
| `recorded_at` / `created_at` | ISO timestamps |

## Cloud later

Keep this relational shape; replicate or migrate to open-source cloud DB (e.g. PostgreSQL). Do not invent a second local store for the same events.
