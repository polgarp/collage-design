# Pipeline Recipes

Exact, reusable commands for the collage pipeline. Every run needs most of these — use them
verbatim instead of re-deriving them, and reach for the bundled `scripts/` helpers first (they wrap
the fiddly, error-prone steps). Read this when you reach Movement 4 (Compose) — except §4, which
you need at Movement 3, when you start pulling material.

**"Stage A"** below means fragment preparation — every raster operation, done before anything
enters the SVG: normalising exposure, cutting edges, lifting silhouettes, and applying the
reconciling treatment. It has a name because it is where all the pixel work belongs; the SVG stage
carries only assembly and type, which is what keeps the shipped file renderer-independent.

## Table of contents
1. Fonts (automatic; how the check works and why not `fc-match`)
2. Text → paths (portability)
3. Render + cross-renderer check (svg == png)
4. Fetching + asset validation (collisions, throttling, 404-HTML-as-image)
5. Surveying the pool, batching Stage A, and the art recipes (edges, knockouts, treatments)
6. SVG assembly gotchas (filters, shadows, embedding, clipping)
7. The build script (a first-class deliverable)

---

## 1. Fonts

**Mostly automatic now — `scripts/fonts.py` handles this.** `svgkit.Canvas` generates a working
font config on first use and `svgkit.render()` defaults to it, so a downloaded face no longer
depends on remembering to thread `FONTCONFIG_FILE=` through every command. If you shell out to
`inkscape`/`rsvg-convert` yourself, you still must pass it inline (shell state does not survive
between tool calls, so `export` won't do).

```bash
scripts/setup_fonts.sh ./collage-fonts                      # → FONTCONFIG_FILE=/abs/path/fonts.conf
scripts/setup_fonts.sh ./collage-fonts Futura Overpass      # …and verify these exist; exit 1 if not
scripts/fonts.py --list-families | grep -i grotesk          # what IS available
```

**A missing family is a hard error, not a warning.** `Canvas.text()` raises `FontSubstitution` at
the call that named the font. This is deliberate: a substituted face is baked into outlines by
`vectorize_text.sh`, and `check_render.sh` renders the same SVG twice and diffs, so a
wrong-but-consistent typeface passes every gate that follows. There is no later point at which the
mistake is visible. `COLLAGE_ALLOW_FONT_SUBSTITUTION=1` downgrades it to a warning.

**Test membership, not matching — never `fc-match`.** This is the part that is easy to get wrong,
and two plausible approaches are actively broken:

- **`fc-match` name comparison.** Matching always *succeeds*: it returns the nearest family it
  knows, so you are measuring name distance, not availability. Worse, Homebrew's stock config
  omits `/System/Library/Fonts/Supplemental` — where macOS keeps Futura, Optima, Baskerville,
  American Typewriter, Didot — so it reports those as Hiragino Sans while **Inkscape and rsvg
  render them correctly**, resolving through CoreText instead. Five of five tested faces were
  slandered this way. Fail a build on that and you block a working typeface.
- **Rendering a probe and comparing against a nonsense family.** Unsound: the fallback the engine
  picks depends on the *name*, so `Fake Face 99` and `ZzQq No Such Family` land on different faces
  and a genuinely missing font sails through.

`fc-list` enumerates rather than matches, so membership in it is exact. That is what `fonts.py`
uses (8/8 installed faces found, 3/3 invented ones rejected), against a config that names every
font directory — including the ones the stock config forgets.

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
verifies `svg == png`, never `svg == intended`. A font substituted before vectorizing is baked into
both renders identically and passes here. §1 catches that at the `text()` call and §2 refuses to
vectorize it — this gate never will.

---

## 4. Fetching and asset validation (avoid 404-HTML-as-image)

**Query the archive's API, not its pages.** Most open archives expose one, and it returns licence
and dimensions inline — so you filter for what is usable before downloading anything, instead of
opening twenty pages to find out. Two worth knowing by name:

```bash
# Library of Congress — any search URL takes &fo=json
curl -s 'https://www.loc.gov/photos/?q=night+street&fo=json' \
  | jq -r '.results[] | [.id, .title, .image_url[-1]] | @tsv'

# Wikimedia Commons — search + imageinfo in one call; extmetadata carries the licence
curl -s 'https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search \
&gsrnamespace=6&gsrsearch=matchbox%20label&gsrlimit=100&prop=imageinfo \
&iiprop=url|size|extmetadata' \
  | jq -r '.query.pages[] | [.title, .imageinfo[0].url,
            .imageinfo[0].extmetadata.LicenseShortName.value] | @tsv'
```

Tier-filter on the licence field before you fetch — it is far cheaper than downloading a pool and
discovering afterwards that half of it is CC BY-SA and has made the whole piece copyleft.

**Then use `scripts/fetch.py` for any pull of more than a handful of files.** It bakes in the four
things a hand-written loop gets wrong, all of which fail silently:

```bash
scripts/fetch.py --out sources/ --json items.json --attributions attributions.md
scripts/fetch.py --out sources/ --prefix lab_ URL [URL ...]
```

- **Filenames keyed on the archive's identifier**, never the title. Titles collide; a real pull
  reported 179 downloaded and left 168 on disk, and the surviving files then carry the wrong rows
  in `attributions.md`. Duplicate ids abort *before* the network, so it costs one line to fix.
- **`files on disk == downloads reported`**, asserted at the end. Fails the run if not.
- **Exponential backoff honouring `Retry-After`.** A 429 body writes to disk as a nonzero-size
  non-image, i.e. it looks exactly like a successful download.
- **Multi-frame detection.** Re-running is idempotent, so recovering a partial pull costs only the
  missing files.

**Do not raise the delay.** See the politeness note in the module docstring — briefly: the archives
are donation-funded, going faster past the limit *corrupts* the pool rather than speeding it up,
and abuse gets the next person blocked. Parallelise Stage A (`--jobs`) instead; that is where the
time actually is.

### Validating by hand

WebFetch sometimes reports **guessed/stale image URLs** (invented `-hires`/`-800` variants) that
404 to an HTML error page of nonzero size. Always confirm a download is a real image before using
it:
```bash
identify sources/foo.jpg   # errors if it's HTML/garbage, not an image
file sources/foo.jpg       # should say JPEG/PNG, not "HTML document"
```
**A file can be a real image and still break Stage A by being more than one.** Some Commons files
are animated GIFs whatever extension they were saved under (Muybridge sequences especially);
`identify` confirms they are images, because they are. But `magick in.jpg out.png` on a multi-frame
input writes `out-0.png`, `out-1.png`, … and never `out.png`, so the build dies two stages
downstream with a `FileNotFoundError` on a path that names nothing. **Append `[0]` to the input** —
harmless on single-frame files, so it costs nothing to do always:
```bash
magick 'in.jpg[0]' -colorspace Gray -level 3%,97% norm.png
```
`fetch.py` flags these at download time.

If validation fails, re-fetch the source page and read the true `src` — **unless the URL came from
an API response rather than a guess, in which case just retry the same URL once first.** Sustained
fetching gets throttled, and a throttle response is also an HTML page of nonzero size, so it looks
exactly like the stale-URL failure and sends you looking for a URL problem that isn't there. A
plain re-fetch succeeds. `sleep 1` between downloads in a bulk loop avoids it altogether.

---

## 5. ImageMagick art recipes

Do all raster effects here (Stage A) so the SVG stays filter-free.

**Run Stage A as a batch, not a loop — `--manifest` + `--jobs`.** Every fragment is independent,
so this is embarrassingly parallel, and a per-fragment subprocess is the wrong shape twice over:
for the 300–500 px images a deep archive pull yields, interpreter *startup* costs more than the
pixels. A manifest amortizes startup across every fragment in one process and `--jobs` uses the
other cores. Measured on 100 fragments: **13.9 s → 4.2 s (manifest) → 1.2 s (`--jobs 8`)**, and a
244-fragment piece runs four operations each.

```bash
cat > cuts.txt <<'EOF'
work/norm/001.png  work/cut/001.png  --seed 1
work/norm/002.png  work/cut/002.png  --seed 2      # per-item flags override the shared ones
EOF
cut.py   --style torn    --jobs 8 --manifest cuts.txt
treat.py --style duotone --seed 4 --jobs 8 --manifest treats.txt   # one shared seed: cohesion
```
Lines are `IN OUT [flags]`, inherit everything from the top-level invocation, and `#` comments and
blanks are skipped. **Output is byte-identical at any `--jobs`** — seeds are per-item, so nothing
depends on scheduling order; `scripts/check_batch.sh` asserts it against generated fixtures.

Note which seed spelling you want: a *per-item* `--seed` is right for cuts, where every tear should
differ; the *inherited* one is right for the reconciling treatment, where every fragment must match.
They are one line apart, which is the point.

**Look at the pool before you cut it up — `scripts/survey.py`.** It builds a labelled contact
sheet and measures each source, which is faster and more reliable than opening twenty files:
```bash
scripts/survey.py sources/* --sheet contact.png       # sheet + per-source table
scripts/survey.py sources/* --knockout-sheet ko.png   # the actual mattes, over a checkerboard
scripts/survey.py sources/* --liftable                # only the ones worth cutting out
scripts/survey.py plate.jpg --grid 4x5                # measure a gridded plate cell by cell
scripts/survey.py sources/* --find-patch 900 900      # best flat-colour crops, ready to paste
```
**The liftability verdict runs the real matte**, sweeping tolerance and measuring the shape that
comes back — `kept%`, `solidity` (area / bounding box: ~1.0 is a rectangle, a figure runs 0.3–0.6)
and `span` (that box as a share of the frame). It is not a prediction from input statistics, so it
cannot disagree with `knockout.py`; both judge at the same fixed resolution for the same reason.

This costs a few seconds per source and is worth every one of them. The heuristic it replaces —
flat border plus something far from it — was wrong in both directions, and expensively: on one
290-file pool it rated **111 sources liftable** whose mattes were whole photographs with the scan
frame trimmed, and rejected gridded plates that were clean per cell. The piece built from that pool
shipped one silhouette.

**Two traps the numbers now name for you:**

- *The flat thing is usually the scan frame.* Verdict says `whole frame — trimmed a scan border,
  lifted nothing`. Not fixable by tolerance; the frame is not the ground.
- *A plate is not a fragment.* Measure the crop you intend to cut. One real Muybridge plate scores
  `no — whole frame` as a file and **13 of 20 liftable cells** under `--grid 4x5`.

**Look at `--knockout-sheet` before committing.** A 3%-of-frame scrap passes the thresholds and is
obviously useless on sight. The numbers shortlist; the sheet decides.

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
knockout.py in.jpg cutout.png                    # --tolerance auto is the default
knockout.py --report in.jpg                      # judge one frame, write nothing
knockout.py --shave auto --keep-largest in.jpg cutout.png       # past a mount border, drop specks
knockout.py --global in.jpg cutout.png           # remove ALL bg-coloured pixels (scattered line-art)
knockout.py --bg 255,255,255 --tolerance 40 in.jpg cutout.png   # pin values in a build script
```
**Don't hand-search the tolerance.** `--tolerance auto` sweeps and picks the plateau of the kept%
curve — a real subject/ground boundary puts a gap in the colour-distance histogram, so kept% goes
flat across it, and no gap means no edge. It prints the value it chose; pin that into the build
script for reproducibility. Guessing this by hand costs several failed attempts per source and
teaches you the material is uncuttable when it isn't.

It then **tells you when it produced a rectangle** — solidity near 1.0 across most of the frame
means the matte trimmed a scan border and kept the photograph. Read that warning; it is the single
most common way a knockout fails, and it fails looking like a success.

A subject on a genuinely busy background still can't be lifted here — use that photo as a torn
*rectangle*, or install `rembg` for ML matting (opt-in; see the sourcing doctrine). Then fray the
real silhouette, which is what stops a knockout reading as a die-stamp:
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
  this easy to miss. `--shave auto` detects the band and crops past it before matting; `--shave 4`
  is the usual manual dose. Note that `--report` and `survey.py` already apply this detection, so
  their verdict is about the sheet's real ground rather than its mount.

**Knock out harder when you plan to fray.** `--from-alpha` moves the contour around, which exposes
any halo of background-coloured pixels the matte left behind — invisible on a clean knockout, but
pale flecks once the edge is torn. Erode a little more than feels necessary:
```bash
knockout.py --keep-largest --erode 3 --feather 0.5 in.jpg cutout.png
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

---

## 7. The build script (a first-class deliverable)

The script that made the piece ships with it. `philosophy.md` records the why; this records the
how, and is what lets a finished collage be *edited* rather than remade.

- **Re-runnable from the shipped folder.** Include the fragment preparation — cuts, knockouts,
  treatments — with paths relative to the output directory, so cloning the folder and running the
  script reproduces the `.png`. Never leave it depending on a scratch directory that isn't shipped:
  that is the difference between an artwork you can adjust and a one-off you can only admire.
- **Parametric.** Fragment positions and scales, palette hexes, canvas size, rotation and opacity
  as named variables near the top. Tuning the piece should mean changing a value, not reading the
  composition code and finding the right number buried in a call.
- **Legible.** Comment the intent of each layer — what it is doing for the picture, not what the
  function does.

```python
# --- parameters -------------------------------------------------------
W, H        = 2400, 2400
INK, PAPER  = "#141414", "#e8e2d0"
SEED        = 7
FRAGMENTS   = [   # (source,               x,    y,    w,   rot)
    ("work/label_017.png",                 180,  240,  520,  -3),
    ("work/label_042.png",                 640,  190,  380,   5),
]
# ----------------------------------------------------------------------
```

Pin values the tools chose for you rather than re-deriving them at build time — an auto-selected
knockout tolerance, a seed — so the script is deterministic and a re-run cannot drift.
