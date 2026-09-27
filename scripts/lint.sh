#!/usr/bin/env bash
# Mirror CI Ruff step locally. Fix imports/style, then fail if anything remains.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v ruff >/dev/null 2>&1; then
  RUFF=(ruff)
elif command -v py >/dev/null 2>&1; then
  RUFF=(py -m ruff)
else
  RUFF=(python -m ruff)
fi

echo "==> ruff check --fix custom_components tests"
"${RUFF[@]}" check --fix custom_components tests

echo "==> ruff check custom_components tests"
"${RUFF[@]}" check custom_components tests

echo "Ruff OK (same gate as CI)."
