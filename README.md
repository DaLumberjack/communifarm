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

HA UI credentials for shared test identities come from OpenBao:

```bash
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_NAMESPACE=homelab
export VAULT_TOKEN=...   # short-lived session token
eval "$(./scripts/load_openbao_ha_secrets.sh)"
```

Never commit tokens, passwords, or `known_hosts.test` private material.

## Versioning

Feature branch → merge to `main` → bump `manifest.json` version → local T2 upgrade check → optional T3 on the test VM.

## MVP slice

- Site + Environment config flow
- Bind temperature / humidity / fan / switch
- Profile targets (`number` entities)
- Starter batch lifecycle (`planned → active → complete`)
- One generated dashboard model
- Allowlisted switch proxy
