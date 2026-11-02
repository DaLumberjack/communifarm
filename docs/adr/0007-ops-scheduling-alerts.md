# ADR 0007: Ops scheduling and priority alerts

## Status

Accepted

## Context

Operators need time- and condition-driven prompts (move incubating blocks to fruiting; light/UV left on too long) without a second automation bus. Climate already ticks every 60s. Production already stores `expected_check_at` and stages. Architecture listed `AlarmEvent` as a core model but it was unimplemented.

## Decision

1. Pure domain module `domain/ops_schedule.py` evaluates facts into `AlarmEvent`, `ProjectedMove`, and `OpsQueue`. No `hass` / entity IDs in domain.
2. Sibling ops tick on the existing climate interval (`ops_actions.async_tick_ops`) — not a parallel scheduler or HA Automations YAML product path.
3. Dual alert surface: `sensor.communifarm_ops_queue` (count + attrs) and deduped `persistent_notification` per alarm id.
4. Schema **v20** adds `phase_changed_at` on `batches` and `production_containers` for dwell-based projections; fallback is `created_at`.
5. Seed rules: P2 `move_incubating_to_fruiting` (expected_check_at or provisional dwell); P3 `light_on_exceeds_hours` (ROLE_LIGHT continuous on-time; UV same overrun class until a distinct binding exists).
6. Alerts never auto-advance lifecycle stages.

## Consequences

- Provisional `DEFAULT_INCUBATION_DWELL_HOURS` must be locked via process-evidence before treating as operator truth.
- New schedule/alert intake routes through the `ops-scheduling` skill → extend `evaluate_ops` + T0.
- Dashboard Production tab shows the ops queue card.
