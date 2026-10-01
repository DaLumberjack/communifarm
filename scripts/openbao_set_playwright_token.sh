#!/usr/bin/env bash
# Patch OpenBao kv/ha-test with the Playwright long-lived HA token.
# Prerequisite: OpenBao running + unsealed + bao login (see docs/user/openbao.md).
# Prerequisite: yarn test:e2e:t1:provision-token (writes e2e/.generated/ha-token.env)
#
# Usage:
#   ./scripts/openbao_set_playwright_token.sh
#   TEST_HA_TOKEN=... ./scripts/openbao_set_playwright_token.sh
#   ./scripts/openbao_set_playwright_token.sh /path/to/ha-token.env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIELD="dev_container_playwright_long_lived_access_token"
DEFAULT_ENV="${ROOT}/e2e/.generated/ha-token.env"
ENV_FILE="${1:-$DEFAULT_ENV}"

ADDR="${BAO_ADDR:-${VAULT_ADDR:-http://127.0.0.1:8200}}"
NAMESPACE="${BAO_NAMESPACE:-${VAULT_NAMESPACE:-homelab}}"
TOKEN="${BAO_TOKEN:-${VAULT_TOKEN:-}}"
MOUNT="${OPENBAO_KV_MOUNT:-kv}"
PATH_NAME="${OPENBAO_HA_PATH:-ha-test}"

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
if [[ -n "$TOKEN" ]]; then
  export BAO_TOKEN="$TOKEN" VAULT_TOKEN="$TOKEN"
fi

HA_TOKEN="${TEST_HA_TOKEN:-}"
if [[ -z "$HA_TOKEN" && -f "$ENV_FILE" ]]; then
  HA_TOKEN="$(
    ENV_FILE="$ENV_FILE" py -3 - <<'PY'
import json, os
from pathlib import Path
path = Path(os.environ["ENV_FILE"])
for line in path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, val = line.partition("=")
    if key.strip() != "TEST_HA_TOKEN":
        continue
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        try:
            val = json.loads(val)
        except json.JSONDecodeError:
            val = val[1:-1]
    print(val)
    break
else:
    raise SystemExit(f"TEST_HA_TOKEN not found in {path}")
PY
  )"
fi

if [[ -z "$HA_TOKEN" ]]; then
  echo "No token. Run: yarn test:e2e:t1:provision-token" >&2
  echo "Or set TEST_HA_TOKEN / pass an env file path." >&2
  exit 1
fi

# KV v2 patch keeps existing username/password fields.
if ! "${CLI[@]}" kv patch -mount="$MOUNT" "$PATH_NAME" "${FIELD}=${HA_TOKEN}" >/dev/null; then
  echo "kv patch failed for ${MOUNT}/${PATH_NAME} (namespace=${NAMESPACE})." >&2
  echo "Is OpenBao unsealed? Run: bao login" >&2
  exit 1
fi

echo "Patched ${MOUNT}/${PATH_NAME} field ${FIELD} (namespace=${NAMESPACE})."
echo "Playwright will pick it up on the next yarn test:e2e:* run."
