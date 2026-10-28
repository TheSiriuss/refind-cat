#!/usr/bin/env bash
# refind-cat installer.  One line, from anywhere:
#
#   curl -fsSL https://raw.githubusercontent.com/TheSiriuss/refind-cat/main/install.sh | sudo bash
#
# It downloads this repository, then runs scripts/install.sh, which backs up your rEFInd directory, copies the
# theme (and the animation driver) into it and adds one `include` line to refind.conf. It asks before it changes
# anything.  Options are passed through:  ... | sudo bash -s -- --no-driver --dry-run
# Environment: REFIND_CAT_REF (branch/tag, default main), REFIND_CAT_URL (tarball URL, for mirrors and tests).
set -euo pipefail

REPO=TheSiriuss/refind-cat
REF=${REFIND_CAT_REF:-main}
URL=${REFIND_CAT_URL:-https://github.com/$REPO/archive/$REF.tar.gz}

die() { echo "error: $*" >&2; exit 1; }

# running from a checkout: use it as is
SELF=${BASH_SOURCE[0]:-}
if [ -n "$SELF" ] && [ -f "$SELF" ]; then
  HERE=$(cd "$(dirname "$SELF")" && pwd)
  if [ -f "$HERE/scripts/install.sh" ] && [ -f "$HERE/dist/EFI/refind/themes/cat/theme.conf" ]; then
    exec bash "$HERE/scripts/install.sh" "$@"
  fi
fi

[ "$(uname -m)" = x86_64 ] || die "the animation driver is x86-64 only (found $(uname -m))"
[ -d /sys/firmware/efi ] || die "this system did not boot via UEFI; rEFInd themes need UEFI"
command -v tar >/dev/null || die "tar is required"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
echo "downloading $URL"
if command -v curl >/dev/null; then curl -fsSL "$URL" -o "$TMP/src.tar.gz"
elif command -v wget >/dev/null; then wget -q "$URL" -O "$TMP/src.tar.gz"
else die "curl or wget is required"; fi
mkdir "$TMP/src"; tar -xzf "$TMP/src.tar.gz" -C "$TMP/src" --strip-components=1
[ -f "$TMP/src/scripts/install.sh" ] || die "unexpected archive layout"
exec bash "$TMP/src/scripts/install.sh" "$@"
