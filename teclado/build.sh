#!/usr/bin/env bash
# Builds the R390XXU0AZA3 firmware package with the QWERTY-only Portuguese reply keyboard.
# Usage: teclado/build.sh <stock-aza3.bin> [out.bin]
# Needs: git, python3 with numpy and Pillow, arm-none-eabi-gcc, the Roboto font (fc-match "Roboto:medium").
set -euo pipefail

TOOLKIT_URL="https://github.com/Musicalista/fit3-toolkit-fork"
TOOLKIT_COMMIT="2c702e4b75765202d01ce36b1fdc8fd1affff59e"
STOCK_SHA256="25e692badec82afe111c517c19c5dbdb1d28c8558c2b027143c43f5c8d05998a"

here="$(cd "$(dirname "$0")" && pwd)"
stock="$(realpath "${1:?usage: teclado/build.sh <stock-aza3.bin> [out.bin]}")"
out="$(realpath -m "${2:-R390XXU0AZA3_teclado_qwerty_pt.bin}")"
work="${F3_TOOLKIT:-$here/../build/fit3-toolkit}"

actual="$(sha256sum "$stock" | cut -d' ' -f1)"
if [ "$actual" != "$STOCK_SHA256" ]; then
  echo "O firmware original não é o R390XXU0AZA3 esperado (sha256 $actual)." >&2
  exit 1
fi

if [ ! -d "$work/.git" ]; then
  git clone --quiet "$TOOLKIT_URL" "$work"
fi
git -C "$work" fetch --quiet --depth 1 origin "$TOOLKIT_COMMIT" 2>/dev/null || true
git -C "$work" checkout --quiet --force "$TOOLKIT_COMMIT"
git -C "$work" apply "$here/toolkit.patch"

cd "$work"
python3 -I src/build_firmware.py "$stock" "$out" --hub none --reply-keyboard --kb-lang pt
sha256sum "$out"
