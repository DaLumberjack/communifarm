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

## Persistence

| Store | Holds |
| --- | --- |
| HA `Store` (`communifarm.state`) | Site/Environment/profile/batch setup |
| Communifarm SQLite (`communifarm/communifarm.db`) | Process/analysis events (`weight_events`, later aggregates) |
| HA Recorder | Raw entity history only — not Communifarm process truth |

## Dashboard targets

`DashboardBuilder` emits overview + **Weigh** views. Profile updates go through the number platform → Store; weigh-ins go through `weight_events` when Record is pressed.
