#!/usr/bin/env bash
# record.sh <esp-tree> <out-dir>   (esp-tree = a dist/EFI/refind directory)
# Boots the theme in QEMU and records stills, a time-stamped frame sequence, and mp4/gif clips for the README.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
B=$(realpath "$1"); OUT=$(realpath -m "$2"); T=$(mktemp -d /tmp/rc.XXXXXX)
rm -rf "$OUT"; mkdir -p "$OUT/seq"
{ cat "$ROOT/test/user.conf"; printf '\ninclude themes/cat/theme.conf\n'; } > "$T/refind.conf"
BUILD=$B "$ROOT/test/mkesp.sh" "$T/esp" "$T/refind.conf"
"$ROOT/test/mkimg.sh" "$T/esp" "$T/esp.img" 128
export QWORK=$T/qwork
( "$ROOT/test/qrun.sh" "$T/esp.img" >/dev/null 2>&1 & )
"$ROOT/test/waitmenu.sh" "$QWORK" 60
python3 "$ROOT/test/qctl.py" "$QWORK" "screendump $OUT/menu.ppm" >/dev/null
python3 "$ROOT/test/capture.py" "$QWORK" "$OUT/seq" 160 0.045
python3 "$ROOT/test/qctl.py" "$QWORK" "sendkey right" sleep:1.2 "screendump $OUT/tools.ppm" "sendkey left" sleep:1 >/dev/null
python3 "$ROOT/test/qctl.py" "$QWORK" "sendkey ret" sleep:2.5 "screendump $OUT/launch.ppm" quit >/dev/null 2>&1 || true
sleep 1; [ -f "$QWORK/qemu.pid" ] && kill "$(cat "$QWORK/qemu.pid")" 2>/dev/null || true
cd "$OUT"
python3 - <<'PY'
ts=[float(x) for x in open('seq/times.txt').read().split()]; L=[]
for i,t in enumerate(ts):
    d=(ts[i+1]-t) if i+1<len(ts) else 0.05
    L.append(f"file 'seq/f{i:03d}.ppm'\nduration {d:.4f}")
L.append(f"file 'seq/f{len(ts)-1:03d}.ppm'"); open('concat.txt','w').write('\n'.join(L))
PY
q() { ffmpeg -loglevel error -y -f concat -safe 0 -i concat.txt "$@"; }
q -vf "crop=288:288:816:456,fps=12,scale=320:320:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" cat.gif
q -vf "fps=10,scale=760:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5" scene.gif
for n in menu tools launch; do "$(command -v magick || command -v convert)" $n.ppm -resize 1600x -quality 88 $n.jpg; done
rm -rf seq concat.txt "$T" menu.ppm tools.ppm launch.ppm; ls -la "$OUT"
