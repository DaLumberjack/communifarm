# Air-exchange tachometer — test cases

Operator doc: `repos/communifarm/docs/hardware/air-exchange-tachometer.md`

Quality oracle: `docs/intermediate/cea-quality-process.md`

## label-vent — register a labeled vent before measuring

When you label a vent (intake/exhaust/circulation), these tests verify Communifarm stores a stable vent id and rejects empty/invalid roles.

| field | value |
|-------|-------|
| CQA | Airflow measurements stay attributable to a physical vent |
| CPP / gate | Non-empty label ≤ 64 chars; role in intake/exhaust/circulation/other |
| acceptance | Upsert returns vent with label/role; invalid label/role raises |
| flaw this case is built to catch | Silent blank labels or free-text roles that break later joins |
| loop | `none` |
| stage | T0 |
| pytest or spec | `tests/test_tachometer.py::test_domain_validators_reject_bad_inputs`, `tests/test_tachometer.py::test_upsert_updates_existing_vent_by_label_and_id` |
| pass means | Vent labels are normalized and reusable across readings |
| pass does not mean | Live tach hardware accuracy |

## record-reading — timestamped value per vent

When you record RPM/CFM/FPM with an optional ISO timestamp, these tests verify an append-only reading lands and the status sensor updates.

| field | value |
|-------|-------|
| CQA | Air-exchange samples are contemporaneous and queryable |
| CPP / gate | value ≥ 0; unit in rpm/cfm/fpm; vent_id or vent_label present |
| acceptance | Reading stored; sensor shows last vent/value; negative rejected |
| flaw this case is built to catch | Missing vent identity, negative values accepted, or sensor not refreshed |
| loop | `process` |
| stage | T0 |
| pytest or spec | `tests/test_tachometer.py::test_actions_and_services_record_and_update_sensor`, `tests/test_tachometer.py::test_rejects_negative_value` |
| pass means | Manual handheld measurements persist in SQLite and surface in HA |
| pass does not mean | ACH calculation or live GPIO tachometer |

## schema-v13 — upgrade keeps prior production rows

When schema migrates through v13, prior batch/placement rows survive and vent tables appear.

| field | value |
|-------|-------|
| CQA | Historical production data is not wiped by airflow logging |
| CPP / gate | Additive migration only |
| acceptance | SCHEMA_VERSION == 13; batch/area rows intact; air_vents present |
| flaw this case is built to catch | Migration that drops or rewrites unrelated tables |
| loop | `none` |
| stage | T0 |
| pytest or spec | `tests/test_climate.py::test_schema_v13_upgrade_preserves_v11`, `tests/test_tachometer.py::test_schema_v13_creates_tachometer_tables` |
| pass means | Upgrade path keeps grow history |
| pass does not mean | T2 container upgrade was run |
