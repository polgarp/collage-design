#!/usr/bin/env python3
"""
cut.py — shape the edge of a photo for collage ("scissors").

Cuts a shaped boundary out of an image and writes an RGBA PNG with transparency
outside the cut. The edge style is the collage move: mechanical cuts read as
deliberate/institutional, torn as urgent/handmade, treated as aged/decayed.

Usage:
    cut.py --style STYLE [options] IN OUT
    cut.py --list

Styles (three families):
  A · mechanical   clean    crisp straight edge      (--angle DEG)
                   rounded  soft rounded corners     (--radius PX)
                   scallop  decorative arc border    (--period PX)
                   pinking  zig-zag pinking-shears    (--period PX)
  B · torn         torn     soft deckle paper tear   (--seed, --amplitude PX)
                   rough    jagged ripped/grunge     (--seed, --jitter PX)
  C · treated      burnt    scorched/charred edge    (--seed, --char PX)

Shared options:
  --sides SPEC   which edges get the treatment for torn/rough/burnt:
                 all (default) | any comma list of top,bottom,left,right
  --inset PX     pull the cut in from the image border (default: auto ~4%)
  --feather PX   soften the cut edge (default 1.5)
  --seed INT     seed for organic styles (default 0) — keep builds reproducible
  --from-alpha   operate on the input's EXISTING alpha silhouette (roughen a
                 knockout) instead of cutting the whole rectangle

Determinism: same input + same flags → same output. Record the exact command in
your build script so the fragment can be regenerated.

Invent a new edge — don't force a preset. The seven styles are worked examples of ONE
pattern: a function (w, h, params, rng) returning an L-mode mask (255 = keep). When the
philosophy wants an edge these don't cover, make your own and reuse the plumbing (loading,
feather, from-alpha, save) rather than rebuilding it:
  • drop-in file — write my_edge.py with `def mask(w, h, p, rng): ... return L_image`, then
        cut.py --style-file my_edge.py in.png out.png
  • or import — `from cut import load, compose` (+ helpers `_profile`, `_organic_mask`,
    `_roughen_alpha`, `_band`, `_perimeter`), build any mask, and `compose(img, mask).save(out)`.

The organic styles (torn/rough/burnt) displace a CLOSED contour inward along its own
normals, so a tear carries continuously through the corners instead of leaving them at
90 degrees. `--from-alpha` follows the subject's real silhouette the same way.
"""
import argparse, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

STYLES = {}          # name -> (family, builder, help)
def style(name, family, helptext):
    def reg(fn): STYLES[name] = (family, fn, helptext); return fn
    return reg

# ---- geometric mask builders: return an L-mode mask (255 = keep) ----

@style("clean", "mechanical", "crisp straight edge; --angle for a diagonal cut")
def m_clean(w, h, p, rng):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    i = p.inset
    d.rectangle([i, i, w - 1 - i, h - 1 - i], fill=255)
    if p.angle:
        m = m.rotate(p.angle, resample=Image.BILINEAR, expand=False, fillcolor=0)
    return m

@style("rounded", "mechanical", "soft rounded corners; --radius PX")
def m_rounded(w, h, p, rng):
    m = Image.new("L", (w, h), 0)
    r = p.radius if p.radius is not None else int(0.12 * min(w, h))
    i = p.inset
    ImageDraw.Draw(m).rounded_rectangle([i, i, w - 1 - i, h - 1 - i], radius=r, fill=255)
    return m

@style("scallop", "mechanical", "repeated convex arcs (vintage print border); --period PX")
def m_scallop(w, h, p, rng):
    per = p.period if p.period is not None else max(24, int(0.05 * min(w, h)))
    r = per / 2.0
    i = p.inset
    # circle centers ride the inner rect's perimeter; corners get a circle too, so
    # adjacent sides' scallops meet in a clean rounded-scallop corner.
    L, T, R, B = i + r, i + r, w - 1 - i - r, h - 1 - i - r
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rectangle([L, T, R, B], fill=255)
    def circ(cx, cy):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    xs = list(np.arange(L, R, per)) + [R]
    ys = list(np.arange(T, B, per)) + [B]
    for x in xs:
        circ(x, T); circ(x, B)
    for y in ys:
        circ(L, y); circ(R, y)
    return m

