# Pipeline Recipes

Exact, reusable commands for the collage pipeline. Every run needs most of these — use them
verbatim instead of re-deriving them, and reach for the bundled `scripts/` helpers first (they wrap
the fiddly, error-prone steps). Read this when you reach Movement 4 (Compose).

## Table of contents
1. Font setup (fontconfig)
2. Text → paths (portability)
3. Render + cross-renderer check (svg == png)
4. Asset validation (avoid 404-HTML-as-image)
5. Surveying the pool, and the art recipes (duotone/tritone, edges, knockouts, grain)
6. SVG assembly gotchas (filters, shadows, embedding, clipping)

---

## 1. Font setup (fontconfig)

**Never assume a face resolves — verify it, installed ones included.** `rsvg`/`inkscape` resolve
fonts through fontconfig and substitute silently when it fails, and a stock system config can be
wrong even about faces that are definitely installed — matching an entire family to an unrelated
fallback, so a slab serif quietly becomes something else.

```bash
scripts/setup_fonts.sh ./collage-fonts     # → prints FONTCONFIG_FILE=/abs/path/fonts.conf
FONTCONFIG_FILE=<conf> fc-match -f '%{family[0]}\n' '<your family>'   # must echo it back
```

Use `fc-match`, not `fc-list`: listing proves the file is on disk, which is not the same as
fontconfig choosing it. If a family comes back as something else, write a conf naming the
directories that hold it — **system font directories included** — and pass that.

Pass `FONTCONFIG_FILE=` **inline on every render/vectorize command** — shell state does not persist
between tool calls, so `export` won't survive. A generated conf keeps the system directories
alongside your download dir; hand-write one and you must do the same, or `FONTCONFIG_FILE`
replaces the system config and every installed font disappears.

---

## 2. Text → paths (portability)

**Vectorize all text before shipping — system faces included — using the helper:**

```bash
scripts/vectorize_text.sh <conf> in.svg out.svg
```

It wraps the one incantation that works (`--export-text-to-path` alone is unreliable on inkscape
1.x), fails loudly if any `<text>` survived, and warns when a family resolved to a different face.
**Do not inline the inkscape call in a build script** — that skips both checks, and this is the
last point at which a substitution is visible: object-to-path bakes the wrong face into outlines
and nothing downstream can tell.

It also converts **only the text**, and that matters for size. Inkscape's object-to-path unlinks
clones, so running it over the whole document expands every `<use>` back into a duplicated
`<image>` — undoing `svgkit`'s embed-once economy and roughly doubling the shipped file (measured:
296 KB → 885 KB on a two-placement fixture; on a real piece, 7 MB → 14 MB, past rsvg's XML limit).
The helper scopes the conversion to `<text>` elements and prints the `<use>`/`<image>` counts
before and after, so a doubling is visible rather than inferred. It needs Inkscape ≥ 1.2; on older
builds it falls back to whole-document conversion and says so.

---

## 3. Render + cross-renderer check (svg == png)

Ship the PNG from **inkscape** (most faithful filter/font flattening), then prove the `.svg` and
`.png` are the same picture by rendering the SVG in a second engine and diffing.

```bash
# final render
FONTCONFIG_FILE=<conf> inkscape collage.svg --export-type=png \
  --export-filename=collage.png -w 2400

# portability check — arg 2 is the FONTCONFIG FILE, not the png. The .png is never an input:
# the check renders the SVG twice, in two engines, and diffs those.
scripts/check_render.sh collage.svg
scripts/check_render.sh collage.svg "$CONF"           # if the piece uses downloaded fonts
scripts/check_render.sh collage.svg "$CONF" 3600      # re-check at full width (see below)
```
`check_render.sh` renders the SVG in both inkscape and rsvg, compares them, and prints PASS/FAIL
+ normalized RMSE (threshold 0.02). PASS means the shipped `.png` — which is the inkscape render —
is the same picture the `.svg` produces in any viewer.

**A FAIL says the engines disagree; it does not say why.** Read the diff image it writes beside
the SVG before you go hunting. The two things it can be:

- **A real leak** — a renderer-dependent filter or an un-vectorized font. The diff marks the
  offending element and little else. Fix per the filter-free rule; don't ship.
- **Resampling noise.** The check compares downscaled renders, and two engines' *downsamplers*
  disagree about per-pixel grain, so a heavily-treated piece can fail on noise that is not in the
  file. The gate already defends against this — it compares at half the artwork's width and blurs
  both renders 1px first, which structural faults survive and noise does not — but a very grainy
  piece can still tip over. The tells: a near-empty diff image, and a FAIL that disappears when
  you re-run at full width (third argument). Measured on one 3600px piece: 0.0282 at w=800,
  0.00075 at w=2400, with nothing wrong in the file.

