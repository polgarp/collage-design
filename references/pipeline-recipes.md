# Pipeline Recipes

Exact, reusable commands for the collage pipeline. Every run needs most of these — use them
verbatim instead of re-deriving them, and reach for the bundled `scripts/` helpers first (they wrap
the fiddly, error-prone steps). Read this when you reach Movement 4 (Compose).

## Table of contents
1. Font setup (fontconfig)
2. Text → paths (portability)
3. Render + cross-renderer check (svg == png)
4. Asset validation (avoid 404-HTML-as-image)
5. ImageMagick art recipes (duotone/tritone, edges, knockouts, grain)
6. SVG assembly gotchas (filters, shadows, embedding)

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
scripts/check_render.sh collage.svg "$CONF"     # if the piece uses downloaded fonts
```
`check_render.sh` renders the SVG in both inkscape and rsvg, compares them, and prints PASS/FAIL
+ normalized RMSE (threshold 0.02). PASS means the shipped `.png` — which is the inkscape render —
is the same picture the `.svg` produces in any viewer. If it FAILS, a renderer-dependent filter or
an un-vectorized font leaked in; fix per the filter-free rule, don't ship.

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
If it fails, re-fetch the source page and read the true `src`.

---

## 5. ImageMagick art recipes

Do all raster effects here (Stage A) so the SVG stays filter-free.

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
don't cover, make your own and reuse the plumbing instead of rebuilding it:
```bash
# drop-in file: my_edge.py defines  def mask(w, h, p, rng): ... return L_image
scripts/cut.py --style-file my_edge.py in.jpg out.png
# or import the plumbing:  from cut import load, compose (+ _profile/_organic_mask/_roughen_alpha)
```
Same spirit for the ImageMagick treatments below — they are starting points to extend, not a fixed
set. Reuse the infrastructure; invent the aesthetics.

**Silhouette knockout — use `scripts/knockout.py`** (lift a subject off a flat/neutral ground;
PIL/numpy only, no ML):
```bash
knockout.py --tolerance 40 in.jpg cutout.png     # remove border-connected bg, keep interior holes
knockout.py --global in.jpg cutout.png           # remove ALL bg-coloured pixels (scattered line-art)
knockout.py --bg 255,255,255 --keep-largest in.jpg cutout.png   # explicit bg + drop stray specks
```
Handles flat/neutral backgrounds. A subject on a busy background can't be lifted cleanly here — use
that photo as a torn *rectangle* instead, or install `rembg` for ML matting (opt-in; see the
sourcing doctrine). Then fray the real silhouette:
`cut.py --style rough --from-alpha cutout.png out.png`.

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
whole defence, and it defaults to off.

Oversized embeds are a hard failure, not just bloat. Base64 attributes past libxml2's limits make
`rsvg-convert` abort with `Premature end of data in tag defs`, which reads as a corrupt file when
the XML is perfectly valid and inkscape opens it happily. If `check_render.sh` reports that, don't
hunt for a malformed tag — you embedded at full resolution; pass `max_width` and re-run.
