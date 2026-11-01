# Production inoculate — test cases

Operator doc: `repos/communifarm/docs/process/production-inoculate.md`

Quality oracle: `docs/intermediate/cea-quality-process.md`

## P1 — Storage inventory after Mix relocate

When bags relocate from Mix, Production → Storage must list zone, batch, unit, stage, NFC.

| field | value |
|-------|-------|
| CQA | Know which bags await culture |
| CPP / gate | Relocate lands in Storage; container `zone_id` set |
| acceptance | Placement storage sensor count ≥ 1; cold storage empty for that bag |
| flaw this case is built to catch | Batch zone set but containers stay unzoned / wrong area |
| loop | process |
| stage | T0 |
| pytest or spec | `tests/test_placement_inventory.py::test_relocate_lands_containers_in_storage_section` |
| pass means | Operator sees ready bags in Storage |
| pass does not mean | Live tent capacity UI |
| related batches | Post-mix batches |

## P2 — Move to incubation with optional bag NFC

When Tag source / `nfc_uid` is a bag, only that container advances and relocates; otherwise whole batch.

| field | value |
|-------|-------|
| CQA | Per-bag move audit |
| CPP / gate | Container NFC on active batch |
| acceptance | Scanned bag → incubating + inoculation-tent zone; sibling bag unchanged |
| flaw this case is built to catch | Button always moves every bag even when one bag was scanned |
| loop | iteration |
| stage | T0 |
| pytest or spec | `tests/test_placement_inventory.py::test_advance_with_bag_nfc_moves_only_that_container` |
| pass means | Partial pulls from Storage are trackable |
| pass does not mean | Dedicated scan UX (Tag source until scan process lands) |
| related batches | Active inoculated batch |

### Sources

- `docs/process/production-inoculate.md`
- `docs/process/mixing-batch.md`