**What PASS does not mean.** This gate compares one SVG against itself across two engines, so it
verifies `svg == png`, never `svg == intended`. A font substituted before vectorizing is baked
into both renders identically and passes. §2 is the only place that is caught.

---

## 4. Asset validation (avoid 404-HTML-as-image)

WebFetch sometimes reports **guessed/stale image URLs** (invented `-hires`/`-800` variants) that
404 to an HTML error page of nonzero size. Always confirm a download is a real image before using
it:
```bash
identify sources/foo.jpg   # errors if it's HTML/garbage, not an image
file sources/foo.jpg       # should say JPEG/PNG, not "HTML document"
```
If it fails, re-fetch the source page and read the true `src` — **unless the URL came from an API
response rather than a guess, in which case just retry the same URL once first.** Sustained
fetching gets throttled, and a throttle response is also an HTML page of nonzero size, so it looks
exactly like the stale-URL failure and sends you looking for a URL problem that isn't there. A
plain re-fetch succeeds. `sleep 1` between downloads in a bulk loop avoids it altogether.

---

## 5. ImageMagick art recipes

Do all raster effects here (Stage A) so the SVG stays filter-free.

**Look at the pool before you cut it up — `scripts/survey.py`.** It builds a labelled contact
sheet and measures each source, which is faster and more reliable than opening twenty files:
```bash
scripts/survey.py sources/* --sheet contact.png       # sheet + per-source table
scripts/survey.py sources/* --find-patch 900 900      # best flat-colour crops, ready to paste
```
The table answers two questions the eye is bad at: `ground` is border variance (is there one flat
ground?) and `contrast` is subject/ground separation (is there a subject to lift?) — together they
predict whether `knockout.py` will work before you spend three attempts finding out.

`--find-patch` is the same idea pushed further, and it generalises. **A philosophy dimension
written precisely enough can be turned into a selector.** "Colour as ingredient, never colour as
scene" means no structure; structure is edges; edges are variance — so ranking crops by
`2.0*saturation − 2.4*luminance_std − 1.6*chroma_std` finds fields of pigment and rejects anything
with a subject in it. The variance penalty is the load-bearing term: a scorer that rewards only
saturation and hue-uniformity picks whole flowers, because a flower is both. Where a dimension can
be scored, the machine picks better crops than you do, and it looks at the whole source at once.

**`-crop` takes PIXEL offsets even when the size is a percentage.** This is silent and it returns
the top-left corner of the plate every time, which is easy to mistake for a bad source:
```bash
magick in.jpg -crop 40%x30%+0+0   +repage out.png    # 40%x30% OF THE IMAGE, but offset 0,0 px
magick in.jpg -crop 40%x30%+1200+800 +repage out.png # offsets are PIXELS, not percent
```
Cutting a region out of a large plate is a constant collage operation — compute the offsets in
pixels yourself, and always `+repage` or the crop's origin follows it into everything downstream.

**Normalize each fragment BEFORE the shared treatment.** Sources arrive from different archives at
wildly different exposures, and one fixed curve applied to all of them will blow the light scans to
blank paper while the dark ones stay mud:
```bash
magick in.jpg -colorspace Gray -level 3%,97% norm.png    # then cut, then treat
```
This is Stage-A prep, **not** treatment: the cohesion rule below governs the *treatment*, and
normalizing does not violate it. Unifying sources is not the same as pretending they started equal.

**Unify (colour/tone) — use `scripts/treat.py`** (the reconciling treatment; PIL/numpy). Apply the
SAME style + seed to EVERY fragment or they won't read as one object:
```bash
scripts/treat.py --list          # the full menu + per-style knobs
scripts/treat.py --style duotone --dark '#0b2534' --light '#e8e2d0' in.png out.png
scripts/treat.py --style tritone --dark '#0a1014' --mid '#4a6a72' --light '#e8e2d0' in.png out.png
```
Invent a treatment — don't force a preset: `treat.py --style-file my_treat.py in.png out.png`
(file defines `treat(rgb,p,rng)->rgb`), or `from treat import load, save_rgb, lum`. ImageMagick
stays available for treatments treat.py doesn't cover (e.g. halftone).

**Edge cutting — use `scripts/cut.py`** (the "scissors"). All edge styles are one tool:
`clean`, `rounded`, `scallop`, `pinking` (mechanical); `torn`, `rough` (hand-tear); `burnt`
(treated). It writes an RGBA PNG, is deterministic via `--seed`, treats one or more sides
(`--sides` — a strip torn on a single edge is a classic collage move), and can roughen an existing
knockout's silhouette with `--from-alpha`. Record the exact command in your build script.
```bash
scripts/cut.py --list                                  # show the menu + per-style knobs
scripts/cut.py --style torn    --seed 7    in.jpg out.png
scripts/cut.py --style rounded --radius 40 in.jpg out.png
scripts/cut.py --style scallop --period 60 in.jpg out.png
scripts/cut.py --style torn    --sides bottom in.jpg out.png    # tear one edge only
scripts/cut.py --style rough   --from-alpha jelly.png out.png   # rough an existing cutout
```
**Invent a new edge — don't force a preset.** The seven styles are worked examples of one pattern:
a function `(w, h, params, rng) -> L mask` (255 = keep). When the philosophy wants an edge they
don't cover, make your own and reuse the plumbing instead of rebuilding it. A whole custom edge,
start to finish — the cabinet-card oval a Victorian studio actually mounted its portraits in:

```python
# my_edge.py — a vignette that fades into the mount instead of ending at a border
import numpy as np
from PIL import Image

def mask(w, h, p, rng):                      # p is cut.py's arg namespace
    fade = p.params.get("fade", 0.30)        # --param fade=0.45  (custom, not a built-in flag)
    fill = p.params.get("fill", 0.98)        # --param fill=0.90
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    r = np.sqrt(((xx - (w - 1) / 2) / (w * fill / 2)) ** 2 +
                ((yy - (h - 1) / 2) / (h * fill / 2)) ** 2)     # 1.0 at the ellipse edge
    t = np.clip((r - (1 - fade)) / max(fade, 1e-6), 0, 1)
    a = 0.5 * (1 + np.cos(np.pi * t))        # raised cosine: a linear ramp shows a seam
    a[r <= 1 - fade] = 1.0
    a[r >= 1] = 0.0
    return Image.fromarray((a * 255).astype("uint8"), "L")
```
```bash
scripts/cut.py --style-file my_edge.py --param fade=0.45 --param fill=0.9 in.jpg out.png
# or import the plumbing:  from cut import load, compose (+ _profile/_organic_mask/_roughen_alpha)
```
**`--param KEY=VALUE` is how a custom style takes its own parameters** (repeatable; numeric-looking
values arrive as floats). Without it you end up repurposing `--radius` as one thing and `--period`
as another, which works and is undiscoverable. `treat.py --style-file` takes `--param` identically,
where the function is `treat(rgb, p, rng) -> rgb`.

Same spirit for the ImageMagick treatments below — they are starting points to extend, not a fixed
set. Reuse the infrastructure; invent the aesthetics.

**The sticker cut** — a die-cut keyline of backing paper following the silhouette. It is a
post-process on the alpha rather than a mask function, so it is a flag, and it runs **after** the
treatment: varnish the keyline along with the image and it stops reading as the paper the shape
was cut from.
```bash
scripts/cut.py --style rough --from-alpha --seed 4 cutout.png frayed.png
scripts/treat.py --style-file varnish.py frayed.png treated.png
scripts/cut.py --sticker 16 --sticker-color '#f4efe2' treated.png sticker.png   # no --style
```

**Silhouette knockout — use `scripts/knockout.py`** (lift a subject off a flat/neutral ground;
PIL/numpy only, no ML):
```bash
knockout.py --tolerance 40 in.jpg cutout.png     # remove border-connected bg, keep interior holes
knockout.py --global in.jpg cutout.png           # remove ALL bg-coloured pixels (scattered line-art)
knockout.py --bg 255,255,255 --keep-largest in.jpg cutout.png   # explicit bg + drop stray specks
```
Handles flat/neutral backgrounds **the subject contrasts with**. A subject on a busy background
can't be lifted cleanly here — use that photo as a torn *rectangle* instead, or install `rembg` for
ML matting (opt-in; see the sourcing doctrine). Then fray the real silhouette:
`cut.py --style rough --from-alpha cutout.png out.png`.

**Read what it prints.** `kept %` is the subject's share of the frame, and `contrast` is how far
the frame's content sits from the ground colour — the tool warns on both, and the two warnings
mean opposite things:

- *contrast below ~2× tolerance* — the subject is the same value as its ground and is inside the
  tolerance ball with it. **No tolerance fixes this**: raise it and the figure dissolves (one real
  case walked 19% → 16% → 6% kept as tolerance went 26 → 44), lower it and the ground stays. Use
  the photo as a rectangle, or source a subject that contrasts.
- *a shallow, even background band on all four sides* — a **mount border**, which museum and
  archive photography carries constantly. It seals the sheet off from the image edge, so
  border-connected removal never reaches the real ground and the sheet survives whole. Once
  treated, its paper-coloured ground is nearly invisible against the canvas, which is what makes
  this easy to miss. `--shave 4` crops past it before matting.

**Knock out harder when you plan to fray.** `--from-alpha` moves the contour around, which exposes
any halo of background-coloured pixels the matte left behind — invisible on a clean knockout, but
pale flecks once the edge is torn. Erode a little more than feels necessary:
```bash
knockout.py --tolerance 40 --keep-largest --erode 3 --feather 0.5 in.jpg cutout.png
cut.py --style rough --from-alpha --seed 4 cutout.png final.png
```

