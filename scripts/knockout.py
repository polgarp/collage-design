#!/usr/bin/env python3
"""
knockout.py — lift a subject off a flat/neutral background into an RGBA cutout.

Classical extraction (PIL/numpy only, no ML): estimate the background colour from
the image border, key pixels by colour distance, then keep only the foreground that
is NOT connected to the border (a flood-fill from the edge). Interior background-
coloured pockets stay part of the subject, which is usually what you want.

WHAT ACTUALLY DECIDES WHETHER THIS WORKS

Not "is the ground flat" — archive scans nearly always have a flat border, because
the flat thing is the SCAN FRAME or the mount, not a studio sweep. Keying against it
removes the frame and hands back the whole photograph as a rectangle. Measured on a
real 290-file pool, a border-statistics heuristic rated 111 sources liftable and the
ones tried came back as rectangles.

So this tool judges a matte by the SHAPE of what it produced (`assess`), not by the
statistics of what went in:

    kept %        foreground share of the frame — >75% means nothing was lifted, <2% that
                  the matte dissolved the subject
    solidity      area / bounding-box area — ~1.0 for a rectangle, 0.3-0.6 for a figure
                  with limbs and gaps. Both terms are area integrals, so unlike anything
                  perimeter-based it does not move when the matte edge is noisy
    span          that bounding box as a share of the frame. The one that catches a matte
                  which stripped a ragged margin and kept the photograph: plausible kept%,
                  plausible solidity, and a box covering the whole frame
    swing         how much kept% moves across a tolerance sweep. A real edge shows a
                  plateau, because there is a gap in the colour-distance histogram;
                  an arbitrary matte slides continuously

`--tolerance auto` finds the plateau instead of making you search for it by hand, and
`survey.py` calls the same `assess()` so its verdict cannot disagree with this tool.

The genuinely unfixable case is a subject at the same colour as its ground — a pale
dress on a pale sweep. No tolerance helps: raise it and the figure dissolves, lower it
and the ground stays. That case is rare in practice (1 file in 469 on the pools tested);
FRAMING, not contrast, is what usually defeats a knockout, and the answer to framing is
to measure the crop you will actually cut rather than the whole file (`survey.py --grid`).

Usage:
    knockout.py [options] IN OUT.png
Options:
    --bg auto|R,G,B     background colour; auto = median of the border (default auto)
    --tolerance N|auto  colour distance counted as background, 0-255 (default auto).
                        `auto` sweeps and picks the plateau; the chosen value is printed
                        so it can be pinned in a build script.
    --shave PCT         crop PCT% off each side BEFORE matting (default 0). Museum and
                        archive photography usually carries a mount border, and a border
                        defeats border-connected removal outright — the sheet survives
                        whole, and once treated its ground goes paper-coloured and the
                        failure is easy to miss. `--shave 4` is the usual dose; `auto`
                        detects the band and shaves past it.
    --global            remove ALL background-coloured pixels, not just the ones
                        connected to the border — right for scattered line-art such
                        as a specimen plate; may hole a subject sharing the bg colour
    --erode PX          shrink the matte to kill background fringe (default 1)
    --feather PX        soften the matte edge (default 1.0)
    --keep-largest      drop stray specks; keep only the biggest foreground blob
    --report            print the shape measurements and the verdict, then exit without
                        writing — the same judgement survey.py makes, for one file

Then treat the edge with:  cut.py --style rough --from-alpha OUT.png final.png

If you intend to fray the result, erode a little harder than you otherwise would
(--erode 2..3, --feather 0.5). Fraying moves the contour around, which exposes any
residual halo of background-coloured pixels the matte left behind — a fringe you
never notice on a clean knockout reads as pale flecks once the edge is torn.
"""
import argparse, sys
import numpy as np
from PIL import Image, ImageFilter

# Tolerances the sweep tries. Spread wider than linear at the top because the
# interesting plateau, when there is one, sits low; past ~80 everything dissolves.
SWEEP = (16, 24, 32, 44, 60, 80)

# Every assessment happens at this resolution, whoever asks. Big enough that thin limbs
# survive the downscale, small enough that six mattes per source stay affordable across a
# deep pull. See `assess` for why a single fixed size matters rather than being a knob.
ASSESS_EDGE = 320

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

