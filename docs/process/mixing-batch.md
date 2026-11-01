# Mixing batch (hardwood substrate)

Operator process for bulk substrate mixing using the Simpler Wood Lover recipe.

Quality oracle: `docs/intermediate/cea-quality-process.md`

## Flow

| Step | How | Record |
| --- | --- | --- |
| Weigh dry ingredients | **Weigh** tab (manual select ~50% or NFC scan ~95%) | `weight_events` + `sensor.communifarm_weigh_session` |
| Mix all drys | **Mix** button or employee badge | `drys_combined` |
| Add water (first pour) | Weigh water type + Mix checkpoint | `water_added` + water `weight_events` |
| Incorporate | Mix / badge | `dry_wet_mix_started` |
| Add remaining water | Weigh (summed toward 10200 g) | `remaining_water_added` |
| Incorporate | Mix / badge | `settling_started` |
| Field capacity | Capacitance sensor + button | `field_capacity_reached` |
| Completely mixed | Mix / badge | `completely_mixed` |
| Bag / bin | Container count + separate | `containers_separated` |
| Relocate for sterilization | Bag NFC + location NFC | `relocated_for_sterilization` |

## Manual weigh (scale fallback)

| value | meaning |
| --- | --- |
| **−1** (default) | Omit — `record_weight` uses live `sensor.esp32dev_calibrated_g` |
| **0** | Ingredient not in this recipe / zero pour (recorded) |
| **> 0** | Override scale (broken scale, post-tare stuck at 0, sandbox) |

Entity: `number.communifarm_manual_weigh_g`. Assess / recipe logic is unchanged — only the mass **source** swaps. After a successful manual record or tare, the number resets to −1.

## Water

| rule | detail |
| --- | --- |
| Recipe mass | **10200 g** total (`water` line) |
| NFC / select variants | tap, filtered, warm tap, warm filtered — all map to key `water` |
| Over-add | rejected above target × 1.05 |
| Pours | first + remaining **sum** toward the target |

Salts skew capacitance. Calibrate `sensor.cf_mixroom_field_capacity_pct` band (default 40–70%) for this substrate before trusting auto field-capacity signals.

## NFC inventory

Same display name may have many lots (e.g. two oak pellet bags). Each lot has its own Communifarm UUID; the physical chip UID binds to that lot. NDEF carries typed identity JSON (`cf://inventory/<id>`).

Write station: `/communifarm/nfc-write`.

## Dashboards

| Tab | Role |
| --- | --- |
| Mix | Standalone process: focus → drys → water pours (location tare) → finish |
| Weigh | Redirects to Mix |
| Intake | Purchases + NFC write sections (asset / location / bag / machine / culture / batch / employee) |

**Relocate for sterilization (last step):** pick a **Storage** shelf on Mix, then **Relocate for sterilization**. Bags land in Storage (awaiting culture) and appear on **Production → Storage**. Badge cannot finish this step. Active **batch NFC** is enough when no bag tag exists yet; bag/bin tags preferred.

**Sandbox NFC / badge checkpoints:** **Seed shipment NFC tags** (Intake) → Mix **Tag source** → **Scan NFC tag** → **Badge: complete next checkpoint**. For employee milestones pick `nfc-employee-01`.

**Production blocks:** Tag source → bag UID → **Register tag source as production block**.

| Env | Fake HA sensors? |
| --- | --- |
| Sandbox (`devcontainer/ha_config/packages/`) | **Yes** — `input_select.cf_sandbox_shipment_nfc_uid`, last-NFC helpers, simulate buttons |
| Production integration | **No** — only bind/import from real ESPHome last-NFC entities |

## Test cases

See [test-cases/mixing-batch.md](./test-cases/mixing-batch.md).

## Sources

- Intake recipe: `docs/intake/mushroom data/recipe.md` (Fungaia Life Simpler Wood Lover)
- Deferred weigh notes: `docs/intermediate/weigh-station-process-deferred.md`
