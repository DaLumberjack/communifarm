#!/usr/bin/env bash
# Run merge-blocking local Playwright suites and write committed CI artifacts.
# Requires local HA (devcontainer) + OpenBao secrets — not for hosted CI.
set -euo pipefail
cd "$(dirname "$0")/.."

# Raw Playwright JSON must NOT live under test-results/ — Playwright empties
# that directory at the start of every run and would wipe the first suite.
RAW_DIR=e2e/.generated/reports
mkdir -p "$RAW_DIR" test-results/e2e

if command -v py >/dev/null 2>&1; then
  PYTHON=(py)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=(python3)
else
  PYTHON=(python)
fi

echo "==> T1 seeded (raw JSON)"
TEST_REPORT_JSON="$RAW_DIR/raw-t1-seeded.json" \
  yarn test:e2e:t1:seeded
test -f "$RAW_DIR/raw-t1-seeded.json" || {
  echo "ERROR: missing $RAW_DIR/raw-t1-seeded.json after seeded run" >&2
  exit 1
}

echo "==> T1 POS (raw JSON)"
TEST_REPORT_JSON="$RAW_DIR/raw-t1-pos.json" \
  yarn test:e2e:t1:pos
test -f "$RAW_DIR/raw-t1-pos.json" || {
  echo "ERROR: missing $RAW_DIR/raw-t1-pos.json after POS run" >&2
  exit 1
}

echo "==> Summarize for MR gate"
"${PYTHON[@]}" scripts/e2e_local_report.py summarize \
  --suite "t1_seeded:$RAW_DIR/raw-t1-seeded.json" \
  --suite "t1_pos:$RAW_DIR/raw-t1-pos.json" \
  --output test-results/e2e/summary.json \
  --markdown test-results/e2e/summary.md

echo "Commit test-results/e2e/summary.json and summary.md with this HEAD before opening the MR."
