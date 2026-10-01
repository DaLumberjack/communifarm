# Point of sale / sales tracking

General (non-GAP) sales tracking after harvest. Operators log venue, buyer, payment, and sold mass; Communifarm stores rows for analysis and tax-prep handoff.

| Item | Value |
| --- | --- |
| Schema | v10 |
| Services | `record_sale`, `record_sale_cleanup` |
| Dashboard | **POS** tab |
| Sensor | `sensor.communifarm_sales_status` |

## Flow

```text
prepacked sale_pack (open)  ─┐
                             ├→ record_sale(confirm=true) → sales + line + pack sold
weigh-at-sale (harvest+mass) ─┘
→ return home → record_sale_cleanup
```

## Identity

Sale lines denormalize `batch_id` and `harvest_id` from the pack’s harvest. Production `batches.stable_id` is the grow/substrate hub — not `media_batches`.

## Out of scope (this release)

Travel/mileage, asset purchase, depreciation, GAP compliance, CRM contacts.
