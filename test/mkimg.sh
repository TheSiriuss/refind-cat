#!/usr/bin/env bash
# mkimg.sh <esp-dir> <out.img> [size-MB]  -- pack a test ESP directory into a real FAT32 image (no root needed)
set -euo pipefail
D=$1; IMG=$2; MB=${3:-128}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; cp -rL "$D"/. "$T"/     # mtools skips symlinked dirs, so dereference first
rm -f "$IMG"; mkfs.fat -F 32 -C "$IMG" $((MB*1024)) >/dev/null
( cd "$T" && mcopy -s -m -i "$IMG" ./* :: )
