#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
PIP="${PIP:-/home/kyz/.local/bin/pip3}"
STEM="guitar_theory_cheatsheet_programmatic"
BUNDLE="guitar_cheatsheet_programmatic_bundle.zip"

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

generate() {
  check_deps
  "$PYTHON" guitar_cheatsheet_generator.py \
    --out-dir . \
    --stem "$STEM"
}

bundle() {
  zip -9 "$BUNDLE" \
    guitar_cheatsheet_generator.py \
    "${STEM}.svg" \
    "${STEM}_1920x1080.png" \
    "${STEM}_3840x2160.png"
}

verify() {
  check_deps
  "$PYTHON" - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
from PIL import Image

stem = "guitar_theory_cheatsheet_programmatic"
bundle = Path("guitar_cheatsheet_programmatic_bundle.zip")
expected = [
    Path("guitar_cheatsheet_generator.py"),
    Path(f"{stem}.svg"),
    Path(f"{stem}_1920x1080.png"),
    Path(f"{stem}_3840x2160.png"),
    bundle,
]

for path in expected:
    if not path.exists():
        raise SystemExit(f"missing expected file: {path}")
    if path.stat().st_size <= 0:
        raise SystemExit(f"empty expected file: {path}")

ET.parse(f"{stem}.svg")

for path, size in [
    (Path(f"{stem}_1920x1080.png"), (1920, 1080)),
    (Path(f"{stem}_3840x2160.png"), (3840, 2160)),
]:
    image = Image.open(path)
    if image.size != size:
        raise SystemExit(f"{path} has size {image.size}, expected {size}")
    image.verify()

with zipfile.ZipFile(bundle) as archive:
    bad_member = archive.testzip()
    if bad_member is not None:
        raise SystemExit(f"bad zip member: {bad_member}")
    names = set(archive.namelist())
    required = {path.name for path in expected[:-1]}
    missing = required - names
    if missing:
        raise SystemExit(f"bundle missing entries: {sorted(missing)}")

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
