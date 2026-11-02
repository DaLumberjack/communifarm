# Operator personas — test cases

Operator docs: [mixing-batch.md](../mixing-batch.md), [production-inoculate.md](../production-inoculate.md)

Quality oracle: `docs/intermediate/cea-quality-process.md`

Two operator modes share the same services. Tests prove both paths write the same batch record shape.

| persona | automation | operator rhythm |
|---------|------------|-----------------|
| **95%** | Live NFC + last-scan helper | Scan asset/bag/location → press the process button |
| **40%** | Tag source dropdown + Scan NFC | Select UID → Scan NFC tag → press button / next |

## OP1 — 95% scan then press (single bag)

When a bag is on the last-NFC helper and Tag source is `(last scanned)`, Move to incubation advances **only that bag**.

| field | value |
|-------|-------|
| CQA | Per-bag move audit |
| CPP / gate | Container NFC resolves on active batch |
| acceptance | Scanned bag → incubating; sibling stays inoculated |
| flaw this case is built to catch | Press always moves entire batch even when a bag was scanned |
| loop | iteration |
| stage | T0 |
| pytest or spec | `tests/test_operator_personas.py::test_persona_95_scan_then_press_moves_only_scanned_bag` |
| pass means | Scan-first operators can pull one bag from Storage |
| pass does not mean | Dedicated handheld scan UI |
| related batches | Active inoculated batch |

## OP2 — 40% dropdown then scan then press

When Tag source is a bag UID and Scan NFC is pressed, the same single-bag advance applies without passing `nfc_uid` on the service.

| field | value |
|-------|-------|
| CQA | Manual station parity with scan-first |
| CPP / gate | Tag source → apply_tag_source_scan → advance |
| acceptance | Selected bag incubating; sibling unchanged |
| flaw this case is built to catch | Dropdown choice ignored; only live PN532 works |
| loop | process |
| stage | T0 |
| pytest or spec | `tests/test_operator_personas.py::test_persona_40_dropdown_scan_then_press_moves_selected_bag` |
| pass means | Partial-automation stations stay usable |
| pass does not mean | Soft keys on ESPHome |
| related batches | Active inoculated batch |

## OP3 — No bag context → entire batch

When last NFC is empty and Tag source is last-scanned, Move advances **all** active bags (4B).

| field | value |
|-------|-------|
| CQA | Whole-batch relocate still works |
| CPP / gate | No container resolution |
| acceptance | Both bags incubating |
| flaw this case is built to catch | Empty scan blocks advance forever |
| loop | process |
| stage | T0 |
| pytest or spec | `tests/test_operator_personas.py::test_persona_95_no_scan_press_moves_entire_batch` |
| pass means | Operators can move a whole batch without bag tags |
| pass does not mean | Silent identity mix across batches |
| related batches | Active inoculated batch |

## OP4 — Non-container Tag source does not fake a bag move

Employee (or other non-container) Tag source must not scope advance to one bag.

| field | value |
|-------|-------|
| CQA | Identity type integrity |
| CPP / gate | Only `object_type=container` scopes to one unit |
| acceptance | Both bags incubating |
| flaw this case is built to catch | Badge UID treated as bag container_id |
| loop | none |
| stage | T0 |
| pytest or spec | `tests/test_operator_personas.py::test_persona_40_non_container_tag_does_not_scope_to_one_bag` |
| pass means | Wrong dropdown type fails closed into whole-batch, not a wrong bag |
| pass does not mean | Employee badge completes relocate |
| related batches | Active inoculated batch |

## OP5 — Badge cannot finish relocate; Storage relocate required

At Mix 10/10, badge rejects; Storage shelf + Relocate succeeds.

| field | value |
|-------|-------|
| CQA | Contemporaneous move to Storage awaiting culture |
| CPP / gate | Relocate location = Storage; badge blocked |
| acceptance | Milestone `relocated_for_sterilization`; bags in Storage inventory |
| flaw this case is built to catch | Badge marks relocate done without Storage placement |
| loop | process |
| stage | T0 |
| pytest or spec | `tests/test_operator_personas.py::test_persona_badge_rejects_when_checkpoints_done_use_relocate` |
| pass means | Mix finish lands bags where Production → Storage can see them |
| pass does not mean | Live sterilization hardware |
| related batches | Active mix batch |

### Sources

- `docs/process/mixing-batch.md`
- `docs/process/production-inoculate.md`
- `docs/intermediate/cea-quality-process.md`
