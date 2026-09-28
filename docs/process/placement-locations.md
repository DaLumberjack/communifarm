# Placement locations (areas + zones)

Physical placement for production batches: tents, fridges, and cabinets subdivided into level/shelf slots.

| Item | Value |
| --- | --- |
| Schema | v7 |
| Model | Site → PlacementArea → Zone → `batches.zone_id` |
| Services | `ensure_placement_layout`, `set_batch_location` (+ optional `zone_id` on inoculate / advance / harvest) |
| Related | [production-inoculate.md](production-inoculate.md), [storage](../user/storage.md) |

## Hierarchy

```text
Site
 └── PlacementArea (tent / fridge / cabinet)  — SQLite
      └── Zone (level or shelf slot)          — SQLite
           └── batches.zone_id               — where the production batch sits
```

Area kinds and slot kinds are **data-driven** (`area_kind`, `slot_kind`). Do not hard-code fungi-only branches in domain logic.

## Default seed layout

Created by `ensure_placement_layout` / `LocationRepository.ensure_default_layout` (idempotent per site).

| Area name | area_kind | slot_kind | count |
| --- | --- | --- | --- |
| Fruiting tent | fruiting_tent | level | 5 |
| Inoculation tent | inoculation_tent | level | 5 |
| Culture fridge | culture_fridge | shelf | 5 |
| Still air cabinet | still_air_cabinet | shelf | 3 |
| Harvest fridge | harvest_fridge | shelf | 6 |

Total zones: **24**.

## Soft stage → area hints

MVP does **not** hard-reject mismatched areas; production status attrs may include `location_warning`.

| Production stage | Suggested area_kind |
| --- | --- |
| inoculated / incubating | inoculation_tent |
| fruiting / harvesting | fruiting_tent |
| after pick (harvest event) | harvest_fridge (via `record_harvest` `zone_id`) |

## Services

| Service | Purpose |
| --- | --- |
| `ensure_placement_layout` | Seed default areas/zones for the site |
| `set_batch_location` | Set `batches.zone_id` (optional `batch_id`) |
| `inoculate_batch` | Optional `zone_id` |
| `advance_production_stage` | Optional `zone_id` (moves batch when advancing) |
| `record_harvest` | Optional `zone_id` on harvest event (e.g. harvest fridge shelf) |

## Dashboard

Production tab shows `zone_id` / area / zone name from `sensor.communifarm_production_status` attrs and a markdown placement hint.

## Testing

| Stage | Coverage |
| --- | --- |
| T0 | `tests/test_placement_locations.py` — layout counts, set location, inoculate/harvest zone_id, stage suggestions, schema v7 |
| T1 / T2 | Pending (schema migration needs T2 before merge to main) |
