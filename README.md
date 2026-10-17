# Communifarm

Home Assistant custom integration for controlled-environment agriculture operations.

## Layout

```text
custom_components/communifarm/   # installable integration
esphome/                         # reusable packages, devices, CI compile examples
tests/                           # T0 pytest
e2e/                             # T1–T3 Playwright
.devcontainer/                   # local HA + mock devices
scripts/                         # version bump, local upgrade, OpenBao, E2E report, test-VM deploy
docs/                            # published docs for this repo
test-results/e2e/                # committed local E2E summary (MR gate)
```

## Quick start (local)

On this machine the Python launcher is `py` (not `python`). Prefer `py -m pip` / `py -m pytest`.

```bash
cd repos/communifarm
py -m pip install -r requirements_test.txt
# Same gate as GitHub Actions "Ruff" step (auto-fix then verify):
./scripts/lint.sh
# or: py -m ruff check --fix custom_components tests && py -m ruff check custom_components tests
py -m pytest --cov=custom_components/communifarm
```

Optional every-commit automation:

```bash
py -m pip install pre-commit
pre-commit install          # once per clone
pre-commit run --all-files  # manual full run
```

Start the local HA stack (Docker):

**Prerequisite:** after a reboot, follow [After a Windows reboot](docs/user/local-development.md#after-a-windows-reboot). Docker Desktop’s window is not enough — `docker version` must show a **Server:** engine version before compose will work.

```bash
# 1) Start Docker Desktop app, wait until Running
# 2) Then:
docker compose -f .devcontainer/docker-compose.yml up -d homeassistant
# HA: http://127.0.0.1:8123
# Component is bind-mounted into /config/custom_components/communifarm
```

Testing stages (authoritative): workspace `.agents/skills/testing/SKILL.md`.

| Stage | Command |
|-------|---------|
| T0 | `pytest` |
| T1 | Playwright against `http://127.0.0.1:8123` with mock devices |
| T2 | `./scripts/bump_version.sh` → `./scripts/local_upgrade_install.sh` → Playwright `TEST_HA_STAGE=T2` |
| T3 | `./scripts/deploy_test_vm.sh dry-run` then `deploy` to `192.168.102.20` only |

Before opening or updating an MR: `ruff check custom_components tests`, then `yarn test:e2e:report`, then commit `test-results/e2e/summary.json` (+ `.md`). Detail: [local-development.md](docs/user/local-development.md).

## Secrets

HA UI credentials come from OpenBao. **Start and unseal OpenBao, then `bao login` once** — see [docs/user/openbao.md](docs/user/openbao.md).

Playwright loads `username_dev_container` / `password_dev_container` from `kv/ha-test` (namespace `homelab`) automatically via `playwright.config.ts`. No manual `eval` for tests.

```bash
yarn playwright test e2e/flows/dashboard-targets.spec.ts
```

Never commit tokens, passwords, or `known_hosts.test` private material.

## ESPHome device packages

Reusable YAML under `esphome/packages/` (common / boards / roles), deployment devices under `esphome/devices/`, and CI compile targets under `esphome/examples/compile/`. Matching Home Assistant T1 mocks live in `devcontainer/ha_config/packages/`.

| Device | Board / role | HA T1 mock |
|--------|--------------|------------|
| `cf-tent1-sensor01` | ESP32-S3-WROOM-1 · BME688/SHT3x/OneWire + calibration | `mock_cf_tent_sensor` |
| `cf-mixroom-scale01` | D1 Mini32 / esp32dev · scale | `mock_esp32dev_scale` |
| `cf-mixroom-nfc-scan01` | D1 Mini32 · PN532 I2C scan | `mock_cf_nfc_reader` |
| `cf-lab-nfc-write01` | D1 Mini32 · PN532 SPI R/W | `mock_cf_nfc_reader` |
| `cf-lab-aio868` | KinCony KC868-AIO · machine templates | `mock_cf_aio868` |

KinCony actuators stay **template switches** until manufacturer pin maps are verified — no guessed GPIOs. Overview: [esphome/README.md](esphome/README.md), [docs/hardware/esphome-devices.md](docs/hardware/esphome-devices.md).

## Manual air-exchange tachometer

Schema **v13** stores labeled vents and timestamped RPM/CFM/FPM readings (`communifarm.upsert_air_vent`, `communifarm.record_tachometer`). Handheld first; GPIO pulse tach later.

| Doc | Purpose |
|-----|---------|
| [docs/hardware/air-exchange-tachometer.md](docs/hardware/air-exchange-tachometer.md) | Operator workflow, purchase checklist, upgrades |
| [docs/process/test-cases/air-exchange-tachometer.md](docs/process/test-cases/air-exchange-tachometer.md) | T0 acceptance cases |
| `tests/test_tachometer.py` | Pytest coverage |
| `mock_cf_tachometer` | Devcontainer helpers |

## Versioning

Feature branch → merge to `main` → bump `manifest.json` version → local T2 upgrade check → optional T3 on the test VM.

## MVP slice

- Site + Environment config flow
- Bind temperature / humidity / fan / switch
- Profile targets (`number` entities, adjustable on the dashboard)
- Starter batch lifecycle (`planned → active → complete`)
- One generated dashboard with Current settings + Targets controls
- Allowlisted switch proxy
- Local `esp32dev` scale mock + NFC ingredient select stub ([docs/user/mock-scale.md](docs/user/mock-scale.md))
- Communifarm SQLite for weigh events ([docs/user/storage.md](docs/user/storage.md), ADR 0003)
- ESPHome role packages + HA mocks ([docs/hardware/esphome-devices.md](docs/hardware/esphome-devices.md))
- Manual vent tachometer logging (schema v13)

See [docs/user/dashboard.md](docs/user/dashboard.md).

