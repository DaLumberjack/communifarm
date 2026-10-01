# Placement locations (areas + zones)

Physical placement for production batches, culture lots, and media prep: tents, fridges, and cabinets subdivided into level/shelf slots.

| Item | Value |
| --- | --- |
| Schema | v8 |
| Model | Site → PlacementArea → Zone → `batches.zone_id` / `culture_lots.zone_id` / `media_batches.zone_id` |
| Services | `ensure_placement_layout`, `set_batch_location`, `set_culture_location`, `set_media_location` (+ optional `zone_id` on inoculate / advance / harvest / acquire / create_media / introduce) |
| Related | [production-inoculate.md](production-inoculate.md), [storage](../user/storage.md) |

## Hierarchy

```text
Site
 └── PlacementArea (tent / fridge / cabinet)  — SQLite
      └── Zone (level or shelf slot)          — SQLite
           ├── batches.zone_id                — production batch (v7)
           ├── culture_lots.zone_id           — culture storage (v8)
           └── media_batches.zone_id          — media prep / ready (v8)
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

## Soft area hints

MVP does **not** hard-reject mismatched areas; production status attrs may include `location_warning`. Soft helpers: `suggest_area_kind_for_production_stage`, `suggest_area_kind_for_culture_form`, `suggest_area_kind_for_media_status`.

| Object / context | Suggested area_kind |
| --- | --- |
| inoculated / incubating | inoculation_tent |
| fruiting / harvesting | fruiting_tent |
| after pick (harvest event) | harvest_fridge (via `record_harvest` `zone_id`) |
| culture_lots (agar / LC / spores storage) | culture_fridge |
| media_batches planned / weighing / sterilizing | still_air_cabinet |
| media_batches media_ready / in_use | culture_fridge |
| SAB work notes (transfers, plating) | still_air_cabinet |

## Services

| Service | Purpose |
| --- | --- |
| `ensure_placement_layout` | Seed default areas/zones for the site |
| `set_batch_location` | Set `batches.zone_id` (optional `batch_id`) |
| `set_culture_location` | Set `culture_lots.zone_id`; event `culture_location_set` |
| `set_media_location` | Set `media_batches.zone_id`; event `media_location_set` |
| `inoculate_batch` | Optional `zone_id` |
| `advance_production_stage` | Optional `zone_id` (moves batch when advancing) |
| `record_harvest` | Optional `zone_id` on harvest event (e.g. harvest fridge shelf) |
| `acquire_culture` | Optional `zone_id` |
| `create_media_batch` | Optional `zone_id` |
| `introduce_culture` | Optional `zone_id` for child culture storage after intro |

## Culture / media (schema v8)

Culture fridge shelves hold agar plates and LC jars. Still-air cabinet shelves hold media prep and sterile work. Location moves append `culture_events` with types `culture_location_set` / `media_location_set`.

No dedicated culture Lovelace tab yet — use services; Production tab markdown notes culture/media placement services.

## Dashboard

Production tab shows `zone_id` / area / zone name from `sensor.communifarm_production_status` attrs and a markdown placement hint (batch + culture/media services).

## Testing

| Stage | Coverage |
| --- | --- |
| T0 | `tests/test_placement_locations.py` (v7 production) + `tests/test_placement_locations_culture.py` (v8 culture/media) |
| T1 / T2 | Pending (schema migration needs T2 before merge to main) |
