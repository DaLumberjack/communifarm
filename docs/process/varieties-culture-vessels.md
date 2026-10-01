# Varieties + culture vessels (inoculum catalog)

One physical LC jar / grain bag / vial = **one `culture_lots` row** with a stable UID (`nfc_uid`, default = `stable_id`). The human-facing name is the **mushroom variety**.

| Item | Value |
| --- | --- |
| Schema | v11 |
| Catalog table | `varieties` (seed + custom) |
| Lot FK | `culture_lots.variety_id` |
| Forms | `liquid_culture`, `grain_spawn`, `agar`, `spores` |
| Vessel statuses (LC & grain) | `colonizing` → `ready` → `drawing` → `exhausted` (+ `contaminated` / `retired`) |
| Dashboard | **Culture** tab (`/communifarm/culture`) |
| Services | `create_variety`, `retire_variety`, `acquire_culture`, `set_culture_status` |

## Seed varieties

Chestnut, Blue oyster, White oyster, Shiitake, APE, Cascadia Teacher, Golden Teacher.

Custom varieties via **New variety name** → **Create variety** (or `create_variety` / `acquire_culture` with `variety_name`).

## Flow

```text
create_variety (optional custom)
        ↓
acquire_culture (variety_id | variety_name) → culture_lots row (UID)
        ↓
set_culture_status → ready / drawing / …
        ↓
Active inoculum (Production) → inoculate_batch
```

Inoculate / active inoculum only when status ∈ `ready` | `drawing` | `active` (legacy).

## UI

| Control | Entity |
| --- | --- |
| Variety list | `sensor.communifarm_variety_list` |
| Inventory | `sensor.communifarm_culture_inventory` |
| New name | `text.communifarm_variety_name` |
| Catalog pick | `select.communifarm_catalog_variety` |
| Acquire form / source | `select.communifarm_acquire_form`, `select.communifarm_acquire_source` |
| Vessel status | `select.communifarm_culture_vessel_status` + set button |
