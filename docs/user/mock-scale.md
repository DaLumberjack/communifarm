# Mock esp32dev scale (local T1/T2)

Local Home Assistant in the Communifarm devcontainer mocks the live ESPHome scale using **the same public entity IDs** as the device shown in production-adjacent HA (`esp32dev`). Process logic can bind once and run against mocks first.

| Item | Value |
| --- | --- |
| Package | `devcontainer/ha_config/packages/mock_esp32dev_scale.yaml` |
| Intake YAML (do not commit secrets/pins) | workspace `docs/intake/esp devices/scale.yaml` |
| Recipe intake | workspace `docs/intake/mushroom data/recipe.md` |
| Default mode | **Mocks** for code/logic flows |

## Live-shaped entities

| Live-style entity | Role |
| --- | --- |
| `sensor.esp32dev_calibrated_g` / `_g` / `_calibration_value` | Net grams after tare |
| `sensor.esp32dev_calibrated_sensor` | Gross calibrated reading (pre-tare) |
| `sensor.esp32dev_raw` / `_raw_scale_value` | Raw HX711-style counts |
| `sensor.esp32dev_tared_mass_on_scale` | Current tare offset |
| `sensor.esp32dev_temperature` / `_humidity` / `_pressure` | BME280-style env |
| `sensor.esp32dev_last_recorded` | Last recorded mass (numeric parse of text) |
| `button.esp32dev_tare` / `_location_tare` | Capture tare |
| `button.esp32dev_record_weight` | Persist reading (+ selected ingredient) |
| `number.esp32dev_scale_base_weight` | Platform base (default 735 g) |
| `number.esp32dev_scale_weightless_calibration` | Cal number |

Inject-only helpers (`input_number.esp32dev_inject_*`, etc.) are mock scaffolding — not present on live ESPHome.

## NFC stub (option B)

| Entity | Purpose |
| --- | --- |
| `input_select.esp32dev_selected_ingredient` | Dropdown of recipe ingredients (scan result) |
| `input_text.esp32dev_last_nfc_uid` | Mock tag UID (shared with Communifarm harvest resolve) |
| `input_button.esp32dev_simulate_nfc_scan` | Apply UID → **recipe ingredient** map (weigh only) |

Record Weight appends `| <ingredient>` when a selection other than `(none)` is active.

Example UIDs already mapped: `nfc-hardwood-pellets`, `nfc-gypsum`, … (see package automation).

**Production inoculum:** set `input_text.esp32dev_last_nfc_uid` to a culture tag, then press **Select inoculum from NFC scan** on the Production tab (or pick **Active inoculum** in the dropdown). Do **not** use `simulate_nfc_scan` — that maps weigh ingredients only.

**Harvest / POS:** set the same `input_text` to a container UID (`cont_*` from inoculate), then Harvest check-in / confirm. Playwright: `yarn test:e2e:t1:pos`.

## How to drive the mock

```bash
# After HA is up (and OpenBao login for Playwright if needed):
# Developer Tools → Services, or e2e helpers in e2e/helpers/mock-scale.ts

# Set gross calibrated mass
input_number.set_value → input_number.esp32dev_inject_calibrated_sensor

# Select ingredient (simulates NFC without UID map)
input_select.select_option → input_select.esp32dev_selected_ingredient

# Or NFC path:
input_text.set_value → input_text.esp32dev_last_nfc_uid = nfc-hardwood-pellets
input_button.press → input_button.esp32dev_simulate_nfc_scan

button.press → button.esp32dev_tare
button.press → button.esp32dev_record_weight
```

## Mocks vs live devices (read this before “just plug ESPHome into Docker”)

| Question | Answer for Communifarm |
| --- | --- |
| Are mocks enough for now? | **Yes** — code flow, entity contracts, tare/record/NFC-select logic. |
| Can the devcontainer HA talk to a real ESPHome node? | **Yes, technically** — if the container can reach the device on the LAN (API encryption key, same Wi‑Fi/VLAN/routing). It is not “magic”; networking and secrets must be deliberate. |
| Should we use the *production* scale in the devcontainer? | **No** — avoid reflashing / stealing the floor scale. Prefer **dedicated lab hardware** (same as the test HA VM policy). |
| When do we use live devices? | Special cases: calibration math, HX711 noise, real NFC reads, human process timing — usually **T3 test VM** or a **future dedicated lab scale**, not day-to-day T1. |
| Human process flow (recipe walk-through)? | **Deferred** — see workspace `docs/intermediate/weigh-station-process-deferred.md`. Ship mocks + contracts first. |

### Later completion (not this branch)

1. Dedicated ESPHome scale + NFC reader inventory for **lab/devcontainer** (separate from floor production gear).
2. Communifarm process UI: recipe steps → expect NFC → prompt tare → record weight → next ingredient.
3. Bind live entity registry IDs on T3; keep mock package as the T1 default.
4. Redact/move intake `scale.yaml` secrets (API/OTA keys) into OpenBao; never commit live keys.

## Dashboard Weigh tab

Communifarm Lovelace includes a **Weigh** view (`/communifarm/weigh`) with:

| Card | Entities / content |
| --- | --- |
| Recipe scale | `number.communifarm_recipe_scale`, batch NFC UID, session sensor |
| This session | Markdown from `progress_text` (scaled targets vs last recorded per line) |
| Live reading | Current / gross / selected / last recorded |
| Ingredient (NFC) | `input_select.esp32dev_selected_ingredient` |
| Scale | tare / location tare / record |

**Record weight** writes `weight_events` (with `recipe_scale` + `target_amount`) and refreshes the session sensor. Negative mass is rejected; over-capacity and other suspect readings warn on `sensor.communifarm_weigh_session`. See [storage.md](storage.md).

### Mock inject for validity (C12)

Use the same inject helpers to exercise reject/warn paths in T1:

| Scenario | How |
| --- | --- |
| Over capacity | set calibrated mass &gt; 100000 g then record |
| Missing NFC | select ingredient, clear `input_text.esp32dev_last_nfc_uid`, record |
| Tare skipped | record without pressing tare first |
| Env degraded | set `sensor.mock_temperature` outside -40…80 °C |

### Full recipe weigh process (E2E)

`yarn test:e2e:weigh` runs `e2e/flows/weigh-process.spec.ts`: for each Wood Lover line — NFC scan → tare mix bin → set mass → record — then asserts `sensor.communifarm_weigh_session` is `9/9 lines recorded` with every line non-pending.

Reload Communifarm after upgrade so the dashboard model re-provisions.

