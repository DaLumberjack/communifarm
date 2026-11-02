# Ops scheduling — test cases

Operator doc: `docs/intermediate/ops-scheduling.md`

Quality oracle: `docs/intermediate/cea-quality-process.md`

## OS1 — Project incubating → fruiting

When a container is incubating, projection names fruiting + fruiting_tent with a due time.

| field | value |
|-------|-------|
| CQA | Operators see the next move before it is overdue |
| CPP / gate | `lifecycle_phase == incubating` |
| acceptance | `to_phase == fruiting`, suggested area `fruiting_tent` |
| flaw this case is built to catch | Hard-coding fruiting without using STAGE_TRANSITIONS / STAGE_SUGGESTED_AREA_KIND |
| loop | `none` |
| stage | T0 |
| pytest or spec | `tests/test_ops_schedule.py::test_project_incubating_to_fruiting_uses_dwell` |
| pass means | Projection uses dwell or expected_check_at |
| pass does not mean | Live hardware or species-correct colonization days |
| related batches | All incubating containers |

## OS2 — P2 when incubation due

| field | value |
|-------|-------|
| CQA | Overdue incubating stock is visible as P2 |
| CPP / gate | `now >= due_at` |
| acceptance | Alarm code `move_incubating_to_fruiting`, priority `p2` |
| flaw this case is built to catch | Firing P2 before due |
| loop | `none` |
| stage | T0 |
| pytest or spec | `tests/test_ops_schedule.py::test_p2_when_incubation_due` / `test_no_p2_before_incubation_due` |
| pass means | Due gate is deterministic |
| pass does not mean | Provisional dwell hours are process-locked |

## OS3 — P3 light continuous overrun

| field | value |
|-------|-------|
| CQA | Continuous light/UV on-time is flagged |
| CPP / gate | `light_on` and continuous hours > max |
| acceptance | Alarm code `light_on_exceeds_hours`, priority `p3` |
| flaw this case is built to catch | Alarm while light off or recently turned on |
| loop | `control` |
| stage | T0 |
| pytest or spec | `tests/test_ops_schedule.py::test_p3_when_light_continuous_exceeds_max` / `test_no_p3_when_light_off_or_recent` |
| pass means | Overrun class works for ROLE_LIGHT |
| pass does not mean | Distinct UV role binding exists |

## Sources

- `docs/intermediate/ops-scheduling.md`
- ADR 0007
