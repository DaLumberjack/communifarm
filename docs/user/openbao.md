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
| Optional API token | `long_lived_token` / `token` / `ha_token` → `TEST_HA_TOKEN` |

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

## Load into Communifarm shell

From `repos/communifarm` after login + `BAO_NAMESPACE=homelab`:

```bash
export BAO_ADDR=http://127.0.0.1:8200
export BAO_NAMESPACE=homelab
# BAO_TOKEN is set by `bao login` into the CLI token helper; if needed:
# export BAO_TOKEN=...

# REQUIRED: eval — running the script alone only *prints* exports; it does not set them.
eval "$(./scripts/load_openbao_ha_secrets.sh)"

# Verify Playwright will see them (should print two lines, not empty):
echo "user=${TEST_HA_USERNAME:+set} pass=${TEST_HA_PASSWORD:+set}"

yarn playwright test e2e/flows/dashboard-targets.spec.ts
```

Never commit tokens, unseal keys, or exported password values.

## Failure checklist

| Symptom | Likely cause |
| --- | --- |
| connection refused on `:8200` | Server not started (terminal 1) |
| sealed / permission denied | Missing unseal ×3 or expired/missing login |
| empty / missing secret | `BAO_NAMESPACE` not `homelab`, or wrong path |
| Playwright: `TEST_HA_USERNAME/TEST_HA_PASSWORD required` | Ran the loader **without** `eval "$(...)"` — exports printed but not applied |
| Playwright login fails | Credentials wrong for this HA instance, or not eval'd in **this** shell |
