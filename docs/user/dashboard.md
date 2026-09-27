# Dashboard

After Communifarm setup finishes, open **Communifarm** in the sidebar (`/communifarm/overview`).

| Tab | Path | Purpose |
| --- | --- | --- |
| Overview | `/communifarm/overview` | Environment, targets, controls, batch |
| Weigh | `/communifarm/weigh` | Scale mass, tare, NFC ingredient select, record weight |

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
