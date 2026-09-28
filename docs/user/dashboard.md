# Dashboard

After Communifarm setup finishes, open **Communifarm** in the sidebar (`/communifarm/overview`).

| Tab | Path | Purpose |
| --- | --- | --- |
| Overview | `/communifarm/overview` | Environment, targets, controls, batch |
| Weigh | `/communifarm/weigh` | Scale, NFC, recipe scale, session progress, mix milestones |
| Batches | `/communifarm/batches` | Batch list, complete/new, post-weigh mix process |
| Production | `/communifarm/production` | Culture inoculate, incubation/fruiting, harvest |

### Weigh session

| Control | Entity |
| --- | --- |
| Recipe scale (0.1–10×) | `number.communifarm_recipe_scale` |
| Batch NFC UID | `sensor.communifarm_batch_nfc_uid` |
| Progress (this batch) | `sensor.communifarm_weigh_session` |
| Ingredient dropdown | `input_select.esp32dev_selected_ingredient` |
| Current mass / tare / record | `esp32dev_*` scale entities |
| Added water | `button.communifarm_water_added` |
| Started dry/wet mix | `button.communifarm_dry_wet_mix_started` |
| Settling | `button.communifarm_settling_started` |
| Field capacity | `button.communifarm_field_capacity_reached` |

First successful weigh-in **auto-records** `dry_mixing_started`.

### Batches tab

| Control | Entity |
| --- | --- |
| Batch list | `sensor.communifarm_batch_list` |
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
