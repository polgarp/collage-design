#!/usr/bin/env bash
# Register a directory of downloaded fonts with fontconfig so rsvg/inkscape actually use them.
# Usage: setup_fonts.sh <fonts-dir>
# Prints the FONTCONFIG_FILE=... line to pass INLINE on every render/vectorize command
# (shell state does not persist between tool calls, so `export` won't survive).
set -euo pipefail

fonts_dir="${1:?usage: setup_fonts.sh <fonts-dir>}"
# Create it if it isn't there: a piece set entirely in SYSTEM faces still needs the generated
# conf, because a stock fontconfig can resolve an installed family to something else entirely.
# "I downloaded no fonts, run this anyway" is the normal path, not an error.
mkdir -p "$fonts_dir"
fonts_dir="$(cd "$fonts_dir" && pwd)"          # absolute
base="$(dirname "$fonts_dir")/fontconfig"
cache="$base/cache"
conf="$base/fonts.conf"
mkdir -p "$cache"

# NOTE: FONTCONFIG_FILE *replaces* the system configuration, it does not extend it.
# A conf listing only the download dir therefore hides every installed font — text set
# in a system face then has no glyphs, so object-to-path silently leaves it as live
# <text> and the cross-renderer check fails on font fallback. Re-declare the standard
# directories so a piece can mix downloaded and installed faces.
cat > "$conf" <<XML
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>$fonts_dir</dir>

  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>/System/Library/Fonts</dir>
  <dir>/System/Library/Fonts/Supplemental</dir>
  <dir>/Library/Fonts</dir>
  <dir>~/Library/Fonts</dir>
  <dir>/usr/share/fonts</dir>
  <dir>/usr/local/share/fonts</dir>
  <dir>~/.fonts</dir>
  <dir>~/.local/share/fonts</dir>

  <cachedir>$cache</cachedir>
</fontconfig>
XML

FONTCONFIG_FILE="$conf" fc-cache -f "$fonts_dir" >/dev/null 2>&1 || true
echo "Registered fonts in $fonts_dir:" >&2
FONTCONFIG_FILE="$conf" fc-list | sed 's/^/  /' >&2
echo "FONTCONFIG_FILE=$conf"
