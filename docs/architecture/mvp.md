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

## Dashboard targets

`DashboardBuilder` emits a **Current settings** markdown card (Jinja `states()` for live values) plus an interactive **Targets** entities card bound to Communifarm `number` entities. Profile updates go through the number platform → Store; users adjust day-to-day targets on the dashboard, not via the integration options UI.
