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
| NFC Write | Register + write bag/bin / ingredient / location tags |

**Relocate for sterilization:** scan at least one bag/bin (or batch) NFC, then press the button. That milestone documents the **entire batch** moved. Location tag optional.

## Test cases

See [test-cases/mixing-batch.md](./test-cases/mixing-batch.md).

## Sources

- Intake recipe: `docs/intake/mushroom data/recipe.md` (Fungaia Life Simpler Wood Lover)
- Deferred weigh notes: `docs/intermediate/weigh-station-process-deferred.md`
