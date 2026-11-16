#!/usr/bin/env bash
# Gera o firmware teclado+sensores com o experimento de ODR do acelerômetro (Etapa 1).
# Usage: barometro/sensorhub/build.sh <stock-aza3.bin> [out.bin]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; repo="$(cd "$here/../.." && pwd)"
stock="$(realpath "${1:?uso: build.sh <stock-aza3.bin> [out.bin]}")"
out="$(realpath -m "${2:-R390XXU0AZA3_accel1600.bin}")"
work="${F3_TOOLKIT:-$repo/build/fit3-toolkit}"
base="$(mktemp -u)/base.bin"; mkdir -p "$(dirname "$base")"
"$repo/barometro/watch/build.sh" "$stock" "$base" >/dev/null
python3 "$here/patch_odr.py" "$work/src/firmware" "$base" "$out"
