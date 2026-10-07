#!/usr/bin/env bash
# Validate committed local E2E summary (used by CI and locally).
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v py >/dev/null 2>&1; then
  PYTHON=(py)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=(python3)
else
  PYTHON=(python)
fi

exec "${PYTHON[@]}" scripts/e2e_local_report.py validate "$@"
