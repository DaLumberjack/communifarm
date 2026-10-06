# ADR 0004: Climate tree and control ownership

## Status

Accepted

## Context

Communifarm had one onboarding Environment and placement shelves for bags. Grow sites need many climate volumes: outdoors, a general room, tents, and storage. Some are monitored, some borrow a nearby sensor, and some only store goods. Machines (fans, AC, heater, humidifier, dehumidifier, lights, condensate pump) must be commanded from readings without inventing GPIO or a second transport.

Estimated power and cost of goods are a later branch.

## Decision

1. Keep placement areas as shelves. Add a separate climate tree in SQLite schema **v12** (`climate_nodes`, `climate_bindings`, `climate_intents`) plus optional `placement_areas.climate_id`.
2. The onboarding Environment stays in HA Store. Setup calls `ensure_climate_layout`, which copies it into the general-room node (same stable id) under an outdoor parent and binds the sensors and machines labeled on the preset schematic. The call is idempotent.
3. Indoor nodes with no local sample inherit the parent’s effective reading (median of non-stale sensors). Outdoor nodes do not inherit. No reading means do not turn heater, AC, humidifier, dehumidifier, or the condensate pump on.
4. Control decisions are pure domain code. The adapter reads Home Assistant states (the same states ESPHome publishes) and calls `turn_on` / `turn_off` on bound entities only.
5. Nodes with `control_enabled` false (harvest, ready to sell, storage) never produce intents.
6. Fail-safe for this slice is “do not actuate blind.” ESP32 last-state fallback stays a later milestone. No pin maps.

## Consequences

- Schema v12 is additive. Batches, placement rows, and the Store environment survive the migration.
- A 60-second tick plus `tick_climate` run the same decision function.
- Dashboard overview shows `sensor.communifarm_climate_status`.
- Energy dashboard integration is intentionally not in this slice.
