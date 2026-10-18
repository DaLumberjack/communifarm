# Mixing batch — test cases

Operator doc: `repos/communifarm/docs/process/mixing-batch.md`

Quality oracle: `docs/intermediate/cea-quality-process.md`

## INV1 — new UUID for same ingredient name

When you create a second inventory lot with the same label (e.g. hardwood pellets), these tests verify each bag gets a distinct Communifarm UUID and NDEF identity.

| field | value |
|-------|-------|
| CQA | Lot identity / traceability |
| CPP / gate | Label required; readable length |
| acceptance | Two lots, same label, different `stable_id` |
| flaw this case is built to catch | Reusing one UUID for every bag with the same name |
| loop | none |
| stage | T0 |
| pytest or spec | `tests/test_inventory_nfc.py::test_create_inventory_lot_new_uuid_same_name` |
| pass means | Operators can track two oak-pellet bags separately into a mix |
| pass does not mean | Live PN532 NDEF write or OpenBao sync |
| related batches | Mix batch that consumes either lot |

### Setup

Configured Communifarm entry; no prior lots required.

### Steps

1. `create_inventory_lot` label `hardwood pellets`.
2. Repeat with the same label.
3. (Reject) Confirm write without prepare.

### Expected record

| object | field | expected |
|--------|-------|----------|
| inventory_lots | count for key | ≥ 2 |
| inventory_lots | ids | distinct |
| confirm without prepare | error | no bind |

## W1 — water sum and over-add reject

When you record water pours toward 10200 g, these tests verify pours sum and over-add is rejected.

| field | value |
|-------|-------|
| CQA | Substrate moisture / field capacity prep |
| CPP / gate | Water target 10200 g × scale; ≤ target × 1.05 |
| acceptance | Summed close at 10200; reject projected over-add |
| flaw this case is built to catch | Latest pour overwrites prior water; silent over-soak |
| loop | process |
| stage | T0 |
| pytest or spec | `tests/test_mix_protocol.py::test_water_pours_sum_toward_target`, `::test_record_weight_rejects_water_overadd` |
| pass means | Operators cannot silently exceed the water budget |
| pass does not mean | Live capacitance calibration for a specific salt load |
| related batches | Active mix batch |

## M1 — badge checkpoint after dry weigh

When you scan an employee badge during mixing, these tests verify the next open protocol milestone is recorded and dry weigh is required first.

| field | value |
|-------|-------|
| CQA | Contemporaneous batch record / step order |
| CPP / gate | All dry recipe lines recorded before badge checkpoints |
| acceptance | First badge → `drys_combined`; second → `water_added`; empty weigh → error |
| flaw this case is built to catch | Badge marks success before drys are weighed; duplicate same milestone |
| loop | process |
| stage | T0 |
| pytest or spec | `tests/test_mix_protocol.py::test_badge_completes_next_mix_milestone`, `::test_badge_rejects_when_drys_not_weighed` |
| pass means | Proficient operators can badge-scan through Mix in order |
| pass does not mean | Live handheld NFC hardware |
| related batches | Active mix batch |

## D1 — Mix vs Weigh dashboards

When you open Communifarm after setup, these tests verify Weigh stays scale-focused and Mix carries the ordered protocol.

| field | value |
|-------|-------|
| CQA | Operator clarity |
| CPP / gate | Dashboard provision |
| acceptance | `/mix` has ordered steps; `/weigh` has no mix milestone card; `/nfc-write` exists |
| flaw this case is built to catch | Protocol buried on the general scale tab |
| loop | none |
| stage | T0 |
| pytest or spec | `tests/test_dashboard.py::test_dashboard_includes_mix_and_nfc_write_tabs`, `::test_dashboard_includes_weigh_tab_with_scale_and_nfc` |
| pass means | Task UI is separated from weights & measures |
| pass does not mean | Playwright layout polish |
| related batches | n/a |

### Sources

- `docs/process/mixing-batch.md`
- `docs/intake/mushroom data/recipe.md`
