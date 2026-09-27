# ADR 0003: Communifarm SQLite for process / analysis events

## Status

Accepted

## Context

Recording scale weights (NFC-selected ingredient + mass) is the first Communifarm-owned dataset for long-term grow analysis. Options considered:

| Option | Fit |
| --- | --- |
| HA Recorder / `home-assistant_v2.db` | Wrong owner — HA schema, entity-centric, weak stable Communifarm IDs, painful cloud export |
| HA `Store` JSON | Fine for config/profile; poor for append-only events and queries |
| **Communifarm SQLite file** | Matches storage skill; local, open source; same relational shape can later sync/migrate to cloud Postgres |
| Cloud DB first | Speculative infrastructure; blocked by project rules |

## Decision

1. Keep **HA Store** for mutable setup state (Site/Environment/profile/batch) — ADR 0001.
2. Add a **Communifarm-owned SQLite** database under the HA config dir (`communifarm/communifarm.db`) for process events and future aggregates.
3. First table: `weight_events` (stable event id, site/environment/batch ids, ingredient key + label, mass_g, optional NFC uid, source entity snapshot, timestamps).
4. Do **not** create custom tables inside Recorder’s database.
5. Cloud later: replicate/migrate the same relational model to an open-source server DB (e.g. PostgreSQL); keep domain repositories abstract so backends can swap.

## Consequences

- Weigh “Record” persists via Communifarm (service + scale button hook), not only ESPHome `last_recorded` text.
- SQLite I/O runs off the event loop (`async_add_executor_job`).
- Schema versioned with tested migrations.
- Env metric rollups remain a later table family; raw high-frequency sensor history stays Recorder’s job.
