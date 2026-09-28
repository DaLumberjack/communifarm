# Production inoculate (culture → substrate)

Bridge from culture lots into substrate production batches: inoculate N identical containers, advance incubating → fruiting → harvesting, record flush harvests.

| Item | Value |
| --- | --- |
| Schema | v6 |
| Services | `inoculate_batch`, `advance_production_stage`, `record_harvest`, `add_batch_note`, `set_check_reminder` |
| Dashboard | **Production** tab (`/communifarm/production`) |
| Related | [culture media](../user/storage.md#culture-media-hub-media_batches--culture_lots), [storage](../user/storage.md) |

## Locked defaults

| # | Decision | Value |
| --- | --- | --- |
| 1 | Unit of work | N identical containers under one `batches` row |
| 2 | Quantity | Substrate **g/container** required; inoculum amount optional |
| 3 | Container types | `block` \| `tub` \| `bag` \| `jar` \| `other` |
| 4 | Stages | `inoculated` → `incubating` → `fruiting` → `harvesting` → `complete` |
| 5 | Flushes | Default max 3; explicit `is_final` ends batch |
| 6 | Reminders | `expected_check_at` + `persistent_notification` |
| 7 | Notes | `batch_note` milestones |
| 8 | MVP defer | Cost/revenue math, camera UI, full alarm profiles |

## Flow

```text
acquire_culture (culture_lots)
        ↓
inoculate_batch  → batches.culture_id + container_* + substrate_g
        ↓
advance → incubating → fruiting → harvesting
        ↓
record_harvest (flush) … is_final → complete
```

Culture intro into **media** stays on `media_batches`. Production inoculate links `culture_lots` → `batches` — **no** child culture lot for substrate.

## Services

| Service | Purpose |
| --- | --- |
| `inoculate_batch` | Require known `culture_id`; set container type/count + substrate g/container |
| `advance_production_stage` | `inoculated` → `incubating` → `fruiting` → `harvesting` |
| `record_harvest` | Flush mass (g); `is_final` completes batch |
| `add_batch_note` | Free-text `batch_note` milestone |
| `set_check_reminder` | Persist `expected_check_at` + HA notification |

## Dashboard Production tab

| Control | Entity |
| --- | --- |
| Status | `sensor.communifarm_production_status` |
| Container type | `select.communifarm_container_type` |
| Container count | `number.communifarm_container_count` |
| Substrate g/container | `number.communifarm_substrate_g_per_container` |
| Inoculate | `button.communifarm_inoculate_batch` (uses last acquired culture) |
| Move incubation / fruiting / harvest | `button.communifarm_move_to_*` |
| Harvest mass | `number.communifarm_harvest_mass_g` |
| Record / final harvest | `button.communifarm_record_harvest` / `button.communifarm_final_harvest` |

## Testing

| Stage | Coverage |
| --- | --- |
| T0 | `tests/test_production_inoculate.py` — gates, schema v6, dashboard tab, happy path, unknown culture |
| T1 / T2 | Pending |