@style("pinking", "mechanical", "zig-zag pinking-shears edge; --period PX")
def m_pinking(w, h, p, rng):
    per = p.period if p.period is not None else max(20, int(0.04 * min(w, h)))
    amp = per * 0.5
    i = p.inset + amp
    pts = []
    def teeth(length, horizontal, fixed, sign, reverse=False):
        n = int((length - 2 * i) / per)
        seq = range(n + 1)
        for k in (reversed(seq) if reverse else seq):
            along = i + k * per
            out = amp if k % 2 == 0 else 0
            if horizontal:
                pts.append((along, fixed - sign * out))
            else:
                pts.append((fixed - sign * out, along))
    teeth(w, True, i, 1)                       # top L->R
    teeth(h, False, w - 1 - i, -1)             # right T->B
    teeth(w, True, h - 1 - i, -1, reverse=True)# bottom R->L
    teeth(h, False, i, 1, reverse=True)        # left B->T
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m

# ---- organic edge-displacement builders (respect --sides) ----

def _band(length, k, rng, periodic=False):
    """One octave of seeded noise, smoothed over k samples and normalised to [-1, 1].
    With periodic=True the smoothing wraps, so the octave joins itself end-to-end —
    required when the profile runs around a closed contour. Reuse when inventing an
    edge that needs correlated (non-comb) randomness."""
    n = rng.standard_normal(length)
    k = max(1, int(k))
    if k > 1:
        ker = np.ones(k) / k
        if periodic:
            pad = k
            n = np.convolve(np.concatenate([n[-pad:], n, n[:pad]]), ker,
                            mode="same")[pad:pad + length]
        else:
            n = np.convolve(n, ker, mode="same")
    return n / (np.abs(n).max() + 1e-6)

