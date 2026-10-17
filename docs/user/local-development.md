# Local development

## Prerequisite: use `py` for Python

On this Windows host the executable is **`py`**, not `python`. Local scripts and docs should call `py` / `py -m ...`. (Remote HAOS deploy checks may still use `python3` on the Linux VM.)

## After a Windows reboot

Nothing in this stack starts itself. A reboot stops Docker’s Linux engine, the Home Assistant container, and OpenBao (which also seals). Do the rows in order. Commands that do not exist: `docker:run`, `npm docker:run`, `yarn docker:run`.

Work from `repos/communifarm`. Leave two things running for the rest of the session: the Docker Desktop app, and the terminal that is running `bao server`.

| Step | Turn on | Manual action | Done when |
| --- | --- | --- | --- |
| 1 | Docker Desktop | Start menu → **Docker Desktop**. Wait past the UI saying Running. | `docker version` prints a **Server:** block that includes an engine **Version:** |
| 2 | Home Assistant | `docker compose -f .devcontainer/docker-compose.yml up -d homeassistant` | [http://127.0.0.1:8123](http://127.0.0.1:8123) loads a login page |
| 3 | OpenBao server | New terminal. Leave it open. Commands in [openbao.md](openbao.md#start-openbao-terminal-1). | Log line `OpenBao server started!` |
| 4 | Unseal | Second terminal. `bao operator unseal` **three** times (three key shares). | Server log: `vault is unsealed` |
| 5 | Login | Same second terminal. `bao login`, then `export BAO_NAMESPACE=homelab`. | `bao kv get kv/ha-test` lists field names (do not paste values) |

Then, only if you want the UI: open [http://127.0.0.1:8123](http://127.0.0.1:8123) and log in. Playwright does that itself once steps 1–5 are done. It reads `kv/ha-test` (`username_dev_container` / `password_dev_container`). No extra export.

`devcontainer/ha_config` is a folder on disk, so a reboot does **not** wipe Home Assistant. You should land on the login page. Onboarding (`/onboarding.html`) means that folder was empty or replaced — finish **Create my smart home** or restore a backup. See [local HA bootstrap](../../../../docs/intermediate/local-ha-bootstrap.md) in the workspace.

### Engine 500 (`dockerDesktopLinuxEngine`)

Docker Desktop can say **Running** while the engine is dead. Both of these mean step 1 is not done:

- `docker version` shows **Client:** only, then `500 Internal Server Error` for `dockerDesktopLinuxEngine`
- `docker compose ... up` fails with `unable to get image 'ghcr.io/home-assistant/home-assistant:stable'` and the same 500

`docker desktop status` can still print `running`. The named pipe is up; the Linux VM behind it is not answering.

1. Whale menu → **Quit Docker Desktop** (closing the window leaves the backend running).
2. `wsl -t docker-desktop`
3. If that hangs or compose still 500s: `wsl --shutdown`, then start Docker Desktop again.
4. Wait until `docker version` shows **Server:** with an engine version. The UI often flips to Running before the engine does.
5. Retry step 2.

### Leave off unless you need it

| Thing | Start it when |
| --- | --- |
| Compose service `dev` (`sleep infinity`) | You use **Reopen in Container**. Day-to-day host tests only need `homeassistant`. `up` with no service name also starts `dev`. |
| Test VM `192.168.102.20` | T3 only. See [test-vm-deploy.md](test-vm-deploy.md). It is a different machine and does not come back with this PC. |
| Physical ESPHome devices | You are on live hardware. Local T1 uses mocks already in the HA config. |
| `yarn provision:ha-token` | First machine setup, or the long-lived token was rotated. Not every boot. |

## Prerequisite: Docker Desktop must be running

On Windows, the Docker CLI (`docker version` Client) can be installed while the **engine is off**. Local Home Assistant compose needs the Docker Desktop application running.

1. Start **Docker Desktop** from the Start menu.
2. Wait until status is **Running** (whale icon steady).
3. Confirm the engine is up:

```bash
docker version
```

You must see a **Server:** section **with an engine version**. Client-only output, or `500` on `dockerDesktopLinuxEngine`, means the UI is up and the engine is not. Recovery is in [After a Windows reboot](#after-a-windows-reboot).

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

## Playwright suites (scratch vs setup vs seeded)

Do **not** mix these against the wrong HA state. Default `yarn test:e2e` is **seeded** only — post-init operator functionality (target 100% pass on a configured instance).

| Script | What it covers | HA precondition |
| --- | --- | --- |
| `yarn test:e2e` / `yarn test:e2e:t1:seeded` | Dashboard targets, weigh/variance, mock sensors/scale, backup-artifact catalog | Past onboarding; **Communifarm already configured** |
| `yarn test:e2e:t1:pos` | Inoculate / harvest / POS (merge-blocking with seeded) | Seeded + Communifarm configured |
| `yarn test:e2e:t1:setup` | Standalone Communifarm config flow → dashboard path | HA logged in; Communifarm may be missing |
| `yarn test:e2e:t1:scratch` | Empty HA `Welcome!` → Create my smart home → Communifarm | **Empty** config (`/onboarding.html`) |
| `yarn test:e2e:t2` | Upgrade / no-data-loss | Seeded, after version bump |
| `yarn test:e2e:t3` | Live test VM setup/onboarding probe | `192.168.102.20` only |
| `yarn test:e2e:report` | Seeded + POS → committed MR evidence | Same as seeded/POS |
| `yarn test:e2e:validate` | Check `summary.json` vs `HEAD` (same gate as CI) | Summary already written |

### Merge-request E2E evidence (no HA in GitHub Actions)

Hosted CI does **not** run Playwright or the HA container. Before you open or update an MR:

```bash
yarn test:e2e:report
git add test-results/e2e/summary.json test-results/e2e/summary.md
git commit -m "test: refresh local E2E summary for MR gate"
```

| Artifact | Role |
| --- | --- |
| `test-results/e2e/summary.json` | Machine gate: suites, counts, `git_sha` (committed) |
| `test-results/e2e/summary.md` | Human-readable rollup (committed) |
| `e2e/.generated/reports/raw-*.json` | Per-suite Playwright JSON (gitignored; not under `test-results/` because Playwright wipes that folder each run) |

CI job `e2e-local-report` fails unless the summary’s `git_sha` matches the PR head, required suites `t1_seeded` + `t1_pos` are present, and `failed` / `errored` are 0. Test order does not matter. See [ADR 0005](../adr/0005-local-e2e-ci-evidence.md).

Seeded flows assume Site/Environment/bindings/profile already exist. Future ESPHome-driven tests (e.g. tent temp/humidity excursion → exhaust/intake duty) belong in **seeded**, not setup/scratch.

| Wait budget | Value | Use |
| --- | --- | --- |
| `INITIAL_LOAD_MS` | 15s | First navigation / login / shell |
| `STEP_MS` | 5s | Per-step visibility and `expect.poll` after ready |

Scratch against a seeded instance **skips** (no `Welcome!`). Seeded weigh flows call `complete_and_new_batch` first so prior variance mixes cannot leave stale gram amounts on the session sensor.

## Playwright session contract

Seeded / configured-instance UI tests (`dashboard-targets`, `mock-conditions`, `weigh-*`, `upgrade`):

1. Open homepage `/`
2. Log in if the auth form appears (usual)
3. Navigate to the flow endpoint (e.g. `/communifarm/overview`)
4. Execute assertions

Implemented by `e2e/fixtures/ha-test.ts` (auto) + `startHaSession` in `e2e/fixtures/ha-session.ts`.

Scratch bootstrap (`00-ha-scratch-to-communifarm`) starts at onboarding. Setup (`onboarding.spec.ts`) is config-flow only via `yarn test:e2e:t1:setup`. Backup catalog (`01-…`) has no UI session.

## OpenBao (dev-container HA login)

T1 Playwright needs HA credentials from OpenBao (`kv/ha-test` → `username_dev_container` / `password_dev_container`).

**OpenBao must be running, unsealed, and you must have run `bao login` once.** Playwright auto-loads secrets — no manual export. Details: [openbao.md](openbao.md).

```bash
yarn test:e2e:dashboard
```

First-time (or rotate) long-lived API token for mock-scale / REST helpers:

```bash
yarn provision:ha-token
```

Scale mock + NFC stub: [mock-scale.md](mock-scale.md) (`yarn test:e2e:scale` when `TEST_HA_TOKEN` is present).

Production → harvest → POS (no physical scanner):

```bash
yarn test:e2e:t1:pos
```

| Spec | Path |
| --- | --- |
| `production-to-pos` | UI inoculate→incubating→fruiting→harvesting→batch harvest→POS sale |
| `mock-nfc-harvest-pos` | Sets `input_text.esp32dev_last_nfc_uid` to container UID → Harvest confirm → POS |
| `inoculate-from-nfc` | Culture tag on `esp32dev_last_nfc_uid` → **Select inoculum from NFC** → inoculate |

Mix is not required before inoculate (`planned` is enough). Harvest NFC uses Communifarm `check_in`, not `esp32dev_simulate_nfc_scan`.

