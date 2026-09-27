# ADR 0001: Store-backed persistence for MVP

## Status

Accepted

## Context

Communifarm needs durable Site/Environment/profile/batch state. Full SQLite aggregation is a later milestone.

## Decision

Use Home Assistant `Store` (`communifarm.state`) for mutable domain state in MVP, mirrored into config entry `data.state` for setup/reopen. SQLite remains the planned long-term store for aggregates and production events.

## Consequences

- Fast to ship; upgrade tests must round-trip Store JSON.
- A later migration ADR will move Store payloads into SQLite without changing domain models.
