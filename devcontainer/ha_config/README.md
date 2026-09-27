# Local Home Assistant fixtures for Communifarm T1/T2

**Prerequisite:** Start the **Docker Desktop** application before `docker compose ... up`. The CLI alone is not enough; `docker version` must show a Server section. Details: [docs/user/local-development.md](../docs/user/local-development.md).

## What is committed vs ignored

| Commit (share with next developer) | Ignore (secrets / regenerable) |
|------------------------------------|--------------------------------|
| `configuration.yaml` (mock ESP entities) | `.storage/` (auth, tokens, registries) |
| `README.md` | `.cache/`, `.cloud/` |
| Default `blueprints/` shipped with HA | `home-assistant_v2.db*`, logs, `tts/` |
| `.devcontainer/*` compose + JSON | `backups/*.tar` (use workspace intake + OpenBao keys) |
| Repo-root `custom_components/communifarm/` | Nested `ha_config/custom_components/` (bind-mount overlay) |

Next developer: `docker compose -f .devcontainer/docker-compose.yml up -d homeassistant`, then either complete onboarding once, restore a backup from workspace `docs/intake/Dev Container Backups/` (keys via OpenBao / emergency kit intake — never git), or reuse a local `.storage` that is never pushed.

| Profile | Purpose |
|---------|---------|
| Empty / standalone | Communifarm mounted under `custom_components/communifarm`, no config entry yet |
| Mocked ESP set | `sensor.mock_temperature`, `sensor.mock_humidity`, `fan.mock_circulation_fan`, `switch.mock_exhaust` driven by `input_number` / `input_boolean` |
| Seeded state | Local-only `.storage` or restored backup — not committed |

## Injecting conditions

```bash
# Change mock temperature (via HA UI Developer Tools / services, or API token)
# input_number.set_value → entity_id input_number.mock_temperature
```

See workspace `.agents/skills/testing/SKILL.md` for stage definitions.