**Baked soft drop shadow** (portable — no SVG filter): render a blurred dark copy under the
fragment as its own raster layer, offset a few px in the light direction.

**Grain / paper texture as a raster overlay** (NOT `feTurbulence` in the SVG): pre-render a grain
tile and embed it as a semi-transparent `<image>`:
```bash
# `magick` is ImageMagick 7; on IM6 (Debian/Ubuntu LTS) the same command is `convert`
magick -size 2400x3600 xc: +noise Random -colorspace Gray -attenuate 0.5 \
  -blur 0x0.3 grain.png    # embed at low opacity as an <image> overlay
```
Tonal overlays under `Multiply` must be **white-based** (dark marks on white) or they blacken the
image — otherwise use `SoftLight` / `Overlay`.

---

## 6. SVG assembly gotchas (filters, shadows, embedding)

**Assemble with `scripts/svgkit.py`** — reusable composition plumbing that already emits
filter-free, portable SVG: `Canvas(w,h)` with `embed()` (embed-once, compressed), `place()`
(rotate+scale), `contact_shadow()` (renderer-safe gradient), `text()`, `raw()` (escape hatch for
any custom SVG), and `render()` (inkscape). Import it and invent the layout on top. The gotchas
below are what it handles for you — and what to preserve if you ever hand-write SVG instead.

**Filter-free is the rule.** The shipped SVG must contain only pre-treated `<image>` fragments,
plain vector geometry, and live `<text>`. `feTurbulence`, `feColorMatrix`, `feDropShadow`, and
blend-mode compositing render *completely differently* across engines (inkscape vs. browser vs.
Preview vs. rsvg), so any filter that survives into the shipped file makes the `.svg` and `.png`
diverge — it looks right in one viewer only. Do all such effects in Stage A (ImageMagick) and bake
them into the raster. `check_render.sh` is the gate that catches leaks.

**Shadows without filters.** Two safe options: bake a soft drop shadow into the fragment's own
raster in Stage A (a blurred dark copy offset in the light direction), or lay a **radial-gradient
contact shadow** under the fragment in the SVG. Do NOT use `feDropShadow` — some Inkscape 1.x
builds render any element carrying it *completely blank*, vanishing whole fragments with nothing
but a console warning. `feGaussianBlur`+`feOffset` is also a filter and also diverges; avoid it too.

**Embed once, and small.** `Canvas.embed(path, max_width=…)` handles this: one copy per fragment
in `<defs>` referenced by `<use>`, JPEG for opaque layers, quantized PNG for cutouts, downscaled to
the width you pass. **Always pass `max_width` = the width you place it at** — that argument is the
first defence, and it defaults to off.

**`colors` is the second, and for treated fragments it is the bigger one.** Most reconciling
treatments — grain, halftone, duotone-plus-noise — write per-pixel noise, and noise is
incompressible: a fragment that is *visually* six flat inks can embed as several MB of PNG.
Turning `colors` **down** is near-lossless there, because the press output genuinely has few
colours (`embed(..., colors=32)` took one piece from 14 MB to 6.7 MB with nothing visible
changing). Turn it up, or to 0, only for banding on a large smooth-gradient fragment — the
opposite case. `embed()` prints the payload size when a single fragment lands over 1.5 MB.

Oversized embeds are a hard failure, not just bloat. Base64 attributes past libxml2's limits make
`rsvg-convert` abort with `Premature end of data in tag defs`, which reads as a corrupt file when
the XML is perfectly valid and inkscape opens it happily. If `check_render.sh` reports that, don't
hunt for a malformed tag — pass `max_width`, lower `colors`, and re-run.

**Clip fragments into a container shape** — the silhouette whose interior is made of other
pictures. `Canvas.clip_to()` is a context manager; everything placed inside is confined to the
silhouette's alpha:
```python
with c.clip_to("fragments/head.png", x=200, y=300, w=1400):
    for frag in crowd:            # each one clipped to the head's outline
        c.place(frag, x=…, y=…, w=…, rotate=…)
```
It emits a `<mask>`, not a `<clipPath>` — a clip path takes geometry and what a cutout gives you
is a raster alpha. Masks are not filter primitives, so the filter-free rule is untouched, and both
engines resolve them identically (verified: cross-engine RMSE 0.0009 on a 24-fragment container).

**A vector element that must belong to the pile has to be rasterised in Stage A.** A `<rect>`
title band drawn in the SVG floats on top of a stack of treated photographs looking subtly
synthetic — and it cannot be fixed in the SVG, because every raster effect lives in Stage A. So
generate the band as a raster, run it through the **same treatment with the same seed**, bake its
shadow, and place it in the z-stack where later fragments overlap it. It then belongs. This
follows from the filter-free rule, and the failure mode is easy to misread as a colour problem.
