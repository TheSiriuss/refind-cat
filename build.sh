#!/usr/bin/env bash
# build.sh [--cutout]      VARIANT=night|day  DIST=<output dir> ./build.sh
#
# Regenerates dist/EFI/refind  (theme PNGs, anim.bin, and the animation driver) from art/source.
#   --cutout   also re-extract the cat from art/source/painting.png (GrabCut; slow, the result is committed)
# Needs: python3 (a venv is created in .venv), clang + lld for the driver.
set -euo pipefail
cd "$(dirname "$0")"
export VARIANT=${VARIANT:-night}
export DIST=$(realpath -m "${DIST:-dist}")      # output tree, default ./dist
if [ -z "${PYTHON:-}" ]; then
  [ -x .venv/bin/python ] || { python3 -m venv .venv; .venv/bin/pip install -q -r requirements.txt; }
  PYTHON=.venv/bin/python
fi
mkdir -p art/work "$DIST/EFI/refind/themes/cat/icons" "$DIST/EFI/refind/drivers_x64"

if [ "${1:-}" = "--cutout" ]; then
  echo ">> cutting the cat out of the painting"
  cp art/source/painting.png art/work/src.png
  for s in 01_head 02_bird 03_cutout; do $PYTHON art/cutout/$s.py; done
  cp art/work/cat_full.png art/cat_cutout.png
  $PYTHON art/cutout/04_layers.py
fi

echo ">> background ($VARIANT)"
$PYTHON art/make_bg.py
cp art/work/bg.png "$DIST/EFI/refind/themes/cat/bg.png"
echo ">> theme assets"
$PYTHON art/make_theme.py
cp art/theme.conf "$DIST/EFI/refind/themes/cat/theme.conf"
echo ">> animation data"
$PYTHON art/make_anim.py
echo ">> driver"
driver/build.sh
cp driver/cat_anim_x64.efi "$DIST/EFI/refind/drivers_x64/cat_anim_x64.efi"
echo "done: $DIST/EFI/refind"
