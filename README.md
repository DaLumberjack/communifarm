# Communifarm

Home Assistant custom integration for controlled-environment agriculture operations.

## Layout

```text
custom_components/communifarm/   # installable integration
tests/                           # T0 pytest
e2e/                             # T1–T3 Playwright
.devcontainer/                   # local HA + mock devices
scripts/                         # version bump, local upgrade, OpenBao secrets, test-VM deploy
docs/                            # published docs for this repo
```

## Quick start (local)

On this machine the Python launcher is `py` (not `python`). Prefer `py -m pip` / `py -m pytest`.

```bash
cd repos/communifarm
py -m pip install -r requirements_test.txt
py -m pytest --cov=custom_components/communifarm
```

Start the local HA stack (Docker):

**Prerequisite:** Docker Desktop must be running on Windows. `docker version` must show a **Server:** section before compose will work. See [docs/user/local-development.md](docs/user/local-development.md).

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

## Secrets

HA UI credentials come from OpenBao. **Start and unseal OpenBao, then `bao login` once** — see [docs/user/openbao.md](docs/user/openbao.md).

Playwright loads `username_dev_container` / `password_dev_container` from `kv/ha-test` (namespace `homelab`) automatically via `playwright.config.ts`. No manual `eval` for tests.

```bash
yarn playwright test e2e/flows/dashboard-targets.spec.ts
```

Never commit tokens, passwords, or `known_hosts.test` private material.

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

See [docs/user/dashboard.md](docs/user/dashboard.md).

