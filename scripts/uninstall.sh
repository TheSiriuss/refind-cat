#!/usr/bin/env bash
# uninstall.sh [--esp DIR]
# Removes the refind-cat block from refind.conf and deletes themes/cat and the animation driver.
# (The backup made by install.sh stays in /var/backups/refind-cat/.)
set -euo pipefail
ESP=""; BEGIN='# >>> refind-cat >>>'; END='# <<< refind-cat <<<'
die() { echo "error: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
  case $1 in
    --esp) ESP=${2:?--esp needs a directory}; shift 2 ;;
    -h|--help) sed -n '2,4p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done
if [ -z "$ESP" ]; then for d in /boot /boot/efi /efi; do [ -f "$d/EFI/refind/refind.conf" ] && ESP=$d && break; done; fi
[ -n "$ESP" ] || die "could not find rEFInd; pass --esp DIR"
RD=$ESP/EFI/refind
[ -w "$RD" ] || die "$RD is not writable; run with sudo"
tmp=$(mktemp)
awk -v b="$BEGIN" -v e="$END" '$0==b{skip=1;next} $0==e{skip=0;next} !skip' "$RD/refind.conf" > "$tmp"
sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$tmp"
cat "$tmp" > "$RD/refind.conf"; rm -f "$tmp"
rm -rf "$RD/themes/cat"; rm -f "$RD/drivers_x64/cat_anim_x64.efi"
rmdir "$RD/themes" 2>/dev/null || true; rmdir "$RD/drivers_x64" 2>/dev/null || true
sync
echo "removed the refind-cat block, themes/cat and the animation driver from $RD"
