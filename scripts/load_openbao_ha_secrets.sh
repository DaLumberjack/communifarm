#!/usr/bin/env bash
# Load HA test credentials from OpenBao into the current shell environment.
# Usage: eval "$(./scripts/load_openbao_ha_secrets.sh)"
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_NAMESPACE="${VAULT_NAMESPACE:-homelab}"
TOKEN="${VAULT_TOKEN:-${BAO_TOKEN:-}}"
MOUNT="${OPENBAO_KV_MOUNT:-kv}"
PATH_NAME="${OPENBAO_HA_PATH:-local-services/ha-test}"

if [[ -z "$TOKEN" ]]; then
  echo "VAULT_TOKEN or BAO_TOKEN is required" >&2
  exit 1
fi

if command -v bao >/dev/null 2>&1; then
  CLI=(bao)
elif command -v vault >/dev/null 2>&1; then
  CLI=(vault)
else
  echo "Neither bao nor vault CLI found" >&2
  exit 1
fi

export VAULT_ADDR VAULT_NAMESPACE VAULT_TOKEN="$TOKEN"

# Prefer KV v2 read; fail closed on missing fields.
RAW="$("${CLI[@]}" kv get -format=json "${MOUNT}/${PATH_NAME}" 2>/dev/null || true)"
if [[ -z "$RAW" ]]; then
  echo "Failed to read ${MOUNT}/${PATH_NAME} from OpenBao" >&2
  exit 1
fi

py - <<'PY' "$RAW"
import json, sys
raw = json.loads(sys.argv[1])
data = raw.get("data", {})
# KV v2 nests under data.data
payload = data.get("data", data)
user = payload.get("username-1")
password = payload.get("password-1")
token = payload.get("long_lived_token") or payload.get("token") or payload.get("ha_token")
if not user or not password:
    raise SystemExit("OpenBao secret missing username-1 or password-1")
# Print shell exports only; never log values elsewhere.
print(f"export TEST_HA_USERNAME={json.dumps(user)}")
print(f"export TEST_HA_PASSWORD={json.dumps(password)}")
if token:
    print(f"export TEST_HA_TOKEN={json.dumps(token)}")
PY
