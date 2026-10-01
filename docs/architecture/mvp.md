# MVP architecture

```text
Config Flow / Options
        ↓
HA adapters (entities, services, lovelace provisioner)
        ↓
Domain models (Site, Environment, Profile, Batch, Bindings)
        ↓
CommunifarmRepository (HA Store)
```

Domain modules must not import `hass` or entity IDs as permanent keys. Bindings store entity registry entry ids when available and resolve live entity ids at runtime.

## Entity bases

Home Assistant platform modules stay at the component root (`button.py`, `sensor.py`, and the rest). Shared plumbing is two levels:

| Level | Class | Owns |
| --- | --- | --- |
| 1 | `CommunifarmEntity` | config-entry bucket, `unique_id`, explicit `entity_id` |
| 2 | `CommunifarmButton`, `CommunifarmSelect`, `CommunifarmNumber`, `CommunifarmSensor`, `CommunifarmText`, `CommunifarmSwitch` | platform behavior |

Subclasses override the method that differs (`async_press`, `native_value`, and so on). Data-only buttons, selects, and draft numbers are descriptions, not extra classes. Do not add a third inheritance level.

SQLite table SQL stays in `storage/sqlite_db.py` `MIGRATIONS`. Repositories inherit `SqliteRepository` for the connection and lock, and keep their own queries. There is no schema class hierarchy.

## Persistence

| Store | Holds |
| --- | --- |
| HA `Store` (`communifarm.state`) | Site/Environment/profile/batch setup |
| Communifarm SQLite (`communifarm/communifarm.db`) | Process/analysis events (`weight_events`, later aggregates) |
| HA Recorder | Raw entity history only — not Communifarm process truth |

## Dashboard targets

`DashboardBuilder` emits overview + **Weigh** views. Profile updates go through the number platform → Store; weigh-ins go through `weight_events` when Record is pressed.
