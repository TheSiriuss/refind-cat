#!/usr/bin/env bash
# Run with sudo.  Re-arms the animation driver after its NVRAM guard disabled it (two unconfirmed starts in a row).
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo: sudo bash $0"; exit 1; }
V=/sys/firmware/efi/efivars/CatAnimGuard-7c0a3f21-5d1e-4b6a-9a42-c10e6f2d9358
if [ -e "$V" ]; then chattr -i "$V" 2>/dev/null || true; rm -f "$V"; echo "guard cleared"; else echo "guard variable not set (driver is not disabled)"; fi
