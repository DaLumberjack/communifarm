# OpenBao (HA test secrets)

Playwright T1/T2/T3 and shared HA logins read credentials from OpenBao. **OpenBao must be running and unsealed** or `load_openbao_ha_secrets.sh` / the UI will fail.

## Secret location

| Item | Value |
| --- | --- |
| UI | http://127.0.0.1:8200/ui/vault/secrets/kv/show/ha-test?namespace=homelab |
| Mount / path | `kv/ha-test` |
| Namespace | `homelab` |
| Dev-container user | `username_dev_container` |
| Dev-container password | `password_dev_container` |
| Dev-container Playwright token | `dev_container_playwright_long_lived_access_token` → `TEST_HA_TOKEN` |
| Legacy API token aliases | `long_lived_token` / `token` / `ha_token` → `TEST_HA_TOKEN` |

### Provision the Playwright token (first-time / rotate)

HA long-lived tokens are created once and stored in OpenBao. Automate with:

```bash
# 1) Login to HA via OpenBao username/password, mint token, write e2e/.generated/
yarn test:e2e:t1:provision-token

# 2) Patch kv/ha-test (requires bao login)
yarn openbao:set-playwright-token

# Or both:
yarn provision:ha-token
```

| Detail | Value |
| --- | --- |
| HA client_name | `communifarm-playwright-dev` |
| Lifespan | 3650 days |
| Artifacts | `e2e/.generated/ha-token.env` + `ha-token.json` (gitignored) |
| OpenBao field | `dev_container_playwright_long_lived_access_token` |
| Script | [`scripts/openbao_set_playwright_token.sh`](../../scripts/openbao_set_playwright_token.sh) |

Re-running provision **deletes** any existing refresh token with that client_name and creates a fresh access token (HA never re-shows the old string).

Loader: [`scripts/load_openbao_ha_secrets.sh`](../../scripts/load_openbao_ha_secrets.sh) exports `TEST_HA_USERNAME` / `TEST_HA_PASSWORD` (and token when present). Override path with `OPENBAO_HA_PATH` if needed.

## Start OpenBao (terminal 1)

Clear stale token/namespace env, then start the server. Config path is machine-local — adjust `OPENBAO_CONFIG` if yours differs.

### Bash (Git Bash / MSYS)

```bash
unset BAO_TOKEN BAO_NAMESPACE VAULT_TOKEN VAULT_NAMESPACE
export BAO_ADDR=http://127.0.0.1:8200
export OPENBAO_CONFIG="${OPENBAO_CONFIG:-/c/Users/andre/Documents/selfhosted/iac/openbao/config.hcl}"
bao server -config="$OPENBAO_CONFIG"
```

Leave this terminal running.

### PowerShell (reference)

```powershell
Remove-Item Env:\BAO_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:\BAO_NAMESPACE -ErrorAction SilentlyContinue
$env:BAO_ADDR = "http://127.0.0.1:8200"
bao server -config="C:/Users/andre/Documents/selfhosted/iac/openbao/config.hcl"
```

## Unseal + login (terminal 2)

Unseal requires **three** unseal key entries, then a login token. Keep namespace unset until after login.

### Bash

```bash
unset BAO_NAMESPACE VAULT_NAMESPACE
export BAO_ADDR=http://127.0.0.1:8200

bao operator unseal   # key 1
bao operator unseal   # key 2
bao operator unseal   # key 3
bao login             # paste root/user token when prompted

# KV under the homelab namespace (required to see ha-test)
export BAO_NAMESPACE=homelab
export VAULT_NAMESPACE=homelab

# Confirm (should list username_dev_container / password_dev_container — do not paste values into chat/logs)
bao kv get kv/ha-test
```

### PowerShell (reference)

```powershell
Remove-Item Env:\BAO_NAMESPACE -ErrorAction SilentlyContinue
$env:BAO_ADDR = "http://127.0.0.1:8200"
bao operator unseal
bao operator unseal
bao operator unseal
bao login
$env:BAO_NAMESPACE = "homelab"
```

## Load into Communifarm / Playwright

**Playwright auto-loads** `TEST_HA_USERNAME` / `TEST_HA_PASSWORD` from OpenBao when you run `yarn playwright …` (`e2e/load-openbao-secrets.ts` via `playwright.config.ts`). No manual `eval` for tests.

Still required once per machine boot:

1. OpenBao server running
2. Unsealed (×3)
3. `bao login` (token helper `~/.bao-token` or `~/.vault-token`)

Then:

```bash
yarn playwright test e2e/flows/dashboard-targets.spec.ts
```

| Override | Purpose |
| --- | --- |
| `BAO_ADDR` | default `http://127.0.0.1:8200` |
| `BAO_NAMESPACE` | default `homelab` |
| `OPENBAO_HA_PATH` | default `ha-test` |
| `SKIP_OPENBAO_SECRETS=1` | skip auto-load |
| `TEST_HA_USERNAME` / `TEST_HA_PASSWORD` | use pre-set values (skip OpenBao) |

### Manual shell export (optional)

Only for interactive shells (not needed for Playwright):

```bash
export BAO_ADDR=http://127.0.0.1:8200
export BAO_NAMESPACE=homelab
eval "$(./scripts/load_openbao_ha_secrets.sh)"
```

Never commit tokens, unseal keys, or exported password values.

## Failure checklist

| Symptom | Likely cause |
| --- | --- |
| connection refused on `:8200` | Server not started (terminal 1) |
| sealed / permission denied | Missing unseal ×3 or expired/missing login |
| empty / missing secret | Wrong namespace/path in OpenBao |
| Playwright: could not load HA secrets | Not logged in (`bao login`) or OpenBao sealed |
| Playwright login fails | Secret values do not match this HA owner user |
