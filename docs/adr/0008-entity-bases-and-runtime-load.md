# ADR 0008: Entity bases, runtime load, and maintainability

## Status

Accepted (spike branch `spike/ha-integration-architecture-eval`)

## Context

Operators and maintainers asked whether Communifarm’s HA custom-component class/inheritance model is recommended or an anti-pattern, whether it is too heavy for a typical HA host, and whether dangerous patterns need an alternate approach. Skills used: architecture (HA custom-component), reviewing-ha-esphome-code, debugging-home-assistant-esphome, review-security.

| SHA | Role |
| --- | --- |
| `24c0d42` | Spike branch base = updated `main` |
| `cc9cb44` | Eval tip `feature/ops-scheduling-alerts` (ops queue + ADR 0007; not merged into this spike) |

Prior design: PR #8 / [mvp.md](../architecture/mvp.md) already locked **two inheritance levels** and Spec dataclasses for draft controls.

## Findings

### Inheritance (KEEP)

| Check | Evidence |
| --- | --- |
| Depth | `CommunifarmEntity` → platform base (`CommunifarmButton`, …) → leaf. No third base layer. |
| HA fit | Platform mixins (`ButtonEntity`, `SensorEntity`, …) are standard HA. |
| Domain purity | `domain/` has **zero** `homeassistant` / `HomeAssistant` imports. |
| Spec usage | `_ButtonSpec`, `_SelectSpec`, `_NumberSpec`, `_TextSpec` + bucket helpers already compose repetitive drafts. |
| Leaf sprawl | On spike base: ~29 button classes, ~19 sensor classes — many one-off `async_press` wrappers. Maintainability cost, not an inheritance anti-pattern. |

**Verdict:** Shallow inheritance is recommended. Deep ABC/mixin trees would be the anti-pattern.

### Runtime load (acceptable for home scale)

| Check | Evidence |
| --- | --- |
| Climate/ops tick | `CLIMATE_TICK_SECONDS = 60`; tick schedules async task (does not block the loop). |
| SQLite | Repositories use `async_add_executor_job` + process-wide `DB_LOCK` (avoids event-loop I/O and close races). |
| Dashboard | `dashboard/builder.py` ~1.5k LOC runs at provision / unit-change, not every tick. |
| Entity fan-out | Fixed set at setup (identity frozen in `tests/test_entity_bases.py`); no unbounded dynamic entity create. |
| Updates | Dispatcher signals, not a mandatory `DataUpdateCoordinator` for every sensor. |

**Verdict:** Not a heavy toll on a typical HA machine at current farm scale. Watch ops notification churn and large sensor attribute payloads as queues grow.

### Security / dangerous patterns

| Item | Severity | Notes |
| --- | --- | --- |
| Parameterized SQL in repos | OK | Executor-backed; PRAGMA/`ALTER` f-strings in migrations use fixed table/column identifiers only. |
| NFC / services | OK (HA auth) | Trust boundary = authenticated HA user; no new anonymous RPC. Ops-scheduling security review: no medium+ issues. |
| Config entry `async_reload` on `transition_batch` | Should fix (follow-up) | Full unload/reload is expensive and race-prone vs dispatcher refresh. |
| Dual Store + SQLite truth | Should fix (hygiene) | Setup state in Store/entry data; process history in SQLite — document which write wins. |
| Mega `hass.data[DOMAIN][entry_id]` draft bucket | Should fix (maintainability) | Dozens of draft keys; works, hard for a standard developer without a typed map. |
| No diagnostics redaction module | Nit | No secrets in component today; add redacted diagnostics before shipping cloud-adjacent dumps. |
| `__init__.py` ~1.6k LOC | Should fix (maintainability) | Setup + many service handlers in one file; logic already partially in `*_actions.py`. |

None of the above require replacing the entity inheritance model.

## Decision

1. **Keep** the two-level entity bases and Spec dataclasses.
2. **Prefer Spec + shared leaf** (`CommunifarmMilestoneButton`, `CommunifarmAdvanceStageButton`, new `CommunifarmEntryActionButton`) over new one-off subclasses when behavior is `action(hass, entry_id)`.
3. **Do not** introduce deep inheritance, Entity ABC hierarchies, or a full Coordinator rewrite.
4. Record follow-ups below; they are independent of this KEEP decision.

### Spike on this branch

Collapsed eight inventory NFC / mix helper buttons into `CommunifarmEntryActionButton` + `_ButtonSpec` in `button.py`. Entity ids / unique ids unchanged (`tests/test_entity_bases.py` still the freeze oracle).

## Rejected alternatives

| Alternative | Why rejected now |
| --- | --- |
| Deep inheritance / EntityABC tree | Anti-pattern for HA integrations; contradicts mvp.md; harder for standard developers. |
| Replace entity classes with free functions only | Fights HA platform entity model. |
| Mandatory `DataUpdateCoordinator` for all sensors | High churn; dispatchers + 60s tick already fit home scale. |
| Drop SQLite / Store-only | Process history needs SQLite (ADR 0003). |

## Related: alert priority policy (ops)

Does **not** change entity inheritance. It does constrain how `AlarmEvent` priorities should be assigned when ops scheduling grows (ADR 0007 tip / skill `ops-scheduling`):

| class | priority | rule |
| --- | --- | --- |
| Out-of-tolerance **sensors** / env readings | **P0** or **notifying P1** | Primary path for highest urgency |
| Time / dwell / “left open” alone | ≤ **P3** (or no alarm) | e.g. window open for X hours while temp/RH still in band → **do not** P0 |
| Business / security time rule | may be **P0** | Explicit policy (example: front door shut after 21:00), not comfort timing |

Seeded codes today remain P2 (`move_incubating_to_fruiting`) and P3 (`light_on_exceeds_hours`). First P0 implementation must extend `PRIORITIES` in `domain/ops_schedule.py` and add T0 cases. Digest: workspace `docs/intermediate/ops-scheduling.md`; intake `docs/intake/2026-11-02-alert-priority-sensor-vs-time.md`.

## Consequences / follow-ups (non-blocking)

1. Extend Spec / `EntryActionButton` pattern to remaining thin buttons when touching those areas.
2. Avoid full `config_entries.async_reload` where a dispatcher + state write suffices.
3. Split remaining service registration out of `__init__.py` into focused modules.
4. Optional typed entry-bucket helper (TypedDict / dataclass) documenting draft keys.
5. Ops tip: notify only on alarm-set change; cap ops/sensor attribute size (see ADR 0007 on ops branch when merged).
6. When adding P0: sensors-first; time-based P0 only for business/security rules (table above).

## Sources

- PR #8 `feature/entity-inheritance-bases` (`28cbd44` / merge `d6c23e7`)
- [mvp.md](../architecture/mvp.md) Entity bases section
- `.agents/skills/architecture/SKILL.md`, `architecture/ha/SKILL.md`
- `.agents/skills/reviewing-ha-esphome-code/SKILL.md`
- `.agents/skills/debugging-home-assistant-esphome/SKILL.md`
- Security review of ops-scheduling diff (no medium+ findings)
- Workspace digest: `docs/intermediate/ha-integration-architecture-eval.md`