def label(fg, chunk=8):
    """Label 4-connected components by propagating each pixel's index to its
    neighbours' maximum until stable. Returns int32, 0 = background.

    Pure numpy, so no scipy. Convergence is O(geodesic diameter), which is fine on a
    thumbnail and too slow at full resolution — `largest_blob` handles that by
    labelling small and reconstructing large."""
    h, w = fg.shape
    lab = np.where(fg, np.arange(1, h * w + 1, dtype=np.int32).reshape(h, w), 0)
    while True:
        prev = lab
        for _ in range(chunk):
            d = lab.copy()
            d[1:, :] = np.maximum(d[1:, :], lab[:-1, :])
            d[:-1, :] = np.maximum(d[:-1, :], lab[1:, :])
            d[:, 1:] = np.maximum(d[:, 1:], lab[:, :-1])
            d[:, :-1] = np.maximum(d[:, :-1], lab[:, 1:])
            lab = np.where(fg, d, 0)
        if np.array_equal(lab, prev):
            return lab

def largest_blob(fg, small=384):
    """Boolean mask of the biggest 4-connected component.

    Labels a downscaled copy to find WHICH blob is biggest — cheap — then grows that
    blob back through the full-resolution mask with one reconstruction. Labelling at
    full resolution would need thousands of propagation steps; this needs one flood."""
    if not fg.any():
        return fg
    h, w = fg.shape
    if max(h, w) <= small:
        lab = label(fg)
        ids, counts = np.unique(lab[lab > 0], return_counts=True)
        return lab == ids[int(np.argmax(counts))] if len(ids) else fg

    sc = small / max(h, w)
    sh, sw = max(1, int(h * sc)), max(1, int(w * sc))
    tiny = np.asarray(Image.fromarray(fg.astype("uint8") * 255).resize((sw, sh),
                                                                      Image.NEAREST)) > 127
    if not tiny.any():                                   # thin subject vanished when scaled
        return fg
    lab = label(tiny)
    ids, counts = np.unique(lab[lab > 0], return_counts=True)
    seed_small = (lab == ids[int(np.argmax(counts))])
    seed = np.asarray(Image.fromarray(seed_small.astype("uint8") * 255).resize((w, h),
                                                                  Image.NEAREST)) > 127
    seed &= fg
    if not seed.any():
        return fg
    return _reconstruct(seed, fg)

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
    return np.where(largest_blob(alpha > 0), alpha, 0).astype("uint8")

def separation(arr, bg, min_area=0.005):
    """How far the frame's contrasting content sits from the ground colour: the distance
    exceeded by at least `min_area` of the pixels (default 0.5%).

    Phrased as an AREA threshold rather than a fixed percentile for a reason. This used to
    take the p90, which silently required the subject to fill more than a tenth of the
    frame — so a figure occupying 7% measured as zero contrast and was rejected as "subject
    at ground value" with a textbook-clean silhouette sitting in it. Small subjects make
    good collage fragments, and that phrasing threw them all away.

    The p90 was chosen so a stray dark speck or a caption could not stand in for a figure
    that isn't there. The area floor keeps that property — 0.5% of the frame is far more
    than a speck — without imposing a minimum subject size.

    Necessary but nowhere near sufficient: on real archive pools this is almost never the
    binding constraint (median 257 against a floor of 40). Use `assess`, not this."""
    dist = np.sqrt(((arr.astype(float) - bg) ** 2).sum(-1))
    return float(np.percentile(dist, 100 * (1 - min_area)))

# ---- shape of the matte: what actually says whether a subject was lifted ----

def shape_metrics(alpha, thresh=128):
    """Measure the matte as a shape.

    `solidity` — area / bounding-box area — is the discriminator the old border-statistics
    heuristic lacked, and it is what catches the dominant failure: a knockout that merely
    trimmed a scan frame hands back a near-solid full-bleed block, solidity ~0.9, while a
    lifted figure with limbs and gaps runs 0.3-0.6. Both terms are area integrals, so
    unlike anything perimeter-based it does not move when the matte edge is noisy.

    `span` — that bounding box as a fraction of the frame — is the other half, and catches
    the case solidity misses: a matte that strips a ragged margin off a photograph and keeps
    the rest scores a plausible kept% and a plausible solidity while lifting nothing.

    (Two measures were tried here and removed. Edge contact — how much of the frame edge the
    foreground touches — cannot work, because border-connected removal always strips the
    outer ring, so it is ~0 by construction whatever was lifted. Isoperimetric complexity
    P^2/(4*pi*A) is dominated by matte noise rather than by silhouette shape.)"""
    fg = alpha > thresh
    h, w = fg.shape
    n = int(fg.sum())
    if n == 0:
        return dict(kept=0.0, solidity=0.0, span=0.0)

    big = largest_blob(fg)
    area = int(big.sum())
    ys, xs = np.where(big)
    bh, bw = int(ys.max() - ys.min() + 1), int(xs.max() - xs.min() + 1)
    return dict(kept=100.0 * n / (h * w),
                solidity=float(area / (bh * bw)),
                span=float((bh * bw) / (h * w)))

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

