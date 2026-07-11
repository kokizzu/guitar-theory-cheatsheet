#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
PIP="${PIP:-/home/kyz/.local/bin/pip3}"
BASE_STEM="guitar_theory_cheatsheet_programmatic"
BUNDLE="guitar_cheatsheet_programmatic_bundle.zip"
RATIO_16_9_STEM="${BASE_STEM}_ratio_16_9"
RATIO_8_3_STEM="${BASE_STEM}_ratio_8_3"

legacy_files=(
  "${BASE_STEM}.svg"
  "${BASE_STEM}_1920x1080.png"
  "${BASE_STEM}_3840x2160.png"
)

output_files=(
  "${RATIO_16_9_STEM}.svg"
  "${RATIO_16_9_STEM}_1920x1080.png"
  "${RATIO_16_9_STEM}_3840x2160.png"
  "${RATIO_8_3_STEM}.svg"
  "${RATIO_8_3_STEM}_1920x720.png"
  "${RATIO_8_3_STEM}_3840x1440.png"
)

check_deps() {
  "$PYTHON" - <<'PY'
import cairosvg
import svgwrite
from PIL import Image
PY
}

deps() {
  "$PIP" install --user --break-system-packages svgwrite cairosvg
}

cleanup_legacy() {
  rm -f "${legacy_files[@]}"
}

generate_ratio() {
  local stem="$1"
  local width="$2"
  local height="$3"
  local scale_set="$4"

  "$PYTHON" guitar_cheatsheet_generator.py \
    --width "$width" \
    --height "$height" \
    --out-dir . \
    --stem "$stem" \
    --scale-set "$scale_set"
}

generate() {
  check_deps
  cleanup_legacy
  generate_ratio "$RATIO_16_9_STEM" 3840 2160 full
  generate_ratio "$RATIO_8_3_STEM" 3840 1440 major
}

bundle() {
  rm -f "$BUNDLE"
  zip -9 "$BUNDLE" \
    guitar_cheatsheet_generator.py \
    "${output_files[@]}"
}

verify() {
  check_deps
  "$PYTHON" - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path
import zipfile
from PIL import Image

bundle = Path("guitar_cheatsheet_programmatic_bundle.zip")
base_stem = "guitar_theory_cheatsheet_programmatic"
outputs = [
    (Path(f"{base_stem}_ratio_16_9.svg"), None),
    (Path(f"{base_stem}_ratio_16_9_1920x1080.png"), (1920, 1080)),
    (Path(f"{base_stem}_ratio_16_9_3840x2160.png"), (3840, 2160)),
    (Path(f"{base_stem}_ratio_8_3.svg"), None),
    (Path(f"{base_stem}_ratio_8_3_1920x720.png"), (1920, 720)),
    (Path(f"{base_stem}_ratio_8_3_3840x1440.png"), (3840, 1440)),
]
expected = [
    Path("guitar_cheatsheet_generator.py"),
    bundle,
    *[path for path, _ in outputs],
]
legacy = [
    Path(f"{base_stem}.svg"),
    Path(f"{base_stem}_1920x1080.png"),
    Path(f"{base_stem}_3840x2160.png"),
]

for path in expected:
    if not path.exists():
        raise SystemExit(f"missing expected file: {path}")
    if path.stat().st_size <= 0:
        raise SystemExit(f"empty expected file: {path}")

for path in legacy:
    if path.exists():
        raise SystemExit(f"legacy unsuffixed output still exists: {path}")

for path, size in outputs:
    if size is None:
        ET.parse(path)
    else:
        image = Image.open(path)
        if image.size != size:
            raise SystemExit(f"{path} has size {image.size}, expected {size}")
        image.verify()

with zipfile.ZipFile(bundle) as archive:
    bad_member = archive.testzip()
    if bad_member is not None:
        raise SystemExit(f"bad zip member: {bad_member}")
    names = set(archive.namelist())
    required = {"guitar_cheatsheet_generator.py", *[path.name for path, _ in outputs]}
    missing = required - names
    if missing:
        raise SystemExit(f"bundle missing entries: {sorted(missing)}")
    stale = {path.name for path in legacy} & names
    if stale:
        raise SystemExit(f"bundle contains legacy entries: {sorted(stale)}")

print("validated generated cheatsheet outputs")
PY
}

case "${1:-all}" in
  all)
    generate
    bundle
    verify
    ;;
  deps)
    deps
    ;;
  generate)
    generate
    ;;
  bundle)
    bundle
    ;;
  verify)
    verify
    ;;
  *)
    echo "usage: $0 [all|deps|generate|bundle|verify]" >&2
    exit 2
    ;;
esac
