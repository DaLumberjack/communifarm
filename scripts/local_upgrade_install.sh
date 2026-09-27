#!/usr/bin/env bash
# Local T2 helper: copy current component into a local HA config and print next steps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HA_CONFIG="${HA_CONFIG:-$ROOT/devcontainer/ha_config}"
SRC="$ROOT/custom_components/communifarm"
DEST="$HA_CONFIG/custom_components/communifarm"

mkdir -p "$HA_CONFIG/custom_components"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$SRC/." "$DEST/"

VERSION="$(py - <<'PY' "$DEST/manifest.json"
import json, sys
print(json.load(open(sys.argv[1]))["version"])
PY
)"

echo "Installed communifarm $VERSION into $DEST"
echo "Restart local HA, then run Playwright with TEST_HA_STAGE=T2 TEST_HA_URL=http://127.0.0.1:8123"
echo "Do not wipe $HA_CONFIG/.storage during this upgrade check."
