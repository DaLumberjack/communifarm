# Dashboard

After Communifarm setup finishes, open **Communifarm** in the sidebar (`/communifarm/overview`).

| Tab | Path | Purpose |
| --- | --- | --- |
| Overview | `/communifarm/overview` | Environment, targets, controls, batch |
| Weigh | `/communifarm/weigh` | Recipe scale, session progress from SQLite, NFC select, tare/record |

### Weigh session

| Control | Entity |
| --- | --- |
| Recipe scale (0.1–10×) | `number.communifarm_recipe_scale` |
| Batch NFC UID | `sensor.communifarm_batch_nfc_uid` |
| Progress (this batch) | `sensor.communifarm_weigh_session` |
| Ingredient dropdown | `input_select.esp32dev_selected_ingredient` |
| Current mass / tare / record | `esp32dev_*` scale entities |

Session table lists each recipe line’s **scaled target**, last recorded value, and closeness — enough to see what’s done without dumping full DB history. Gauges later.

| Validity signal | Where |
| --- | --- |
| Rejects (negative mass, bad labels) | Service error + `last_reject` on session sensor |
| Warnings (capacity, tare, NFC, stuck) | `warnings` / `warning` attrs + progress text |
| Env sensor out of range | `sensor.communifarm_environment_status` = `degraded` |

If the sidebar entry is missing after an upgrade, reload the Communifarm integration (or restart Home Assistant) so provisioning can register the Lovelace storage dashboard. A prior bug left the config only in memory — fixed by creating the real storage dashboard.

## What you see

| Section | Purpose |
| --- | --- |
| Header | Site, Environment, active batch |
| Current settings | Live temperature and humidity targets |
| Environment | Bound temperature / humidity sensors |
| Targets | Editable temperature (°C) and humidity (%) controls |
| Controls | Allowlisted switch / fan when bound |
| Production | Batch stage |

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
| T1 | `e2e/flows/dashboard-targets.spec.ts` (homepage → login → dashboard; OpenBao auto-load) |
