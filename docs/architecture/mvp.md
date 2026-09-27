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
