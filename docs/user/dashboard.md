# Dashboard

After Communifarm setup finishes, open **Communifarm** in the sidebar (`/communifarm/overview`).

| Tab | Path | Purpose |
| --- | --- | --- |
| Overview | `/communifarm/overview` | Environment, targets, climate rooms, controls, batch |
| Layout | `/communifarm/climate-layout` | Full-width desktop floor plan. A phone layout is later |
| Climate | `/communifarm/climate-status` | Gauges, 24h history, machine on/off |
| Weigh | `/communifarm/weigh` | Redirect — use **Mix** |
| Mix | `/communifarm/mix` | Standalone mix: focus → drys → water pours → finish / relocate |
| Intake | `/communifarm/intake` | Process modes: **combined** / **mark_tags** / **purchase_intake** (same page; shipment seed + NFC write + purchases) |
| Batches | `/communifarm/batches` | Batch list, complete/new, heat/cooling history |
| Culture | `/communifarm/culture` | Variety catalog CRUD, acquire LC/grain vessels, vessel status |
| Production | `/communifarm/production` | Culture inoculate, incubation/fruiting, batch harvest (shared entities) |
| Harvest | `/communifarm/harvest` | Same batch harvest entities + fridge/bagging SOP (NFC UI later) |
| POS | `/communifarm/pos` | Sale draft, confirm, cleanup |

The overview **Climate** card shows the seeded rooms. See [climate.md](climate.md).

### Weigh session

| Control | Entity |
| --- | --- |
| Recipe scale (0.1–10×) | `number.communifarm_recipe_scale` |
| Batch NFC UID | `sensor.communifarm_batch_nfc_uid` |
| Progress (this batch) | `sensor.communifarm_weigh_session` |
| Ingredient dropdown | `input_select.esp32dev_selected_ingredient` (includes water types) |
| Current mass / tare / record | `esp32dev_*` scale entities |
| Manual weigh (g) | `number.communifarm_manual_weigh_g` (−1 = use scale; 0 = not in recipe; ≥0 overrides) |

First successful weigh-in **auto-records** `dry_mixing_started`. Water target is **10200 g** (summed pours; over-add rejected).

### Mix protocol

| Control | Entity |
| --- | --- |
| Focus (now / last / next) | `sensor.communifarm_mix_protocol` → `focus_text` |
| Dry / water tables | `sensor.communifarm_weigh_session` → `dry_progress_text` / `wet_progress_text` |
| Record water pour | `button.communifarm_record_water_pour` (after Location tare) |
| Field capacity | `sensor.communifarm_field_capacity` |
| Tag source | `select.communifarm_intake_tag_uid` |
| Scan NFC tag | `button.communifarm_apply_tag_source_scan` (applies Tag source → last-NFC) |
| Badge complete next | Tag source → employee → Scan NFC → `button.communifarm_mix_step_from_badge` |
| Relocate (last step) | Storage shelf + bag/batch NFC → `button.communifarm_relocate_for_sterilization` (not badge); bags show on Production → Storage |
| Production placement | `sensor.communifarm_placement_{storage,cold_storage,fruiting_tent,inoculation_tent}` |

See [mixing-batch.md](../process/mixing-batch.md).

### Intake (NFC mark + purchase)

Path: `/communifarm/intake` (alias of former `nfc-write`). SQLite is source of truth after bind; see [nfc-schema.md](../architecture/nfc-schema.md).

| Control | Entity |
| --- | --- |
| Process mode | `select.communifarm_intake_process_mode` (`combined` / `mark_tags` / `purchase_intake`) |
| Tag source | `select.communifarm_intake_tag_uid` |
| Scan mode | `select.communifarm_nfc_scan_mode` |
| Object type | `select.communifarm_nfc_write_object_type` |
| Ingredient / label | `select.communifarm_nfc_write_label` |
| New inventory UUID | `button.communifarm_create_inventory_lot` |
| Prepare / confirm | `button.communifarm_prepare_nfc_write`, `confirm_nfc_write` |
| Status + NDEF | `sensor.communifarm_nfc_write_status` |
| Last resolve context | `sensor.communifarm_nfc_checkin` (attrs: label, zone, amount, `scan_event_id`) |

