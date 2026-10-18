# Manual fan tachometer / air exchange

Operators measure each vent with a handheld tachometer (or anemometer), label the vent, stamp the time, and store the value in Communifarm SQLite. This is the basic / reliable-home path: a measurement trail before ACH math or GPIO tach hardware.

| Item | Value |
| --- | --- |
| Schema | v13 (`air_vents`, `tachometer_readings`) |
| Services | `communifarm.upsert_air_vent`, `communifarm.record_tachometer` |
| Status sensor | `sensor.communifarm_tachometer_status` |
| T1 helpers | `devcontainer/ha_config/packages/mock_cf_tachometer.yaml` |
| Evidence digest | workspace `docs/intermediate/air-exchange-measurement.md` |
| Test cases | [air-exchange-tachometer.md](../process/test-cases/air-exchange-tachometer.md) |

## Why manual first

GPIO pulse tachometers can come later on AIO868 / ESP nodes. Semi-frequent air-exchange checks need a labeled vent log that works with a laser tach or vane anemometer today. Fan on/off schedules are not proof of air speed at the crop.

## Choose a level

| level | what you do | Communifarm use |
| --- | --- | --- |
| basic | Label vents; log when air smells stale or CO2 looks high | Any unit; services above |
| reliable home | Same vents on a schedule; prefer CFM | Compare readings over time on the status sensor |
| advanced clean | Re-measure after layout or filter changes | Treat readings as commissioning evidence |
| lab-quality CEA | Calibrated meter, duct area, ACH tied to batch CPP records | Enter volume + CFM on Climate settings; compare progress to τ |

## Workflow

| Step | Action |
| --- | --- |
| 1 | Label the vent once (`Fruiting intake left`, `Inoculation exhaust`, …) via **Upsert air vent** or the mock helpers |
| 2 | Set **Vent role** (`intake` / `exhaust` / `circulation` / `other`) |
| 3 | Optionally set **Timestamp** (ISO). Blank = now |
| 4 | Enter **Value** and **Unit** (`rpm`, `cfm`, or `fpm`) |
| 5 | Press **Record Reading** |

`record_tachometer` with only `vent_label` creates the vent if needed.

## Units

| Unit | Use |
| --- | --- |
| `rpm` | Fan shaft / sticker tachometer |
| `cfm` | Direct airflow (preferred for air-exchange math later) |
| `fpm` | Face velocity; convert with duct area later |

ACH estimates live in climate automation when the same enclosure has **volume_m³** and intake/exhaust **CFM** commissioned (`docs/user/climate.md`). Prefer logging CFM here so those settings stay truthful. RPM-only logs still help trend fans but do not drive ACH until converted.

## Purchase Checklist

| have | item | level | why | lower-cost substitute | upgrade path |
| --- | --- | --- | --- | --- | --- |
| [ ] | Handheld laser tachometer (RPM) | basic | Shaft/sticker readings when CFM is unavailable | Phone tach app (higher variance) | Vane anemometer with CFM |
| [ ] | Vane or hot-wire anemometer | reliable home | Face velocity / CFM for exchange checks | Laser tach + duct-area estimate | Calibrated lab anemometer |
| [ ] | Durable vent labels | basic | Stable identity across readings | Marker on tape | Engraved tags keyed to `air_vents` |
| [ ] | Notebook or HA helpers for each reading | reliable home | Timestamp + unit discipline | Status sensor only | Lab-quality CEA batch CPP form |
| [ ] | Room volume note (L×W×H) | advanced clean | Future ACH from CFM | Skip until CFM is routine | Commissioned ACH targets |

## Minimal Process Upgrades

| current setup | smallest upgrade | failure mode reduced | why this first | source |
| --- | --- | --- | --- | --- |
| No airflow record | Label vents + log CFM/RPM in Communifarm | Unattributable “felt weak” anecdotes | Measurement before more fans or GPIO | Operator need; V1 |
| Duty-cycle fans only | Record face velocity after fruiting layout changes | Treating on/off as proven crop airflow | Literature air-speed targets need a meter | V4 |
| Absolute-pressure dashboard only | Keep pressure as display; measure vents separately | False confidence in room balance | Differential pressure needs calibration | V1 + operator climate policy |
| Waiting on AIO868 pulse tach | Keep manual path; do not guess relay/tach pins | Blocked logging for missing hardware | Pin maps unpublished until verified | ESPHome device policy |

## Devcontainer helpers

| Helper | Entity |
| --- | --- |
| Vent label | `input_text.cf_tach_vent_label` |
| Role | `input_select.cf_tach_vent_role` |
| Value | `input_number.cf_tach_value` |
| Unit | `input_select.cf_tach_unit` |
| Timestamp | `input_text.cf_tach_recorded_at` |
| Upsert vent | `input_button.cf_tach_upsert_vent` |
| Record | `input_button.cf_tach_record_reading` |

## Testing

| Stage | Coverage |
| --- | --- |
| T0 | `tests/test_tachometer.py` — case file: [air-exchange-tachometer.md](../process/test-cases/air-exchange-tachometer.md) |
| T1 | mock package + services once Communifarm is configured |
| T2/T3 | skipped until version bump / live vents requested |

## Sources

| Claim | Source |
| --- | --- |
| Semi-frequent labeled vent log before GPIO tach | Operator need; this doc |
| Ventilation demand changes with crop load; uniform movement avoids high-CO2 pockets | Penn State Extension, *Basic Procedures for Agaricus Mushroom Growing* |
| Fruiting Pleurotus more CO2-sensitive; stage-aware ventilation | Zhang et al., 2022, PMCID PMC9321156 |
| Tested Pleurotus air-velocity result of 0.3 m/s (commissioning target, not duty-cycle proof) | Oh et al., *Journal of Mushrooms*, 2019 |
| Intake digest | workspace `docs/intake/2026-10-06-cea-ventilation-occupancy-controls.md` (V1, V3, V4) |
| Intermediate digest | workspace `docs/intermediate/air-exchange-measurement.md` |
| Climate control context | [climate.md](../user/climate.md), ADR 0004 |
