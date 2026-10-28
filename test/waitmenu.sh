#!/usr/bin/env bash
# waitmenu.sh <qwork-dir> [timeout-s]  -- returns 0 once the themed menu is on screen (amber selection ring at 960,467)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); W=$1; N=${2:-60}; IM=$(command -v magick || command -v convert)
F=$(mktemp /tmp/rcw.XXXXXX.ppm); trap 'rm -f "$F"' EXIT
for _ in $(seq 1 "$N"); do
  sleep 1
  python3 "$HERE/qctl.py" "$W" "screendump $F" >/dev/null 2>&1 || continue
  read -r R G B <<<"$("$IM" "$F" -crop 1x1+960+467 +repage -format '%[fx:int(p.r*255)] %[fx:int(p.g*255)] %[fx:int(p.b*255)]' info: 2>/dev/null || echo "0 0 0")"
  if [ "$R" -gt 190 ] && [ "$G" -gt 120 ] && [ "$B" -lt 150 ]; then sleep 2; exit 0; fi
done
echo "menu did not appear within ${N}s" >&2; exit 1