| Mode | Visible groups |
| --- | --- |
| `combined` | Shipment / mark-tags / purchase (bootstrap) |
| `mark_tags` | Shipment, scanner, write targets |
| `purchase_intake` | Asset purchase only |

### Batches tab

| Control | Entity |
| --- | --- |
| Batch list | `sensor.communifarm_batch_list` (latest **10** batches; state-filtered widgets later) |
| Milestones | `sensor.communifarm_batch_milestones` |
| Complete & new | `button.communifarm_complete_and_new_batch` |
| Completely mixed | `button.communifarm_completely_mixed` |
| Container count | `number.communifarm_container_count` |
| Separate containers | `button.communifarm_separate_containers` |
| Heat method | `select.communifarm_heat_treatment` |
| Record heat treatment | `button.communifarm_heat_treated` |
| Stored for cooling | `button.communifarm_stored_for_cooling` |
| Production start (legacy stub) | `button.communifarm_production_cycle_started` |

### Production tab

Culture → substrate containers. See [production-inoculate.md](../process/production-inoculate.md).

| Control | Entity |
| --- | --- |
| Status summary | `sensor.communifarm_production_status` |
| Container type | `select.communifarm_container_type` |
| Substrate g/container | `number.communifarm_substrate_g_per_container` |
| Inoculate | `button.communifarm_inoculate_batch` |
| Move to incubation | `button.communifarm_move_to_incubation` |
| Move to fruiting | `button.communifarm_move_to_fruiting` |
| Move to harvest | `button.communifarm_move_to_harvest` |
| Harvest mass (g) | `number.communifarm_harvest_mass_g` |
| Record harvest | `button.communifarm_record_harvest` |
| Final harvest | `button.communifarm_final_harvest` |

Acquire a culture first (`acquire_culture` service) so the inoculate button has an `active_culture_id`, or call `inoculate_batch` with an explicit `culture_id`.

### Harvest tab

Same **Harvest** entities as Production (shared card builder). Lifecycle advances stay on **Production**; pick/pack SOP stays here. Per-container NFC services remain; dashboard NFC buttons deferred.

| Validity signal | Where |
| --- | --- |
| Rejects (negative mass, bad labels) | Service error + `last_reject` on session sensor |
| Warnings (capacity, tare, NFC, stuck) | `warnings` / `warning` attrs + progress text |
| Env sensor out of range | `sensor.communifarm_environment_status` = `degraded` |

E2E: `yarn test:e2e:weigh` (exact recipe) · `yarn test:e2e:weigh-variance` (under/over/random ±5% on new batches).

If the sidebar entry is missing after an upgrade, reload the Communifarm integration (or restart Home Assistant) so provisioning can register the Lovelace storage dashboard.

## What you see

| Section | Purpose |
| --- | --- |
| Header | Site, Environment, active batch |
| Current settings | Live temperature and humidity targets |
| Environment | Bound temperature / humidity sensors |
| Targets | Editable temperature (°C) and humidity (%) controls |
| Controls | Allowlisted switch / fan when bound |
| Production | Batch stage (overview) + full Production tab |

## Adjust targets without Settings

Use the **Targets** card on the dashboard (sliders). You do not need Settings → Devices & services for day-to-day target changes.

| Control | Entity | Step |
| --- | --- | --- |
| Temperature target | `number.communifarm_temperature_target` | 0.5 °C |
| Humidity target | `number.communifarm_humidity_target` | 1 % |

Changes persist in Communifarm Store and survive restarts.

## Testing

| Stage | Coverage |
| --- | --- |
| T0 | `test_adjust_targets_minus_one_then_plus_one` nudges temp −1/+1 °C and humidity −1/+1 % |
| T0 | `test_production_inoculate.py` Production tab + inoculate happy path |
| T1 | `e2e/flows/dashboard-targets.spec.ts` (homepage → login → dashboard; OpenBao auto-load) |
| T1 | `e2e/flows/weigh-process.spec.ts` / `weigh-variance.spec.ts` |
