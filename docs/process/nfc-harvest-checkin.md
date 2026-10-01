# NFC resolve / check-in harvest

Per-container harvest with handheld NFC. Tags hold **stable IDs only**; Communifarm SQLite stores stage, flush count, and placement.

| Item | Value |
| --- | --- |
| Schema | v9 |
| Services | `resolve_nfc`, `check_in`, `bind_nfc`, `record_container_harvest` |
| Dashboard | **Harvest** tab |
| Scanner entity | `input_text.esp32dev_last_nfc_uid` |

## Flow

1. Scan the production block with the handheld reader.
2. Press **NFC check-in harvest** (or call `check_in` with `activity: harvest`).
3. Cut, weigh the flush, set harvest mass (g).
4. Press **Confirm container harvest** (`confirm=true` required).
5. Non-final flush → container returns to **fruiting**; optional `zone_id` records which tent level it went back to.
6. Repeat for ready containers. Final harvest completes that container; when all containers complete, the batch completes.

## Fridge / bagging (small residential fridge)

| Do | Don't |
| --- | --- |
| Bag ASAP in **paper / vented** packs | Seal wet mushrooms in plastic |
| Store on **main shelves** | Use the crisper drawer |
| Leave air gap; don't overpack | Wash before storage |
| Aim to sell/use in 3–5 days | Leave warm bags stacked until they sweat |

`sale_packs` can reference a `harvest_id` with a freeform `size_label`. Sale recipient labeling is deferred.

## Bind physical tags

After inoculate, each container gets a Communifarm `nfc_uid` (defaults to its `stable_id`). To attach a real chip UID:

```yaml
service: communifarm.bind_nfc
data:
  object_type: container
  object_id: cont_…
  # nfc_uid optional — defaults to last handheld scan
```

## Placement trends

Pass `zone_id` on `check_in` (move/harvest) or `record_container_harvest` so yield can be correlated with fruiting-tent level/shelf later.

## Testing

| Stage | Coverage |
| --- | --- |
| T0 | `tests/test_nfc_harvest.py` |
| T1/T2 | Pending |
