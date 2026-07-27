#!/usr/bin/env bash
# Prove the shipped .svg is portable: render it in TWO engines (inkscape + rsvg-convert) at the
# same size and compare. A low RMSE means the SVG renders identically everywhere (filter-free,
# text vectorized) — so the shipped .png (which IS the inkscape render) matches the .svg in any
# viewer. A high RMSE means a renderer-dependent filter or an un-vectorized font leaked in; fix it
# before shipping.
# Usage: check_render.sh <collage.svg> [fontconfig-file] [compare-width]
#   NOTE: the second argument is the FONTCONFIG file (as printed by setup_fonts.sh), not the PNG.
#   The .png is not an input — this compares the SVG against itself across two renderers.
#   Compare width defaults to half the artwork's width (capped 800..1600); pass it explicitly to
#   re-check a grain-heavy piece at full size. On failure a diff image is written beside the SVG.
set -uo pipefail

svg="${1:?usage: check_render.sh <collage.svg> [fontconfig-file]}"
conf="${2:-}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
diff_png="${svg%.svg}.diff.png"

# Compare at half the artwork's own width rather than a fixed 800. Two engines' DOWNSAMPLERS
# disagree about per-pixel noise, so the harder a piece is downscaled the more its grain shows
# up as divergence that isn't in the file (measured on one 3600px grain-heavy piece: 0.0282 at
# w=800, 0.00075 at w=2400). Capped, because the check should stay quick.
art_w="$(grep -o '<svg[^>]*>' "$svg" | head -1 | grep -o 'width="[0-9.]*' | head -1 | cut -d'"' -f2)"
w="${3:-$(awk -v a="${art_w:-1600}" 'BEGIN{v=int(a/2); if(v>1600)v=1600; if(v<800)v=800; print v}')}"

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
# Match heights too, in case the two engines round differently — and blur both by 1px before
# measuring. The failures this gate exists for (a substituted font, a leaked filter, a dropped
# fragment) are STRUCTURAL and survive a 1px blur intact; resampling noise from per-pixel grain
# does not. Without it, the pieces whose treatment is most committed are the ones that cry wolf.
$IM "$tmp/rsvg.png" -resize "${w}x!" -background white -flatten -blur 0x1 "$tmp/rsvg2.png"
$IM "$tmp/ink.png"  -resize "${w}x!" -background white -flatten -blur 0x1 "$tmp/ink2.png"

# -metric RMSE prints "<absolute> (<normalized>)"; the normalized value goes SCIENTIFIC
# (e.g. 9.98e-05) exactly when the render is near-perfect, so the exponent chars must be
# part of the match or a passing check would fail to parse.
out="$($IMCMP -metric RMSE "$tmp/ink2.png" "$tmp/rsvg2.png" null: 2>&1 || true)"
norm="$(printf '%s' "$out" | sed -n 's/.*(\([0-9.eE+-]*\)).*/\1/p')"
[ -z "$norm" ] && { echo "check failed to parse compare output: $out" >&2; exit 2; }

if awk -v n="$norm" 'BEGIN{ exit !((n + 0) <= 0.02) }'; then
  awk -v n="$norm" -v w="$w" 'BEGIN{ printf "PASS  svg==png  (RMSE %.6f at w=%d)\n", n + 0, w }'
  exit 0
fi

# Report what was measured, not a diagnosis. The check establishes that two engines disagree;
# it does not establish why, and asserting a cause sends you hunting for a filter that may not
# exist. The diff image is what settles it.
# -fuzz is what makes the diff readable: without it every pixel of a grain-heavy piece differs
# slightly under resampling and the whole canvas comes back marked (measured: 37% of pixels at
# fuzz 0, 0.2% at fuzz 10). At 10% only differences big enough to matter survive.
$IMCMP -metric RMSE -fuzz 10% -compose src "$tmp/ink2.png" "$tmp/rsvg2.png" "$diff_png" >/dev/null 2>&1 || true
awk -v n="$norm" -v w="$w" 'BEGIN{ printf "FAIL  the two renderers disagree  (RMSE %.6f at w=%d, threshold 0.02)\n", n + 0, w }'
cat >&2 <<MSG
  Usually a renderer-dependent filter or an un-vectorized font — fix per the filter-free rule.
  But a grain-heavy piece can diverge on downsampling noise alone, with nothing wrong in the file.
  Diff written to: $diff_png  (red = differs by more than 10%; grain alone marks almost nothing)
    · a marked element or block of type -> a real leak; that is the thing to fix
    · a near-empty diff                 -> the RMSE is resampling noise, not a fault.
                                           Re-check at full width before believing the FAIL:
                             check_render.sh "$svg" "${conf:-''}" ${art_w:-2400}
MSG
exit 1
