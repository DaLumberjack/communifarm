#!/usr/bin/env bash
# Load HA test credentials from OpenBao into the current shell environment.
# Prerequisite: OpenBao must be running and unsealed (see docs/user/openbao.md).
# Usage: eval "$(./scripts/load_openbao_ha_secrets.sh)"
set -euo pipefail

# OpenBao CLI prefers BAO_*; Vault CLI prefers VAULT_*. Accept either.
ADDR="${BAO_ADDR:-${VAULT_ADDR:-http://127.0.0.1:8200}}"
NAMESPACE="${BAO_NAMESPACE:-${VAULT_NAMESPACE:-homelab}}"
TOKEN="${BAO_TOKEN:-${VAULT_TOKEN:-}}"
MOUNT="${OPENBAO_KV_MOUNT:-kv}"
# UI: http://127.0.0.1:8200/ui/vault/secrets/kv/show/ha-test?namespace=homelab
PATH_NAME="${OPENBAO_HA_PATH:-ha-test}"

if [[ -z "$TOKEN" ]]; then
  echo "BAO_TOKEN or VAULT_TOKEN is required (run: bao login)" >&2
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

export BAO_ADDR="$ADDR" VAULT_ADDR="$ADDR"
export BAO_NAMESPACE="$NAMESPACE" VAULT_NAMESPACE="$NAMESPACE"
export BAO_TOKEN="$TOKEN" VAULT_TOKEN="$TOKEN"

# Prefer KV v2 read; fail closed on missing fields.
RAW="$("${CLI[@]}" kv get -format=json "${MOUNT}/${PATH_NAME}" 2>/dev/null || true)"
if [[ -z "$RAW" ]]; then
  echo "Failed to read ${MOUNT}/${PATH_NAME} (namespace=${NAMESPACE}). Is OpenBao unsealed?" >&2
  exit 1
fi

py - <<'PY' "$RAW"
import json, sys
raw = json.loads(sys.argv[1])
data = raw.get("data", {})
# KV v2 nests under data.data
payload = data.get("data", data)

# Dev-container identity (preferred for local T1) then legacy VM fields.
user = (
    payload.get("username_dev_container")
    or payload.get("username-1")
    or payload.get("username")
)
password = (
    payload.get("password_dev_container")
    or payload.get("password-1")
    or payload.get("password")
)
token = (
    payload.get("long_lived_token")
    or payload.get("token")
    or payload.get("ha_token")
)
if not user or not password:
    raise SystemExit(
        "OpenBao secret missing username_dev_container/password_dev_container "
        "(or username-1/password-1)"
    )
# Print shell exports only; never log values elsewhere.
print(f"export TEST_HA_USERNAME={json.dumps(user)}")
print(f"export TEST_HA_PASSWORD={json.dumps(password)}")
if token:
    print(f"export TEST_HA_TOKEN={json.dumps(token)}")
PY
