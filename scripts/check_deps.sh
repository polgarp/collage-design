#!/usr/bin/env bash
# Preflight for collage-design: verify the tooling the pipeline needs and print the exact
# install line for anything missing (per OS). Run this before rendering on a fresh machine.
# Exit 0 if everything is present, 1 if something is missing.
set -uo pipefail

case "$(uname -s)" in
  Darwin) OS=mac ;;
  Linux)  OS=linux ;;
  *)      OS=other ;;
esac

miss=0
bin() {  # cmd  brew-pkg  apt-pkg
  if command -v "$1" >/dev/null 2>&1; then
    echo "  ✓ $1"
  else
    echo "  ✗ $1  (missing)"
    case "$OS" in
      mac)   echo "      → brew install $2" ;;
      linux) echo "      → sudo apt-get install $3   (or your distro's equivalent)" ;;
      *)     echo "      → install $1  (brew: $2 / apt: $3)" ;;
    esac
    miss=1
  fi
}

echo "collage-design dependency check ($OS):"
# ImageMagick 7 is `magick`; IM6 (Debian/Ubuntu LTS) is `convert` + `compare`. Either works.
if command -v magick >/dev/null 2>&1; then
  echo "  ✓ imagemagick (v7, magick)"
elif command -v convert >/dev/null 2>&1 && command -v compare >/dev/null 2>&1; then
  echo "  ✓ imagemagick (v6, convert/compare)"
else
  echo "  ✗ imagemagick  (missing)"
  case "$OS" in
    mac)   echo "      → brew install imagemagick" ;;
    linux) echo "      → sudo apt-get install imagemagick" ;;
    *)     echo "      → install imagemagick" ;;
  esac
  miss=1
fi
bin inkscape     inkscape    inkscape
bin rsvg-convert librsvg     librsvg2-bin
bin fc-cache     fontconfig  fontconfig

if command -v python3 >/dev/null 2>&1; then
  echo "  ✓ python3"
  pymiss=""
  # Pillow >= 8.2 for ImageDraw.rounded_rectangle; numpy >= 1.17 for default_rng.
  python3 - <<'PY' >/dev/null 2>&1 && echo "  ✓ python: Pillow" || { echo "  ✗ python: Pillow >= 8.2"; pymiss="pillow"; }
from PIL import Image, ImageDraw, ImageFilter
d = ImageDraw.Draw(Image.new("L", (40, 40)))
d.rounded_rectangle([0, 0, 39, 39], radius=6, fill=255)
Image.new("L", (40, 40)).filter(ImageFilter.GaussianBlur(2)).filter(ImageFilter.MinFilter(3))
PY
  python3 - <<'PY' >/dev/null 2>&1 && echo "  ✓ python: numpy" || { echo "  ✗ python: numpy >= 1.17"; pymiss="$pymiss numpy"; }
import numpy as np
np.ptp(np.convolve(np.random.default_rng(0).standard_normal(8), np.ones(3) / 3, mode="same"))
PY
  [ -n "$pymiss" ] && { echo "      → python3 -m pip install --upgrade $pymiss"; miss=1; }
else
  echo "  ✗ python3  (missing)"; miss=1
fi

echo
if [ "$miss" -eq 0 ]; then
  echo "All dependencies present — ready to render."
else
  echo "Install the missing tools above before rendering (Movement 4)."
  echo "Optional heavy extra: 'pip install rembg' only if a brief needs ML background matting."
fi
exit $miss
