#!/usr/bin/env python3
"""
knockout.py — lift a subject off a flat/neutral background into an RGBA cutout.

Classical extraction (PIL/numpy only, no ML): estimate the background colour from
the image border, key pixels by colour distance, then keep only the foreground that
is NOT connected to the border (a flood-fill from the edge). Interior background-
coloured pockets stay part of the subject, which is usually what you want.

Works well when the subject sits on a flat, fairly even ground — a specimen on a
plate, an object on white, a figure on studio grey. It will NOT cleanly lift a
subject from a busy/complex background: for those, either use the photo as a torn
*rectangle* (cut.py --style torn), or install rembg for ML matting (see the skill's
sourcing doctrine — this tool is deliberately light).

Usage:
    knockout.py [options] IN OUT.png
Options:
    --bg auto|R,G,B     background colour; auto = median of the border (default auto)
    --tolerance N       colour distance counted as background, 0-255 (default 32)
    --global            remove ALL background-coloured pixels, not just the ones
                        connected to the border — right for scattered line-art such
                        as a specimen plate; may hole a subject sharing the bg colour
    --erode PX          shrink the matte to kill background fringe (default 1)
    --feather PX        soften the matte edge (default 1.0)
    --keep-largest      drop stray specks; keep only the biggest foreground blob

Then treat the edge with:  cut.py --style rough --from-alpha OUT.png final.png

If you intend to fray the result, erode a little harder than you otherwise would
(--erode 2..3, --feather 0.5). Fraying moves the contour around, which exposes any
residual halo of background-coloured pixels the matte left behind — a fringe you
never notice on a clean knockout reads as pale flecks once the edge is torn.
"""
import argparse, sys
import numpy as np
from PIL import Image, ImageFilter

def sample_bg(arr):
    h, w, _ = arr.shape
    b = max(2, min(h, w) // 40)
    border = np.concatenate([
        arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
        arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3)])
    return np.median(border, axis=0)

def _reconstruct(marker, mask, chunk=8):
    """Morphological reconstruction: grow `marker` within `mask` (4-connectivity)
    until stable. Used instead of PIL's ImageDraw.floodfill, whose behaviour on
    thresholded mattes varies across Pillow versions; this is pure numpy and
    gives the same result everywhere."""
    marker = marker & mask
    while True:
        prev = marker
        for _ in range(chunk):
            d = marker.copy()
            d[1:, :] |= marker[:-1, :]; d[:-1, :] |= marker[1:, :]
            d[:, 1:] |= marker[:, :-1]; d[:, :-1] |= marker[:, 1:]
            marker = d & mask
        if np.array_equal(marker, prev):
            return marker

def matte(arr, bg, tol, glob=False):
    dist = np.sqrt(((arr.astype(float) - bg) ** 2).sum(-1))   # per-pixel colour distance
    bg_like = dist <= tol                                     # True = looks like background
    if glob:                                                  # remove ALL background-coloured pixels
        return np.where(bg_like, 0, 255).astype("uint8")
    # default: remove only background CONNECTED to the image border, so interior
    # background-coloured pockets stay part of the subject (no holes punched in it).
    seed = np.zeros_like(bg_like)
    seed[0, :] = seed[-1, :] = seed[:, 0] = seed[:, -1] = True
    bg_border = _reconstruct(seed & bg_like, bg_like)
    return np.where(bg_border, 0, 255).astype("uint8")

def keep_largest(alpha):
    """Keep only the biggest connected foreground blob; drop stray specks."""
    fg = alpha > 0
    remaining = fg.copy()
    best, best_n = None, 0
    while remaining.any():
        ys, xs = np.where(remaining)
        seed = np.zeros_like(fg); seed[ys[0], xs[0]] = True
        comp = _reconstruct(seed, remaining)
        n = int(comp.sum())
        if n > best_n:
            best_n, best = n, comp
        remaining &= ~comp
    return np.where(best, alpha, 0).astype("uint8") if best is not None else alpha

def main():
    ap = argparse.ArgumentParser(description="Lift a subject off a flat background.")
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--bg", default="auto")
    ap.add_argument("--tolerance", type=float, default=32)
    ap.add_argument("--global", dest="glob", action="store_true",
                    help="remove ALL background-coloured pixels, not just border-connected "
                         "(right for scattered line-art like specimen plates; may hole a subject "
                         "that shares the bg colour)")
    ap.add_argument("--erode", type=float, default=1)
    ap.add_argument("--feather", type=float, default=1.0)
    ap.add_argument("--keep-largest", dest="keep_largest", action="store_true")
    a = ap.parse_args()

    img = Image.open(a.input).convert("RGBA")
    arr = np.asarray(img)[..., :3]
    bg = sample_bg(arr) if a.bg == "auto" else np.array([float(x) for x in a.bg.split(",")])

    alpha = matte(arr, bg, a.tolerance, glob=a.glob)
    if a.keep_largest:
        alpha = keep_largest(alpha)
    am = Image.fromarray(alpha, "L")
    if a.erode:
        am = am.filter(ImageFilter.MinFilter(int(a.erode) * 2 + 1))
    if a.feather:
        am = am.filter(ImageFilter.GaussianBlur(a.feather))

    img.putalpha(am)
    img.save(a.output)
    cov = int((np.asarray(am) > 128).mean() * 100)
    print(f"knockout -> {a.output}  (bg~{bg.astype(int).tolist()}, tol={a.tolerance}, kept {cov}%)")

if __name__ == "__main__":
    main()
