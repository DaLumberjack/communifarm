#!/usr/bin/env bash
# Bump communifarm manifest version (used on merge-to-main / T2 prep).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/custom_components/communifarm/manifest.json"

if [[ ! -f "$MANIFEST" ]]; then
  echo "manifest not found: $MANIFEST" >&2
  exit 1
fi

CURRENT="$(py - <<'PY' "$MANIFEST"
import json, sys
print(json.load(open(sys.argv[1]))["version"])
PY
)"

IFS=. read -r MAJOR MINOR PATCH <<<"$CURRENT"
PATCH=$((PATCH + 1))
NEW="${MAJOR}.${MINOR}.${PATCH}"

py - <<'PY' "$MANIFEST" "$NEW"
import json, sys
path, version = sys.argv[1], sys.argv[2]
data = json.load(open(path))
data["version"] = version
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
print(f"bumped {data.get('domain')} {version}")
PY

# Keep const.VERSION in sync when present.
CONST="$ROOT/custom_components/communifarm/const.py"
if grep -q '^VERSION = ' "$CONST"; then
  sed -i.bak "s/^VERSION = .*/VERSION = \"$NEW\"/" "$CONST"
  rm -f "$CONST.bak"
fi

echo "New version: $NEW"