def _profile(length, amplitude, roughness, rng, periodic=False):
    """A 1-D inward-offset profile, summed from three octaves.

    A real tear carries energy at several scales at once: a long slow wander that
    decides where the edge goes, mid-frequency bites, and short fibre at the deckle.
    Every octave is SMOOTHED — sampling the fibre per-pixel leaves adjacent samples
    uncorrelated, which renders as a 1px comb that reads as fur rather than paper.
    Roughness shifts weight toward the finer octaves; it does not shorten the wander,
    so a soft deckle and a violent rip still travel over the same overall scale."""
    base_k = max(3, int(length * 0.06))          # overall wander, ~6% of the run
    prof  = 1.00 * _band(length, base_k, rng, periodic)
    prof += (0.25 + 0.55 * roughness) * _band(length, max(3, base_k // 4), rng, periodic)
    prof += (0.05 + 0.45 * roughness) * _band(length, max(2, base_k // 16), rng, periodic)
    prof /= (np.abs(prof).max() + 1e-6)
    return np.clip(amplitude * (0.5 + 0.5 * prof), 0, None)

def _perimeter(x0, y0, x1, y1):
    """Walk the inset rectangle's perimeter at ~1px, returning point coordinates, the
    INWARD unit normal at each point, and which side each point belongs to."""
    W, H = max(2, int(round(x1 - x0))), max(2, int(round(y1 - y0)))
    top    = (np.linspace(x0, x1, W), np.full(W, y0),  0.0,  1.0, "top")
    right  = (np.full(H, x1), np.linspace(y0, y1, H), -1.0,  0.0, "right")
    bottom = (np.linspace(x1, x0, W), np.full(W, y1),  0.0, -1.0, "bottom")
    left   = (np.full(H, x0), np.linspace(y1, y0, H),  1.0,  0.0, "left")
    xs, ys, nx, ny, sides = [], [], [], [], []
    for px, py, ux, uy, name in (top, right, bottom, left):
        xs.append(px); ys.append(py)
        nx.append(np.full(len(px), ux)); ny.append(np.full(len(px), uy))
        sides.append(np.full(len(px), name, dtype=object))
    return (np.concatenate(xs), np.concatenate(ys),
            np.concatenate(nx), np.concatenate(ny), np.concatenate(sides))

def _organic_mask(w, h, p, rng, amplitude, roughness):
    """Displace a CLOSED contour inward along its own normals.

    Displacing each of the four sides independently (the obvious approach) leaves the
    corners at a hard 90 degrees, which is the one thing torn paper never does — the
    fragment reads as a rectangle with texture rather than as something ripped. Running
    a single periodic profile around the whole perimeter and pushing each point along
    its inward normal lets the tear carry through the corners continuously.

    --sides still works: points on untreated sides get zero displacement, and the
    weight is smoothed so a treated side eases into an untreated one instead of
    stepping."""
    i = p.inset
    x0, y0, x1, y1 = i, i, w - 1 - i, h - 1 - i
    if x1 <= x0 or y1 <= y0:                       # inset swallowed the image
        return Image.new("L", (w, h), 255)
    px, py, nx, ny, side = _perimeter(x0, y0, x1, y1)
    n = len(px)

    prof = _profile(n, amplitude, roughness, rng, periodic=True)

    # zero the displacement on sides the user excluded, then smooth the on/off step so
    # the contour eases between a torn side and a clean one
    weight = np.array([1.0 if s in p.sides else 0.0 for s in side])
    if 0.0 in weight and 1.0 in weight:
        k = max(3, int(amplitude * 1.5))
        pad = k
        weight = np.convolve(np.concatenate([weight[-pad:], weight, weight[:pad]]),
                             np.ones(k) / k, mode="same")[pad:pad + n]

    d = prof * weight
    poly = list(zip(px + nx * d, py + ny * d))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    return m

@style("torn", "torn", "soft deckle paper tear; --seed, --amplitude PX")
def m_torn(w, h, p, rng):
    amp = p.amplitude if p.amplitude is not None else 0.03 * min(w, h)
    return _organic_mask(w, h, p, rng, amp, roughness=0.55)

@style("rough", "torn", "jagged ripped/grunge tear; --seed, --jitter PX")
def m_rough(w, h, p, rng):
    amp = p.jitter if p.jitter is not None else 0.05 * min(w, h)
    return _organic_mask(w, h, p, rng, amp, roughness=0.9)

@style("burnt", "treated", "scorched/charred edge; --seed, --char PX")
def m_burnt(w, h, p, rng):
    amp = p.char if p.char is not None else 0.045 * min(w, h)
    return _organic_mask(w, h, p, rng, amp * 1.2, roughness=0.75)

def _apply_burn(img, mask, p, rng):
    """Darken/brown a band just inside the burnt edge before it goes transparent.
    The band's depth is modulated by a smooth 2-D noise field, so the scorch eats
    further in at some points than others — a constant-width band reads as a printed
    frame, not as fire."""
    char = p.char if p.char is not None else 0.045 * min(img.size)
    m = np.asarray(mask, float) / 255.0
    band = np.asarray(mask.filter(ImageFilter.GaussianBlur(char * 0.6)), float) / 255.0
    # smooth noise in [0.45, 1.55]: where it is high the char band bites deeper
    nz = Image.fromarray((rng.random(m.shape) * 255).astype("uint8"), "L") \
              .filter(ImageFilter.GaussianBlur(max(2.0, char * 0.5)))
    nz = np.asarray(nz, float) / 255.0
    depth = 4.0 * (0.45 + 1.1 * (nz - nz.min()) / (np.ptp(nz) + 1e-6))  # np.ptp: ndarray.ptp() is gone in numpy 2
    scorch = np.clip((m - band) * -depth + m, 0, 1)  # 0 in the char band, 1 deep inside
    arr = np.asarray(img).astype(float)
    char_col = np.array([40, 22, 12, 255.0])
    for c in range(3):
        arr[..., c] = arr[..., c] * scorch + char_col[c] * (1 - scorch)
    return Image.fromarray(arr.clip(0, 255).astype("uint8"), "RGBA")

ORGANIC = {"torn", "rough", "burnt"}
_ROUGH = {"torn": 0.55, "rough": 0.9, "burnt": 0.75}
def _amp(p, w, h):
    if p.style == "rough": return p.jitter if p.jitter is not None else 0.05 * min(w, h)
    if p.style == "burnt": return (p.char if p.char is not None else 0.045 * min(w, h)) * 1.2
    return p.amplitude if p.amplitude is not None else 0.03 * min(w, h)

def _roughen_alpha(alpha_img, amp, roughness, rng):
    """Perturb an EXISTING silhouette's edge — follows its contour, not a rectangle.

    A soft ramp across the boundary is thresholded against a seeded noise field, so
    only the edge zone frays while the interior stays solid. The fray reaches about
    as far as the ramp is wide, which is why the blur radius is tied to amp.

    The noise field MUST be renormalised after blurring: blurring uniform noise
    collapses its spread toward the mean, so a raw blurred field sits near-constant at
    ~127 and the threshold below just reproduces the original edge — the silhouette
    comes back looking untouched. Rescaling restores the range that makes the contour
    actually wander. Kept inside [0.08, 0.92] so the extremes don't punch holes just
    inside the subject or strand specks outside it."""
    soft = np.asarray(alpha_img.filter(ImageFilter.GaussianBlur(max(1.0, amp * 0.6))), float)
    nblur = max(1.0, amp * (1.0 - roughness) * 0.5 + 1.0)
    nf = np.asarray(Image.fromarray((rng.random(soft.shape) * 255).astype("uint8"), "L")
                    .filter(ImageFilter.GaussianBlur(nblur)), float)
    nf = (nf - nf.min()) / (np.ptp(nf) + 1e-6)            # -> [0, 1]
    nf = (0.08 + 0.84 * nf) * 255.0                       # -> usable threshold band
    return Image.fromarray(np.where(soft > nf, 255, 0).astype("uint8"), "L")

# ---- reusable plumbing (import these when inventing a new edge) ----

def load(path):
    """Load an image as RGBA. Reuse when inventing a new edge."""
    return Image.open(path).convert("RGBA")

def compose(img, mask, feather=1.5, from_alpha=False):
    """Apply an L-mode mask (255 = keep) as the image's alpha; return a new RGBA image.
    Reuse when inventing an edge: write a mask, call compose(). With from_alpha the mask
    is intersected with the image's existing alpha (clip a knockout to a shape)."""
    if from_alpha:
        mask = Image.fromarray(np.minimum(
            np.asarray(img.split()[3]), np.asarray(mask)).astype("uint8"), "L")
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    out = img.copy(); out.putalpha(mask)
    return out

def _resolve_builder(args):
    """A style is just a function (w, h, params, rng) -> L mask. Presets live in STYLES;
    --style-file loads a user .py defining `mask(w, h, p, rng)`, so a new edge needs no
    edit to this tool."""
    if args.style_file:
        import importlib.util
        spec = importlib.util.spec_from_file_location("user_style", args.style_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.mask, "custom"
    return STYLES[args.style][1], args.style

def build(args):
    if args.list:
        w = max(len(n) for n in STYLES)
        for fam in ("mechanical", "torn", "treated"):
            print(f"\n{fam}:")
            for n, (f, _, h) in STYLES.items():
                if f == fam: print(f"  {n:<{w}}  {h}")
        return 0
    if not args.style_file and (not args.style or args.style not in STYLES):
        sys.exit(f"--style must be one of: {', '.join(STYLES)} (or --style-file FILE, or --list)")
    if not (args.input and args.output):
        sys.exit("need IN and OUT paths")

    img = load(args.input)
    w, h = img.size
    if args.inset is None:
        args.inset = int(0.04 * min(w, h))
    args.sides = ({"top", "bottom", "left", "right"} if args.sides == "all"
                  else set(s.strip() for s in args.sides.split(",")))
    rng = np.random.default_rng(args.seed)
    builder, name = _resolve_builder(args)

    if args.from_alpha and name in ORGANIC:
        # roughen the subject's real silhouette (contour-following, not a rectangle)
        mask = _roughen_alpha(img.split()[3], _amp(args, w, h), _ROUGH[name], rng)
        from_alpha = False
    else:
        mask = builder(w, h, args, rng)
        from_alpha = args.from_alpha
    if from_alpha:  # clip to an existing knockout's silhouette
        mask = Image.fromarray(np.minimum(
            np.asarray(img.split()[3]), np.asarray(mask)).astype("uint8"), "L")
    if args.feather:
        mask = mask.filter(ImageFilter.GaussianBlur(args.feather))
    if name == "burnt":
        img = _apply_burn(img, mask, args, rng)
    img.putalpha(mask)
    img.save(args.output)
    print(f"cut '{name}' -> {args.output}  ({w}x{h}, sides={sorted(args.sides)}, seed={args.seed})")
    return 0

def main():
    ap = argparse.ArgumentParser(description="Shape the edge of a photo for collage.")
    ap.add_argument("input", nargs="?"); ap.add_argument("output", nargs="?")
    ap.add_argument("--style")
    ap.add_argument("--style-file", dest="style_file", default=None,
                    help="a .py file defining mask(w,h,p,rng)->L mask; invent a new edge "
                         "without editing this tool")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sides", default="all")
    ap.add_argument("--inset", type=float, default=None)
    ap.add_argument("--feather", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--from-alpha", dest="from_alpha", action="store_true")
    ap.add_argument("--angle", type=float, default=0)      # clean
    ap.add_argument("--radius", type=int, default=None)    # rounded
    ap.add_argument("--period", type=int, default=None)    # scallop, pinking
    ap.add_argument("--amplitude", type=float, default=None)  # torn
    ap.add_argument("--jitter", type=float, default=None)     # rough
    ap.add_argument("--char", type=float, default=None)       # burnt
    sys.exit(build(ap.parse_args()))

if __name__ == "__main__":
    main()
