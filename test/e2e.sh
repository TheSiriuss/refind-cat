#!/usr/bin/env bash
# e2e.sh -- end to end: a plain rEFInd ESP -> scripts/install.sh -> boot in QEMU -> check the screen and that it moves.
# Needs qemu-system-x86_64 + OVMF (see test/qrun.sh), mtools, dosfstools, ImageMagick, and the rEFInd package files.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd); T=${E2E_DIR:-${TMPDIR:-/tmp}/refind-cat-e2e}
rm -rf "$T"; mkdir -p "$T"; IM=$(command -v magick || command -v convert)
cleanup() { [ -f "${QWORK:-/nonexistent}/qemu.pid" ] && kill "$(cat "$QWORK/qemu.pid")" 2>/dev/null || true; }
trap cleanup EXIT
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; exit 1; }

echo "1. plain ESP with the user's own refind.conf"
INSTALL=0 "$ROOT/test/mkesp.sh" "$T/esp" "$ROOT/test/user.conf"
cp "$T/esp/EFI/refind/refind.conf" "$T/orig.conf"

echo "2. install (twice: must stay idempotent), then uninstall must restore the config"
BACKUP_DIR="$T/backup" "$ROOT/scripts/install.sh" --esp "$T/esp" --yes >"$T/install.log"
BACKUP_DIR="$T/backup" "$ROOT/scripts/install.sh" --esp "$T/esp" --yes >>"$T/install.log"
[ "$(grep -c '>>> refind-cat >>>' "$T/esp/EFI/refind/refind.conf")" = 1 ] && ok "exactly one include block after two installs" || bad "include block duplicated"
[ -f "$T/esp/EFI/refind/themes/cat/theme.conf" ] && [ -f "$T/esp/EFI/refind/drivers_x64/cat_anim_x64.efi" ] && ok "theme and driver copied" || bad "files missing"
ls "$T"/backup/*/refind.conf >/dev/null && ok "backup written" || bad "no backup"
cp -r "$T/esp" "$T/esp_installed"
"$ROOT/scripts/uninstall.sh" --esp "$T/esp" >/dev/null
diff -q "$T/orig.conf" "$T/esp/EFI/refind/refind.conf" >/dev/null && ok "uninstall restores refind.conf byte for byte" || bad "refind.conf differs after uninstall"
[ ! -e "$T/esp/EFI/refind/themes" ] && [ ! -e "$T/esp/EFI/refind/drivers_x64" ] && ok "uninstall removed theme and driver" || bad "leftovers after uninstall"

echo "3. boot the installed ESP in QEMU"
"$ROOT/test/mkimg.sh" "$T/esp_installed" "$T/esp.img" 128
export QWORK="$T/qwork"; rm -rf "$QWORK"
( "$ROOT/test/qrun.sh" "$T/esp.img" >/dev/null 2>&1 & )
"$ROOT/test/waitmenu.sh" "$QWORK" 60 || bad "the menu never came up"
shot() { python3 "$ROOT/test/qctl.py" "$QWORK" "screendump $T/$1.ppm" >/dev/null; }
shot f0; sleep 0.7; shot f1; sleep 0.7; shot f2; sleep 0.7; shot f3; sleep 0.7; shot f4; sleep 0.7; shot f5
python3 "$ROOT/test/qctl.py" "$QWORK" "sendkey ret" sleep:2.5 "screendump $T/launched.ppm" quit >/dev/null 2>&1 || true
sleep 1; [ -f "$QWORK/qemu.pid" ] && kill "$(cat "$QWORK/qemu.pid")" 2>/dev/null || true
px() { "$IM" "$T/$1.ppm" -crop 1x1+$2+$3 +repage -format '%[fx:int(p.r*255)] %[fx:int(p.g*255)] %[fx:int(p.b*255)]' info:; }
read -r R G B <<<"$(px f0 960 467)"
{ [ "$R" -gt 190 ] && [ "$G" -gt 120 ] && [ "$B" -lt 150 ]; } && ok "themed menu is up (selection ring pixel $R $G $B)" || bad "menu not themed (pixel $R $G $B)"
MOVED=0
for i in 1 2 3 4 5; do
  d=$("$IM" compare -metric AE "$T/f0.ppm" "$T/f$i.ppm" null: 2>&1 || true); d=$(echo "$d" | awk '{printf "%d", $1}')
  [ "${d:-0}" -gt 20 ] && MOVED=1
done
[ "$MOVED" = 1 ] && ok "the picture changes between frames (animation running)" || bad "frames are identical, animation not running"
c=$("$IM" "$T/launched.ppm" -resize 10% -format %k info:); [ "$c" -lt 600 ] && ok "after Enter the screen is the plain text boot screen ($c colours)" || bad "theme pixels left on screen after launch ($c colours)"
echo "all checks passed"
