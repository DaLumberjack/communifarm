# Local development

## Prerequisite: use `py` for Python

On this Windows host the executable is **`py`**, not `python`. Local scripts and docs should call `py` / `py -m ...`. (Remote HAOS deploy checks may still use `python3` on the Linux VM.)

## Prerequisite: Docker Desktop must be running

On Windows, the Docker CLI (`docker version` Client) can be installed while the **engine is off**. Local Home Assistant compose needs the Docker Desktop application running.

1. Start **Docker Desktop** from the Start menu.
2. Wait until status is **Running** (whale icon steady).
3. Confirm the engine is up:

```bash
docker version
```

You must see a **Server:** section. If you only see Client and an error about `dockerDesktopLinuxEngine`, Docker Desktop is not running — compose will fail the same way.

Optional service check (PowerShell):

```powershell
Get-Service com.docker.service
# if Stopped: Start-Service com.docker.service  (or launch Docker Desktop)
```

## Dev container / compose

Use [`.devcontainer/docker-compose.yml`](../../.devcontainer/docker-compose.yml) to run Home Assistant with Communifarm bind-mounted and mock ESP entities from [`devcontainer/ha_config/configuration.yaml`](../../devcontainer/ha_config/configuration.yaml).

### First boot vs preferred reuse

A new Docker HA config starts at **`http://127.0.0.1:8123/onboarding.html`**. You must finish **Create my smart home** (owner user + basics) until the normal home page appears before installing Communifarm.

HAR-backed first test: `yarn test:e2e:t1:scratch` (`e2e/flows/00-ha-scratch-to-communifarm.spec.ts`).  
Intake backups: `docs/intake/Dev Container Backups/`. Details: workspace `docs/intermediate/har-init-to-communifarm.md`.

| Preference | Path |
|------------|------|
| Preferred | Keep `devcontainer/ha_config` already onboarded and Communifarm-ready so compose starts past onboarding |
| Acceptable | Restore a backup from `docs/intake/Dev Container Backups/` into the new instance |
| Required regression | `00-ha-scratch-to-communifarm` from empty config, then optionally create/update a backup |

### Steps

1. Ensure Docker Desktop is running (see above).
2. `docker compose -f .devcontainer/docker-compose.yml up -d homeassistant`
3. If onboarding appears: complete **Create my smart home** (or restore a backup) until the HA home page loads.
4. Add the Communifarm integration (standalone config flow).
5. Bind mock temperature/humidity/exhaust entities.
6. Confirm the Communifarm dashboard path `/communifarm/overview`.
7. After a good setup, create an HA backup so future empty compose runs can use preference path 2.

## Testing stages

See the workspace testing skill for T0–T3. Local UI work is always T1/T2 first.

## Playwright session contract

Configured-instance UI tests (`dashboard-targets`, `onboarding`, `mock-conditions`, `upgrade`):

1. Open homepage `/`
2. Log in if the auth form appears (usual)
3. Navigate to the flow endpoint (e.g. `/communifarm/overview`, integrations)
4. Execute assertions

Implemented by `e2e/fixtures/ha-test.ts` (auto) + `startHaSession` in `e2e/fixtures/ha-session.ts`.

Scratch bootstrap (`00-ha-scratch-to-communifarm`) starts at onboarding instead; backup catalog (`01-…`) has no UI session.

## OpenBao (dev-container HA login)

T1 Playwright needs HA credentials from OpenBao (`kv/ha-test` → `username_dev_container` / `password_dev_container`).

**OpenBao must be running, unsealed, and you must have run `bao login` once.** Playwright auto-loads secrets — no manual export. Details: [openbao.md](openbao.md).

```bash
yarn test:e2e:dashboard
```

Scale mock + NFC stub: [mock-scale.md](mock-scale.md) (`yarn test:e2e:scale` when `TEST_HA_TOKEN` is present).

