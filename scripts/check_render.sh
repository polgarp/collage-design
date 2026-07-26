#!/usr/bin/env bash
# Prove the shipped .svg is portable: render it in TWO engines (inkscape + rsvg-convert) at the
# same size and compare. A low RMSE means the SVG renders identically everywhere (filter-free,
# text vectorized) — so the shipped .png (which IS the inkscape render) matches the .svg in any
# viewer. A high RMSE means a renderer-dependent filter or an un-vectorized font leaked in; fix it
# before shipping.
# Usage: check_render.sh <collage.svg> [fontconfig-file]
#   NOTE: the second argument is the FONTCONFIG file (as printed by setup_fonts.sh), not the PNG.
#   The .png is not an input — this compares the SVG against itself across two renderers.
set -uo pipefail

svg="${1:?usage: check_render.sh <collage.svg> [fontconfig-file]}"
conf="${2:-}"
w=800
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

case "$conf" in
  *.png|*.jpg|*.jpeg|*.svg)
    echo "check_render.sh: arg 2 is the fontconfig file, not an image — got '$conf'" >&2
    echo "  usage: check_render.sh <collage.svg> [fontconfig-file]" >&2
    exit 2 ;;
esac
[ -n "$conf" ] && export FONTCONFIG_FILE="$conf"

# ImageMagick 7 is `magick` + `magick compare`; IM6 (still standard on Debian/Ubuntu LTS)
# ships `convert` + `compare` as separate binaries. Support both.
if command -v magick >/dev/null 2>&1; then IM="magick"; IMCMP="magick compare"
elif command -v convert >/dev/null 2>&1; then IM="convert"; IMCMP="compare"
else echo "check_render.sh: ImageMagick not found (need 'magick' or 'convert')" >&2; exit 2; fi

inkscape "$svg" --export-type=png --export-filename="$tmp/ink.png" -w "$w" >/dev/null 2>&1
[ -s "$tmp/ink.png" ] || { echo "check_render.sh: inkscape produced no output for $svg" >&2; exit 2; }
rsvg-convert -w "$w" "$svg" -o "$tmp/rsvg.png" || { echo "check_render.sh: rsvg-convert failed on $svg" >&2; exit 2; }
# match heights too, in case the two engines round differently
$IM "$tmp/rsvg.png" -resize "${w}x!" -background white -flatten "$tmp/rsvg2.png"
$IM "$tmp/ink.png"  -resize "${w}x!" -background white -flatten "$tmp/ink2.png"

# -metric RMSE prints "<absolute> (<normalized>)"; the normalized value goes SCIENTIFIC
# (e.g. 9.98e-05) exactly when the render is near-perfect, so the exponent chars must be
# part of the match or a passing check would fail to parse.
out="$($IMCMP -metric RMSE "$tmp/ink2.png" "$tmp/rsvg2.png" null: 2>&1 || true)"
norm="$(printf '%s' "$out" | sed -n 's/.*(\([0-9.eE+-]*\)).*/\1/p')"
[ -z "$norm" ] && { echo "check failed to parse compare output: $out" >&2; exit 2; }

awk -v n="$norm" 'BEGIN{
  v = n + 0
  if (v <= 0.02) { printf "PASS  svg==png  (RMSE %.6f)\n", v }
  else { printf "FAIL  svg!=png  (RMSE %.6f) — a filter or un-vectorized font leaked into the SVG\n", v; exit 1 }
}'
