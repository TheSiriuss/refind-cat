#!/usr/bin/env bash
# shot.sh <esp-dir|img> <out.png> [wait-seconds] [hmp-cmd ...]
# Boots in QEMU, waits, runs optional monitor commands (e.g. "sendkey right" "sleep:1"), takes a screenshot, quits.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ESP=$1; OUT=$2; WAIT=${3:-10}; shift 3 || shift $#
export QWORK=$(dirname "$(realpath "$ESP")")/qwork_$(basename "$ESP"); rm -rf "$QWORK"
( "$HERE/qrun.sh" "$ESP" >/dev/null 2>&1 & )
sleep "$WAIT"
python3 "$HERE/qctl.py" "$QWORK" "$@" "screendump ${OUT%.png}.ppm" sleep:1 quit >/dev/null
sleep 1; if [ -f "$QWORK/qemu.pid" ] && kill -0 "$(cat "$QWORK/qemu.pid")" 2>/dev/null; then kill "$(cat "$QWORK/qemu.pid")"; sleep 1; fi
magick "${OUT%.png}.ppm" "$OUT" 2>/dev/null || convert "${OUT%.png}.ppm" "$OUT"; rm -f "${OUT%.png}.ppm"