def mount_border(arr, bg, tol=32):
    """Recommended --shave percentage if a mount border is present, else 0."""
    d = _bg_depth(arr, bg, tol)
    if all(0.005 < x < 0.10 for x in d) and max(d) - min(d) < 0.05:
        return max(4, int(100 * max(d)) + 1)
    return 0

def sweep(arr, bg, tols=SWEEP, glob=False):
    """kept% at each tolerance. Monotonically non-increasing: more tolerance removes more."""
    return [(t, float((matte(arr, bg, t, glob) > 128).mean() * 100)) for t in tols]

def auto_tolerance(arr, bg, tols=SWEEP, glob=False):
    """Pick the tolerance at the flattest step of the kept% curve, and report the swing.

    A real subject/ground boundary puts a GAP in the colour-distance histogram, so kept%
    plateaus across it — the matte is the same over a range of tolerances because there is
    nothing in between to reclassify. No gap means no edge, and kept% slides continuously;
    that is what `swing` reports, and it is the honest confidence signal here."""
    curve = sweep(arr, bg, tols, glob)
    keeps = [k for _, k in curve]
    deltas = [abs(keeps[i + 1] - keeps[i]) for i in range(len(keeps) - 1)]
    i = int(np.argmin(deltas))
    return curve[i + 1][0], float(max(deltas)), curve      # prefer the higher tol of the flat pair

def assess(arr, tols=SWEEP, glob=False, auto_shave=True, edge=ASSESS_EDGE):
    """Judge whether a subject can actually be lifted out of this frame.

    Runs the real matte rather than predicting from input statistics, which is the whole
    point: a predictor that is not the operation will disagree with it, and this one used
    to — rating scan frames liftable because their borders are uniform.

    NORMALIZES RESOLUTION FIRST, and that is load-bearing rather than an optimisation.
    Matte statistics move with resolution — grain and JPEG noise near the tolerance boundary
    reclassify at full size — so assessing a 5000 px plate and a 320 px thumbnail of it
    returns different verdicts for the same picture. Callers that each picked their own size
    disagreed with each other, which is the exact failure this whole function exists to stop.
    One size, decided here.

    Returns the measurements, the chosen tolerance and a verdict string."""
    if max(arr.shape[:2]) > edge:
        im = Image.fromarray(arr.astype("uint8"))
        im.thumbnail((edge, edge), Image.LANCZOS)
        arr = np.asarray(im).astype(float)

    bg = sample_bg(arr)
    sep = separation(arr, bg)
    shave = mount_border(arr, bg) if auto_shave else 0
    if shave:
        h, w = arr.shape[:2]
        dy, dx = int(h * shave / 100), int(w * shave / 100)
        arr = arr[dy:h - dy, dx:w - dx]
        bg = sample_bg(arr)

    tol, swing, curve = auto_tolerance(arr, bg, tols, glob)
    m = shape_metrics(matte(arr, bg, tol, glob))
    m.update(bg=bg.astype(int).tolist(), tol=tol, sep=sep, swing=swing,
             shave=shave, curve=curve)

    # Ordered so the most informative failure wins. Contrast first: it is the one genuinely
    # unfixable case. Then the shape tests, which is where the old heuristic was blind.
    #
    # SPAN is the load-bearing one, and it is the least obvious. The common failure is not a
    # matte that keeps everything — it is one that strips a ragged margin off a photograph
    # and keeps the rest. That scores a perfectly reasonable kept% (~55%) and a perfectly
    # reasonable solidity (~0.5, because the removed chunks are irregular), and it is still
    # a photograph rather than a subject. What gives it away is that the surviving region's
    # bounding box is nearly the whole frame: nothing was LIFTED OUT of anything.
    #
    # This also encodes what the skill actually wants from a knockout. A cutout earns its
    # place by breaking its bounding box; a subject whose box is most of the frame won't do
    # that however cleanly it mattes, so calling it liftable would be true and useless.
    if sep < 40:
        m["verdict"] = "NO — subject at ground value"
    elif m["kept"] < 2:
        m["verdict"] = "NO — matte dissolves the subject"
    elif m["kept"] > 75:
        m["verdict"] = "no — whole frame (trimmed a scan border, lifted nothing)"
    elif m["span"] > 0.72:
        m["verdict"] = "no — kept region spans the frame; a shaped rectangle, not a silhouette"
    elif m["solidity"] > 0.85:
        m["verdict"] = "no — silhouette is near-rectangular"
    elif m["kept"] > 45:
        m["verdict"] = "marginal — keeps too much of the frame to read as a cutout"
    elif m["swing"] > 35:
        m["verdict"] = "marginal — matte slides with tolerance (no real edge)"
    else:
        m["verdict"] = "liftable"
    return m

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
    s = mount_border(arr, bg, tol)
    if s:
        print(f"  NOTE: a shallow background band of even depth runs round all four sides — "
              f"that is a\n  mount border, and it seals the sheet off from the image edge so "
              f"border-connected removal\n  never reaches the real ground. Try --shave {s}.",
              file=sys.stderr)
    if cov > 95:
        print(f"  WARNING: kept {cov}% — almost nothing was removed.", file=sys.stderr)

