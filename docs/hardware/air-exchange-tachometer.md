# Manual fan tachometer / air exchange

Operators measure each vent with a handheld tachometer (or anemometer), label the vent, stamp the time, and store the value in Communifarm SQLite.

| Item | Value |
| --- | --- |
| Schema | v13 (`air_vents`, `tachometer_readings`) |
| Services | `communifarm.upsert_air_vent`, `communifarm.record_tachometer` |
| Status sensor | `sensor.communifarm_tachometer_status` |
| T1 helpers | `devcontainer/ha_config/packages/mock_cf_tachometer.yaml` |

## Why manual first

GPIO pulse tachometers can come later on AIO868 / ESP nodes. Semi-frequent air-exchange checks need a labeled vent log that works with a laser tach or vane anemometer today.

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

ACH / room-volume math is deferred. Store the raw samples first.

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

- Operator need: measure air exchange per labeled vent
- Climate control context: `docs/user/climate.md`, ADR 0004
