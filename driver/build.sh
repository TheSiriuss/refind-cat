#!/usr/bin/env bash
# build.sh [debug]  -> cat_anim_x64.efi (PE32+, subsystem 11 = EFI boot-service driver). Needs clang + lld only.
set -euo pipefail
cd "$(dirname "$0")"
DEF=""; OUT=cat_anim_x64.efi
[ "${1:-}" = debug ] && { DEF="-DCATANIM_DEBUG"; OUT=cat_anim_x64.debug.efi; }
[ "${1:-}" = crash ] && { DEF="-DCATANIM_DEBUG -DCATANIM_CRASHTEST"; OUT=cat_anim_x64.crash.efi; }
clang -target x86_64-unknown-windows -ffreestanding -fno-builtin -fshort-wchar -mno-red-zone -mgeneral-regs-only \
      -fno-stack-protector -fno-stack-check -fno-asynchronous-unwind-tables -O2 -Wall -Wextra -Wno-unused-parameter $DEF -c cat_anim.c -o cat_anim.o
rm -f "$OUT"     # never leave a stale binary behind if linking fails
lld-link /subsystem:efi_boot_service_driver /entry:efi_main /nodefaultlib /dynamicbase /brepro /base:0x0 \
         /out:"$OUT" cat_anim.o
ls -l "$OUT"
