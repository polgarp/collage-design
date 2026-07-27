#!/usr/bin/env bash
# Convert all live text in an SVG to paths so downloaded fonts render identically everywhere.
# --export-text-to-path is unreliable on inkscape 1.x; the object-to-path action is the fix.
# Usage: vectorize_text.sh <fontconfig-file> <in.svg> <out.svg>
set -euo pipefail

conf="${1:?usage: vectorize_text.sh <fontconfig-file> <in.svg> <out.svg>}"
in="${2:?in.svg}"
out="${3:?out.svg}"

# Fonts are FROZEN at this step: object-to-path bakes in whatever fontconfig resolved, and no
# later check can see a substitution — check_render.sh renders the same SVG twice, so a
# wrong-but-consistent face passes it happily. This is the only place the mistake is visible,
# so check resolution before converting.
while IFS= read -r fam; do
  [ -z "$fam" ] && continue
  case "$(printf '%s' "$fam" | tr 'A-Z' 'a-z')" in
    serif|sans-serif|"sans serif"|monospace|cursive|fantasy|system-ui) continue ;;
  esac
  got="$(FONTCONFIG_FILE="$conf" fc-match -f '%{family[0]}' "$fam" 2>/dev/null || true)"
  a="$(printf '%s' "$fam" | tr 'A-Z' 'a-z' | tr -d ' ')"
  b="$(printf '%s' "$got" | tr 'A-Z' 'a-z' | tr -d ' ')"
  if [ "$a" != "$b" ]; then
    echo "vectorize_text.sh: WARNING — '$fam' resolves to '$got'" >&2
    echo "  About to be baked into paths; no later check will catch it." >&2
    echo "  Fix fontconfig (pipeline-recipes.md §1) or accept this deliberately." >&2
  fi
done <<EOF
$(grep -o 'font-family="[^"]*"' "$in" | sed 's/font-family="//;s/"$//' | sort -u)
EOF

# Convert ONLY the text. `select-all:all;object-to-path` also *unlinks clones*, which expands
# every <use> back into a duplicated <image> — undoing svgkit's embed-once economy and roughly
# doubling the shipped file (measured: 296 KB -> 885 KB on a two-placement fixture). Past
# libxml2's attribute limits that doubling is what makes rsvg abort with `Premature end of data`.
# select-by-element needs Inkscape >= 1.2; older builds fall back below.
FONTCONFIG_FILE="$conf" inkscape "$in" \
  --actions="select-by-element:text;object-to-path" \
  --export-plain-svg --export-filename="$out" || true

if [ ! -s "$out" ] || [ "$(grep -c '<text' "$out" || true)" -gt 0 ]; then
  echo "vectorize_text.sh: text-scoped conversion did not take — retrying whole-document." >&2
  echo "  (Inkscape < 1.2 has no select-by-element. This unlinks <use> clones, so every" >&2
  echo "   embedded payload is duplicated and the file roughly doubles.)" >&2
  FONTCONFIG_FILE="$conf" inkscape "$in" \
    --actions="select-all:all;object-to-path" \
    --export-plain-svg --export-filename="$out"
fi

# Inkscape exits 0 even when it converted nothing — usually because the font could not be
# resolved, so there were no glyph outlines to make. Live <text> left in the shipped file is
# exactly what makes .svg and .png diverge, so fail loudly here rather than at render time.
left="$(grep -c '<text' "$out" || true)"
if [ "$left" -gt 0 ]; then
  echo "vectorize_text.sh: FAILED — $left <text> element(s) survived in $out" >&2
  echo "  The font almost certainly did not resolve. Check that it is registered:" >&2
  echo "    FONTCONFIG_FILE=$conf fc-list | grep -i '<your family>'" >&2
  echo "  If that lists nothing, re-run setup_fonts.sh and confirm the face is in the dir." >&2
  exit 1
fi

# Report the embed economy so a duplication is visible rather than inferred: <use> count should
# survive unchanged, and the file should not grow by more than the glyph outlines.
count() { grep -o "$1" "$2" | wc -l | tr -d ' '; }
printf 'vectorized text: %s -> %s\n  in:  %s bytes, %s <use>, %s <image>\n  out: %s bytes, %s <use>, %s <image>\n' \
  "$in" "$out" \
  "$(wc -c <"$in" | tr -d ' ')"  "$(count '<use' "$in")"  "$(count '<image' "$in")" \
  "$(wc -c <"$out" | tr -d ' ')" "$(count '<use' "$out")" "$(count '<image' "$out")" >&2
