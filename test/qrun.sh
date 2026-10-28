#!/usr/bin/env bash
# qrun.sh <esp-dir|esp.img> [extra qemu args]
# Boots an ESP in QEMU + OVMF (nothing touches a real disk).  A directory is mounted as a vvfat disk (slow, handy);
# an .img is attached as a real FAT32 image on an NVMe disk (fast, like a laptop).
# Env: QEMU_BIN, OVMF_CODE/OVMF_VARS, QEMU_ROOT (a package tree extracted from qemu-system-x86 + edk2-ovmf),
#      XRES/YRES unused (std VGA), QWORK (scratch dir), ACCEL (kvm|tcg).
set -euo pipefail
ESP=$(realpath "$1"); shift
W=${QWORK:-$(dirname "$ESP")/qwork}; mkdir -p "$W"
BIN=${QEMU_BIN:-qemu-system-x86_64}; EXTRA=(); FWDIRS=(/usr/share/edk2/x64 /usr/share/edk2-ovmf/x64 /usr/share/OVMF /usr/share/qemu)
if [ -n "${QEMU_ROOT:-}" ]; then
  BIN=$QEMU_ROOT/usr/bin/qemu-system-x86_64; export LD_LIBRARY_PATH=$QEMU_ROOT/usr/lib
  EXTRA=(-L "$QEMU_ROOT/usr/share/qemu"); FWDIRS=("$QEMU_ROOT/usr/share/edk2/x64" "${FWDIRS[@]}")
fi
CODE=${OVMF_CODE:-}; VARS_T=${OVMF_VARS:-}
if [ -z "$CODE" ]; then
  for d in "${FWDIRS[@]}"; do for c in OVMF_CODE.4m.fd OVMF_CODE_4M.fd OVMF_CODE.fd; do [ -f "$d/$c" ] && { CODE=$d/$c; VARS_T=$d/${c/CODE/VARS}; break 2; }; done; done
fi
[ -f "$CODE" ] && [ -f "$VARS_T" ] || { echo "OVMF firmware not found; set OVMF_CODE and OVMF_VARS" >&2; exit 1; }
cp -n "$VARS_T" "$W/vars.fd"
SOCK=$(mktemp -u /tmp/rcq.XXXXXX); echo "$SOCK" > "$W/mon.path"      # AF_UNIX paths are limited to ~100 chars, so keep it short
ACCEL=${ACCEL:-tcg}; [ -z "${ACCEL_FORCE:-}" ] && [ -w /dev/kvm ] && ACCEL=kvm; [ -n "${ACCEL_FORCE:-}" ] && ACCEL=$ACCEL_FORCE
case "$ESP" in
  *.img) DRV="-drive if=none,id=esp,format=raw,file=$ESP -device nvme,drive=esp,serial=esp0,bootindex=0" ;;
  *)     DRV="-drive format=raw,file=fat:rw:$ESP" ;;
esac
exec "$BIN" "${EXTRA[@]}" -machine q35,accel=$ACCEL -cpu max -m 1024 \
  -drive if=pflash,format=raw,readonly=on,file="$CODE" -drive if=pflash,format=raw,file="$W/vars.fd" \
  $DRV -vga std -display none -nic none \
  -pidfile "$W/qemu.pid" -monitor unix:"$SOCK",server,nowait -serial file:"$W/serial.log" "$@"
