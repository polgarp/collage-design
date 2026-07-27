#!/usr/bin/env python3
"""
knockout.py — lift a subject off a flat/neutral background into an RGBA cutout.

Classical extraction (PIL/numpy only, no ML): estimate the background colour from
the image border, key pixels by colour distance, then keep only the foreground that
is NOT connected to the border (a flood-fill from the edge). Interior background-
coloured pockets stay part of the subject, which is usually what you want.

Works well when the subject sits on a flat, fairly even ground THAT THE SUBJECT
CONTRASTS WITH — a specimen on a plate, an object on white, a dark coat against a
studio sweep. Flatness alone is not the predictor: a pale dress on a pale sweep is
a perfectly flat ground and cannot be lifted at any tolerance, because the subject
sits at the same luminance as the fill. Watch the `kept %` this prints — it is the
tell, and this tool warns when it looks wrong.

It will NOT cleanly lift a subject from a busy/complex background: for those, either
use the photo as a torn *rectangle* (cut.py --style torn), or install rembg for ML
matting (see the skill's sourcing doctrine — this tool is deliberately light).

Usage:
    knockout.py [options] IN OUT.png
Options:
    --bg auto|R,G,B     background colour; auto = median of the border (default auto)
    --tolerance N       colour distance counted as background, 0-255 (default 32)
    --shave PCT         crop PCT% off each side BEFORE matting (default 0). Museum and
                        archive photography usually carries a mount border, and a border
                        defeats border-connected removal outright — the sheet survives
                        whole, and once treated its ground goes paper-coloured and the
                        failure is easy to miss. `--shave 4` is the usual dose.
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

def separation(arr, bg):
    """How far the frame's brightest-contrasting content sits from the ground colour.

    This — not ground flatness — is what predicts whether a knockout can work. A flat
    neutral sweep gives a clean flood fill; it does not give you a SUBJECT if the subject
    is the same value as the fill. p90 rather than max, so a stray dark speck or a caption
    doesn't stand in for a figure that isn't there."""
    dist = np.sqrt(((arr.astype(float) - bg) ** 2).sum(-1))
    return float(np.percentile(dist, 90))

def _bg_depth(arr, bg, tol):
    """How deep the background-coloured band runs in from each of the four edges, as a
    fraction of the image. A mount border shows up as a shallow band of near-equal depth on
    all four sides — the tell that the sheet, not the subject, is what sits on the ground."""
    dist = np.sqrt(((arr.astype(float) - bg) ** 2).sum(-1))
    bgl = dist <= tol
    h, w = bgl.shape
    out = []
    for line, n in ((bgl[:, w // 2], h), (bgl[::-1, w // 2], h),
                    (bgl[h // 2, :], w), (bgl[h // 2, ::-1], w)):
        out.append((int(np.argmax(~line)) if (~line).any() else n) / n)
    return out

def diagnose(arr, bg, tol, cov):
    """Say what was measured when the matte looks wrong. Cheaper than three failed attempts
    at successive tolerances, which is what these cost when they go unreported."""
    sep = separation(arr, bg)
    if sep < 2 * tol:
        print(f"  WARNING: contrast {int(sep)} vs tolerance {tol:g} — almost nothing in this "
              f"frame sits far from\n  the ground colour, so the subject is inside the tolerance "
              f"ball with it. No tolerance fixes\n  this: raise it and the figure dissolves, lower "
              f"it and the ground stays. Source a subject\n  that contrasts with its ground, or "
              f"use this photo as a torn rectangle instead.", file=sys.stderr)
    d = _bg_depth(arr, bg, tol)
    if all(0.005 < x < 0.10 for x in d) and max(d) - min(d) < 0.05:
        print(f"  NOTE: background-coloured band is only {100 * min(d):.0f}-{100 * max(d):.0f}% "
              f"deep on all four sides —\n  that is a mount border, and it seals the sheet off "
              f"from the image edge so border-connected\n  removal never reaches the real ground. "
              f"Try --shave {max(4, int(100 * max(d)) + 1)}.", file=sys.stderr)
    if cov > 95:
        print(f"  WARNING: kept {cov}% — almost nothing was removed.", file=sys.stderr)

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
    ap.add_argument("--shave", type=float, default=0,
                    help="crop PCT%% off each side before matting — gets past a mount border, "
                         "which otherwise defeats border-connected removal entirely")
    a = ap.parse_args()

    img = Image.open(a.input).convert("RGBA")
    if a.shave:
        w, h = img.size
        dx, dy = int(w * a.shave / 100), int(h * a.shave / 100)
        img = img.crop((dx, dy, w - dx, h - dy))
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
    print(f"knockout -> {a.output}  (bg~{bg.astype(int).tolist()}, tol={a.tolerance}, "
          f"kept {cov}%, contrast {int(separation(arr, bg))})")
    diagnose(arr, bg, a.tolerance, cov)

if __name__ == "__main__":
    main()
