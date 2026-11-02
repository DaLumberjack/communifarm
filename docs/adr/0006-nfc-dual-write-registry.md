# ADR 0006: NFC dual-write registry (not central-only UID table)

## Status

Accepted

## Context

NFC UIDs lived on many domain tables (`inventory_lots`, `employees`, containers, …) plus a shipment `nfc_tag_pool`. Options:

| Option | Fit |
| --- | --- |
| **A. Central-only registry** | Strip per-entity `nfc_uid`; resolve only via pool. Cleaner relationally; large migration + rewrite of every lookup. |
| **B. Dual-write** | Keep entity `nfc_uid` for typed resolve; treat `nfc_tag_pool` as physical-tag registry; sync on bind. Smaller blast radius. |

Scan side effects debated: auto-mutate qty/location vs audit + session context only.

## Decision

1. **Dual-write (B)** for this milestone.
2. Resolve remains the entity `nfc_uid` walk; pool is not the walk source.
3. Bind/confirm/register **must** update pool + entity together.
4. Every resolve appends `nfc_scan_events` and refreshes `nfc_session` from SQLite.
5. **No** automatic inventory debit or relocate on bare scan (explicit services only).
6. Document schema + UML in [nfc-schema.md](../architecture/nfc-schema.md); agents follow `.agents/skills/nfc-database/SKILL.md`.

## Consequences

- Schema v19 adds `nfc_scan_events` and `nfc_tag_pool.bound_object_type`.
- Tests must assert pool + entity after bind, and scan audit without qty change.
- A future central-only migration remains possible; this ADR records why it was deferred.
