#!/usr/bin/env bash
# Deploy Communifarm to the HAOS test VM only (192.168.102.20).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/custom_components/communifarm"
ALLOWED_HOST="192.168.102.20"
HOST="${HA_TEST_HOST:-$ALLOWED_HOST}"
SSH_USER="${HA_TEST_SSH_USER:-root}"
REMOTE_BASE="${HA_TEST_REMOTE_CONFIG:-/config}"
SSH_KEY="${HA_TEST_SSH_KEY:-}"
KNOWN_HOSTS="${HA_TEST_KNOWN_HOSTS:-$ROOT/scripts/known_hosts.test}"
DRY_RUN="${DRY_RUN:-1}"
ACTION="${1:-deploy}"

if [[ "$HOST" != "$ALLOWED_HOST" ]]; then
  echo "Refusing host '$HOST' — only $ALLOWED_HOST is allowed" >&2
  exit 1
fi

if [[ ! -d "$SRC" ]]; then
  echo "Source missing: $SRC" >&2
  exit 1
fi

SSH_OPTS=(-o "UserKnownHostsFile=$KNOWN_HOSTS" -o "StrictHostKeyChecking=yes")
if [[ -n "$SSH_KEY" ]]; then
  SSH_OPTS+=(-i "$SSH_KEY")
fi

REMOTE="${SSH_USER}@${HOST}"
STAGING="${REMOTE_BASE}/.communifarm_staging/communifarm"
TARGET="${REMOTE_BASE}/custom_components/communifarm"
BACKUP="${REMOTE_BASE}/.communifarm_backup/communifarm"

ssh_cmd() {
  ssh "${SSH_OPTS[@]}" "$REMOTE" "$@"
}

rsync_cmd() {
  local extra=()
  if [[ "$DRY_RUN" == "1" ]]; then
    extra+=(-n)
  fi
  rsync -avz --delete "${extra[@]}" -e "ssh ${SSH_OPTS[*]}" "$SRC/" "${REMOTE}:${STAGING}/"
}

case "$ACTION" in
  dry-run)
    DRY_RUN=1
    echo "Dry-run sync to $REMOTE:$STAGING"
    ssh_cmd "mkdir -p '$STAGING' '$REMOTE_BASE/custom_components' '$REMOTE_BASE/.communifarm_backup'"
    rsync_cmd
    ;;
  deploy)
    DRY_RUN=0
    echo "Deploying to $REMOTE (test VM only)"
    ssh_cmd "mkdir -p '$STAGING' '$REMOTE_BASE/custom_components' '$REMOTE_BASE/.communifarm_backup'"
    # Stage first
    rsync_cmd
    # Verify staged manifest
    ssh_cmd "test -f '$STAGING/manifest.json' && python3 -c \"import json; d=json.load(open('$STAGING/manifest.json')); assert d['domain']=='communifarm'\""
    # Backup previous
    ssh_cmd "if [ -d '$TARGET' ]; then rm -rf '$BACKUP'; mv '$TARGET' '$BACKUP'; fi"
    # Atomic-ish replace
    ssh_cmd "mkdir -p '$TARGET' && cp -a '$STAGING/.' '$TARGET/'"
    ssh_cmd "ha core check || true"
    ssh_cmd "ha core restart"
    echo "Deploy complete. Verify with: ssh $REMOTE 'ha core info' and logs for communifarm"
    ;;
  rollback)
    echo "Rolling back on $REMOTE"
    ssh_cmd "test -d '$BACKUP'"
    ssh_cmd "rm -rf '$TARGET'; mv '$BACKUP' '$TARGET'"
    ssh_cmd "ha core restart"
    echo "Rollback complete"
    ;;
  *)
    echo "Usage: $0 [dry-run|deploy|rollback]" >&2
    exit 1
    ;;
esac
