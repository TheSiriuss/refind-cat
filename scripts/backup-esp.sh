#!/usr/bin/env bash
# Run with sudo.  Copies the whole ESP (/boot) into a user-readable backup folder in $HOME, so the current rEFInd
# setup can be inspected and restored.  Reads /boot only; changes nothing on it.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo: sudo bash $0"; exit 1; }
U=${SUDO_USER:?run it through sudo from your own account}
DEST=/home/$U/refind-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p "$DEST"
cp -a /boot/. "$DEST/"
chown -R "$U:$U" "$DEST"
ln -sfn "$DEST" "/home/$U/refind-backup-latest"; chown -h "$U:$U" "/home/$U/refind-backup-latest"
echo "ESP backed up to $DEST ($(du -sh "$DEST" | cut -f1))"
echo "--- top of the tree:"
(cd "$DEST" && find . -maxdepth 3 -not -name '*.png' | sort | head -60)