def report(arr, glob=False):
    m = assess(arr, glob=glob)
    print(f"  verdict     {m['verdict']}")
    print(f"  tolerance   {m['tol']:g} (auto)   swing {m['swing']:.0f}%"
          + (f"   shave {m['shave']}%" if m["shave"] else ""))
    print(f"  kept        {m['kept']:>6.0f}%  (>75% means nothing was lifted)")
    print(f"  solidity    {m['solidity']:>6.2f}   (~1.0 is a rectangle; a figure runs 0.3-0.6)")
    print(f"  span        {m['span']:>6.0%}   (bounding box as a share of the frame; >72% "
          f"is a rectangle)")
    print(f"  contrast    {m['sep']:>6.0f}   (<40 is unliftable at any tolerance)")
    print("  sweep       " + "  ".join(f"{t:g}:{k:.0f}%" for t, k in m["curve"]))
    return m

def main():
    ap = argparse.ArgumentParser(description="Lift a subject off a flat background.")
    ap.add_argument("input"); ap.add_argument("output", nargs="?")
    ap.add_argument("--bg", default="auto")
    ap.add_argument("--tolerance", default="auto",
                    help="colour distance counted as background, or 'auto' to find the "
                         "plateau of the kept%% curve (default auto)")
    ap.add_argument("--global", dest="glob", action="store_true",
                    help="remove ALL background-coloured pixels, not just border-connected "
                         "(right for scattered line-art like specimen plates; may hole a subject "
                         "that shares the bg colour)")
    ap.add_argument("--erode", type=float, default=1)
    ap.add_argument("--feather", type=float, default=1.0)
    ap.add_argument("--keep-largest", dest="keep_largest", action="store_true")
    ap.add_argument("--shave", default="0",
                    help="crop PCT%% off each side before matting — gets past a mount border, "
                         "which otherwise defeats border-connected removal entirely. "
                         "'auto' detects the band.")
    ap.add_argument("--report", action="store_true",
                    help="measure and judge this frame, print the numbers, write nothing")
    a = ap.parse_args()

    img = Image.open(a.input).convert("RGBA")

    if a.report:
        report(np.asarray(img)[..., :3], glob=a.glob)
        return

    if not a.output:
        ap.error("an output path is required unless --report is given")

    arr_full = np.asarray(img)[..., :3]
    shave = (mount_border(arr_full, sample_bg(arr_full)) if a.shave == "auto"
             else float(a.shave))
    if shave:
        w, h = img.size
        dx, dy = int(w * shave / 100), int(h * shave / 100)
        img = img.crop((dx, dy, w - dx, h - dy))
    arr = np.asarray(img)[..., :3]
    bg = sample_bg(arr) if a.bg == "auto" else np.array([float(x) for x in a.bg.split(",")])

    if a.tolerance == "auto":
        tol, swing, _ = auto_tolerance(arr, bg, glob=a.glob)
        print(f"  auto tolerance {tol:g} (swing {swing:.0f}% across the sweep)", file=sys.stderr)
    else:
        tol, swing = float(a.tolerance), None

    alpha = matte(arr, bg, tol, glob=a.glob)
    if a.keep_largest:
        alpha = keep_largest(alpha)
    am = Image.fromarray(alpha, "L")
    if a.erode:
        am = am.filter(ImageFilter.MinFilter(int(a.erode) * 2 + 1))
    if a.feather:
        am = am.filter(ImageFilter.GaussianBlur(a.feather))

    img.putalpha(am)
    img.save(a.output)

    sm = shape_metrics(np.asarray(am))
    cov = int(sm["kept"])
    print(f"knockout -> {a.output}  (bg~{bg.astype(int).tolist()}, tol={tol:g}"
          + (f", shave {shave:g}%" if shave else "")
          + f", kept {cov}%, solidity {sm['solidity']:.2f}, span {sm['span']:.0%})")
    if sm["solidity"] > 0.85 and sm["span"] > 0.8:
        print(f"  WARNING: solidity {sm['solidity']:.2f} across {sm['span']:.0%} of the frame — "
              f"this is a rectangle,\n  not a cutout. The matte almost certainly removed a scan "
              f"border and kept the whole\n  photograph. Run `--report` on the source, or measure "
              f"the crop you actually want with\n  `survey.py --grid`.", file=sys.stderr)
    diagnose(arr, bg, tol, cov)

if __name__ == "__main__":
    main()
