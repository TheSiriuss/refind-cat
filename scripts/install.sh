#!/usr/bin/env bash
# install.sh [--esp DIR] [--no-driver] [--dry-run] [--yes]
#
# Installs the theme (and the animation driver) into an existing rEFInd on the EFI System Partition:
#   1. backs up the rEFInd directory and refind.conf to /var/backups/refind-cat/<timestamp>/
#   2. copies  dist/EFI/refind/themes/cat      ->  <ESP>/EFI/refind/themes/cat
#              dist/EFI/refind/drivers_x64/... ->  <ESP>/EFI/refind/drivers_x64/   (skipped with --no-driver)
#   3. appends one marked block to refind.conf:  include themes/cat/theme.conf      (re-running replaces it)
# With Secure Boot enabled only the theme is installed (the animation driver is unsigned).
# It never touches the firmware boot entries and never replaces the rEFInd binary.
# Undo with scripts/uninstall.sh.  Needs root unless the ESP directory is writable by you.
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd); SRC=$HERE/dist/EFI/refind
ESP=""; WITH_DRIVER=1; DRY=0; YES=0
BEGIN='# >>> refind-cat >>>'; END='# <<< refind-cat <<<'
GUARD=/sys/firmware/efi/efivars/CatAnimGuard-7c0a3f21-5d1e-4b6a-9a42-c10e6f2d9358

die() { echo "error: $*" >&2; exit 1; }
run() { if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

while [ $# -gt 0 ]; do
  case $1 in
    --esp) ESP=${2:?--esp needs a directory}; shift 2 ;;
    --no-driver) WITH_DRIVER=0; shift ;;
    --dry-run) DRY=1; shift ;;
    -y|--yes) YES=1; shift ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

CUSTOM_ESP=1
if [ -z "$ESP" ]; then
  CUSTOM_ESP=0
  for d in /boot /boot/efi /efi; do [ -f "$d/EFI/refind/refind.conf" ] && ESP=$d && break; done
  [ -n "$ESP" ] || die "could not find rEFInd (looked for EFI/refind/refind.conf under /boot, /boot/efi, /efi); pass --esp DIR"
fi
RD=$ESP/EFI/refind
[ -f "$RD/refind.conf" ] || die "$RD/refind.conf not found"
[ -f "$SRC/themes/cat/theme.conf" ] || die "dist/ is missing; run ./build.sh first"
if [ "$DRY" = 0 ] && [ ! -w "$RD" ]; then die "$RD is not writable; run with sudo"; fi

# Secure Boot: rEFInd would refuse to load our unsigned driver, so install the theme alone in that case
SB=/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c
if [ "$WITH_DRIVER" = 1 ] && [ -r "$SB" ] && [ "$(od -An -tu1 -j4 -N1 "$SB" 2>/dev/null | tr -d ' ')" = 1 ]; then
  echo "note: Secure Boot is enabled; installing the theme without the (unsigned) animation driver."
  WITH_DRIVER=0
fi

STAMP=$(date +%Y%m%d-%H%M%S)
BK=${BACKUP_DIR:-/var/backups/refind-cat}/$STAMP
echo "rEFInd directory : $RD"
echo "backup           : $BK"

if [ "$DRY" = 0 ] && [ "$YES" = 0 ]; then
  if (: </dev/tty) 2>/dev/null; then read -r -p "Install the theme into $RD ? [y/N] " ans </dev/tty; else die "no terminal to ask on; pass --yes"; fi
  case $ans in y|Y|yes|YES) ;; *) echo "aborted, nothing changed."; exit 1 ;; esac
fi

run mkdir -p "$BK"
run cp -a "$RD/refind.conf" "$BK/refind.conf"
run cp "$HERE/scripts/uninstall.sh" "$BK/uninstall.sh"      # lives next to the backup, so it survives a curl|bash install
run tar -C "$ESP/EFI" -czf "$BK/refind-dir.tar.gz" refind

echo "theme            : $RD/themes/cat"
run rm -rf "$RD/themes/cat"
run mkdir -p "$RD/themes"
run cp -r "$SRC/themes/cat" "$RD/themes/cat"

if [ "$WITH_DRIVER" = 1 ]; then
  echo "animation driver : $RD/drivers_x64/cat_anim_x64.efi"
  run mkdir -p "$RD/drivers_x64"
  run cp "$SRC/drivers_x64/cat_anim_x64.efi" "$RD/drivers_x64/cat_anim_x64.efi"
else
  echo "animation driver : skipped (--no-driver)"
  run rm -f "$RD/drivers_x64/cat_anim_x64.efi"
fi

# marked block in refind.conf: strip an old one, append the new one at the end (so its settings win)
if [ "$DRY" = 1 ]; then
  echo "  [dry-run] append '$BEGIN / include themes/cat/theme.conf / $END' to $RD/refind.conf"
else
  tmp=$(mktemp)
  awk -v b="$BEGIN" -v e="$END" '$0==b{skip=1;next} $0==e{skip=0;next} !skip' "$RD/refind.conf" > "$tmp"
  # drop trailing blank lines, then add the block
  sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$tmp"
  { cat "$tmp"; printf '\n%s\ninclude themes/cat/theme.conf\n%s\n' "$BEGIN" "$END"; } > "$RD/refind.conf.new"
  rm -f "$tmp"; mv "$RD/refind.conf.new" "$RD/refind.conf"
fi

# re-arm the driver's crash guard if an earlier run had disabled it
if [ "$CUSTOM_ESP" = 0 ] && [ "$DRY" = 0 ] && [ -e "$GUARD" ]; then chattr -i "$GUARD" 2>/dev/null || true; rm -f "$GUARD" && echo "driver guard     : cleared"; fi
[ "$DRY" = 0 ] && sync

cat <<MSG

Installed.  To get the cat as the logo of your own entry, give its stanza the icon, e.g.

    menuentry "CachyOS" {
        icon   /EFI/refind/themes/cat/icons/os_cachyos.png
        ...
    }

The animation needs the screen to run at 1920x1200 (add "resolution max" or "resolution 1920 1200" to refind.conf
if rEFInd picks something else); at any other size the static theme is shown.
Undo:  sudo bash $BK/uninstall.sh$([ "$CUSTOM_ESP" = 1 ] && echo " --esp $ESP")
MSG
