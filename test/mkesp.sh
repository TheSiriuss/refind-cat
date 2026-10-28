#!/usr/bin/env bash
# mkesp.sh <esp-dir> <refind.conf>
# Assembles a throw-away test ESP: the stock rEFInd binary + your conf (+ dist/ theme and driver unless INSTALL=0).
# Env: REFIND_DIR (default /usr/share/refind), BUILD (default dist/EFI/refind), DRIVER (default the built driver),
#      INSTALL=0 -> leave the theme out (a "before" ESP for the installer test).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ESP=$1; CONF=$2; RD=${REFIND_DIR:-/usr/share/refind}
rm -rf "$ESP"; mkdir -p "$ESP/EFI/refind"
cp "$RD/refind_x64.efi" "$ESP/EFI/refind/refind_x64.efi"; cp "$RD/refind_x64.efi" "$ESP/EFI/refind/BOOTX64.EFI"
cp -r "$RD/icons" "$ESP/EFI/refind/icons"
cp "$CONF" "$ESP/EFI/refind/refind.conf"
ln -s refind "$ESP/EFI/BOOT"                                   # the firmware's fallback path
cp "$RD/tools_x64/gptsync_x64.efi" "$ESP/vmlinuz-linux-cachyos"  # a harmless EFI program standing in for the kernel
if [ "${INSTALL:-1}" = 1 ]; then
  cp -r "${BUILD:-$ROOT/dist/EFI/refind}/themes" "$ESP/EFI/refind/themes"
  D=${DRIVER:-${BUILD:-$ROOT/dist/EFI/refind}/drivers_x64/cat_anim_x64.efi}
  [ -f "$D" ] && { mkdir -p "$ESP/EFI/refind/drivers_x64"; cp "$D" "$ESP/EFI/refind/drivers_x64/cat_anim_x64.efi"; }
fi
