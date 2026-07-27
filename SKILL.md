---
name: collage-design
description: Create beautiful cut-and-layer collage art in .svg and .png using a collage philosophy, sourcing real open-licensed imagery and composing it into a single crafted piece. Use this skill whenever the user asks for a collage, photomontage, cutout composition, cut-and-paste artwork, mixed-media poster, or any single artwork made by cutting and layering multiple found/photographic images into one composition — even if they don't say the word "collage." This is for creating a finished art piece, not arranging a moodboard grid, removing a background from one image, stitching a panorama, or generating art from code. Sources only open-licensed images and logs attributions; never copies living artists' compositions.
license: Complete terms in LICENSE.txt
---

Instructions for making **collage** — art assembled from real, found imagery: sourced, cut,
layered and reconciled into a single object, with text laid over as the philosophy requires.
Built from **actual photographs and printed material found on the open web**, under
open licences only.

The deliverables are `philosophy.md`, `attributions.md`, a self-contained `.svg`, its `.png`
render, and the build script that made them.

Four movements:
1. **Collage philosophy** (`philosophy.md`)
2. **Deduce the subtle reference**
3. **Source the material** (open-licensed or user-supplied → `sources/` + `attributions.md`)
4. **Compose on an SVG substrate** → `.svg` + `.png` + build script, then a polish pass.

### BEFORE STARTING

- **Real imagery is mandatory** — either downloaded from the open web (needs `WebSearch`/`WebFetch`
  or browser tools) or taken from a folder the user points you at. With neither available, say so
  and stop; never substitute generated or invented imagery.
- **Local tooling:** ImageMagick, Inkscape, librsvg, fontconfig, Python + Pillow + NumPy. Run
  `scripts/check_deps.sh` first; it prints the install line for anything missing.
- **This is a long job** — if the user wants something quick, tell them before Movement 1. A
  multi-piece **series** costs far less than N× a single piece: sourcing dominates the budget, and
  one source pool feeds every piece in the set.

---

## THE DEFAULT REGISTER — PHYSICALITY OVER DIAGRAM

A collage is **physical**. Fragments overlap, occlude, and touch; cut subjects escape their
frames; torn edges show their fiber; the surface accumulates. Unless the philosophy decides
otherwise *in writing*, the piece must read instantly as **cut paper layered by hand** — not as a
clean diagram with a few small photos inset into tidy, separated boxes.

Left alone, composition slides toward the grid: neat rectangles, one timid image each, evenly
spaced, floating in polite empty space. **If the piece could be rebuilt in PowerPoint with nothing
lost, it drifted.**

**The defaults:**
- Fragments **overlap and occlude** — things sit in front of other things.
- Some subjects are **silhouette knockouts that break their bounding box** — a hand, a figure, a
  specimen spilling past any implied frame. This is settled at *sourcing*, not composition:
  knockouts need flat/neutral grounds (Movement 3) and documentary photography rarely has one. With
  busy sources, take the escape from a fragment bleeding off the **canvas edge** instead.
- **Edges are visible and physical** — torn fiber, knife-cut bevel, cast shadow; never an
  invisible seam around a rectangle.
- **Density is a virtue** — and it is a matter of *count and scale variance*, not coverage: many
  fragments, the largest several times the smallest. A dozen mid-sized pieces at even spacing is
  the drift however much of the page they cover. Open space only where text must be read.

### OVERRIDING A DEFAULT

Any default above can be set aside — deliberate tonal clash (Höch, Heartfield), the rigorous
photographic grid, the near-empty field holding one fragment, glitch and scan artifact,
type-as-image are all available registers.

Override **in the philosophy, by name, with a reason** — one sentence saying which default is set
aside and what the piece gets for it:

> *"Fragments are NOT tonally unified: each source keeps the colour temperature it arrived with,
> because the collision between registers is the argument the piece is making."*

**Then say what replaces it.** An override removes a constraint; it has to add one, or the piece
reads as a mistake rather than a decision — *two treatments that never cross, curved edges for one
family and straight for the other, a fixed paint order*. What replaces it is a sourcing and
cutting decision, so it belongs here, before Movement 3 spends anything on material.

Named there, the override governs the rest of the run and the Movement 4 self-check validates
against it. Unnamed, the default stands.

---

## MOVEMENT 1 — COLLAGE PHILOSOPHY CREATION

Write a **collage philosophy** — an aesthetic movement, not a layout or template. Its subject is
**found material and what is done to it**: where it comes from, how it is severed, how it stacks,
and what reconciles it.

Read the brief for the aesthetic territory it implies, not as a checklist to satisfy. Write a
document an *unfamiliar* designer could execute without ever seeing the original request —
decisions stated, reasons given, room left. It determines which fragments get hunted in Movement 3
and how they collide in Movement 4, so decide everything here that a later movement will need.

### PLACE THE MOVEMENT DELIBERATELY

First, state where the movement lands on each axis below, and check you landed there because the
brief pulled you — not because it was the nearest thing to reach:

- **Period** — what era does the material come from? Not automatically the twentieth century, and
  not automatically the past.
- **Colour** — saturated or desaturated, hot or cold, chromatic or monochrome. Degraded sepia is
  one answer among many, and it is the one that arrives unbidden.
- **Register** — the emotional weather. Institutional, forensic, elegiac, but equally: comic,
  ecstatic, tender, lurid, devotional, absurd.
- **Origin** — whose archive? There is a strong pull toward Western European and North American
  institutions because they are the easiest to search. Resist it when the subject points elsewhere.
- **Domain** — documents and specimens are the reflex. Food, textiles, sport, weather, music,
  crowds, machinery in use, bodies in motion, the street are all equally cuttable.

These name the answers that arrive **unbidden**, not banned answers. Sepia, the Western archive,
the specimen plate are each right sometimes: choose one deliberately, say why, and it is fine.
Avoiding whatever this list mentions is the same failure as defaulting to it — and worse in one
way, because an avoidance written into `philosophy.md` binds every movement after it.

Name the movement in 1–2 words once you know where it stands. If the name would sit comfortably
next to a name you have produced before, you have probably defaulted rather than decided.

### THE SIX DIMENSIONS

**Articulate the philosophy** as one substantial paragraph per dimension below, under a short
opening that says what the movement is. Collage has its own load-bearing dimensions — the
material's origin and its treatment, not just form and colour. Cover each **once**, without
redundancy:

- **Source character** — what *family* of found material this movement draws from, and what that
  family sounds like. Every printed or photographed thing that has ever been archived is in scope:
  what matters is that you name one voice and stay with it, not that you pick from a list.
- **Cut & edge language** — how the material is severed from its origin: torn/deckle (paper fiber),
  rough (jagged rip), scissor/knife-clean (crisp straight or diagonal), rounded (snapshot corners),
  scalloped or pinked (decorative vintage-print edges), silhouette knockout (subject lifted from its
  background), sticker keyline (die-cut, a band of backing paper following the silhouette), or burnt
  (scorched, aged). The edge is where collage declares its attitude — mechanical cuts read
  *deliberate*, torn reads *urgent*, treated reads *decayed* — and a strong
  philosophy **assigns different edge languages to different source families**, so that where a
  fragment came from is legible in how it was cut.
- **Layering & depth** — how fragments stack, and what stacking *means* here. Collage is
  fundamentally about things *in front of* other things, so say what being in front amounts to:
  precedence, chronology, suppression, who is burying whom. "Order by occlusion" is a rendering
  instruction; an order carrying an argument is a decision, and the difference shows. The
  **container shape** is available too — one large silhouette holding the others, acting as both
  subject and ground (`svgkit.clip_to`), a register that wants many small fragments rather than a
  few big ones. Shadows default to paper lifting a millimetre off paper: tight, close, one light.
  Anything broader is an argument the philosophy has to make.
- **The reconciling move** — *the decision that most determines whether this works.* Disparate
  sources arrive in clashing colour, light and grain. The default answer is a unifying treatment
  that fuses them — a clamped palette, duotone or tritone wash, desaturation, a shared grain or
  halftone, one consistent light. The other answer is to keep the clash and discipline it
  elsewhere, in the cut or the grid or the light, so the collision reads as intended rather than
  unresolved. Either is legitimate; **silence is not.** Sources with no stated relationship stay a
  pile. Whichever you choose holds identically across every fragment — and, if the piece is one of
  a set, across every piece in it. (Identically at the *treatment* step. Normalizing each
  fragment's exposure beforehand is prep, and is required — see the recipes.)
- **Composition, rhythm & negative space** — how fragments are orchestrated across the field, and
  how emptiness is used as deliberately as image. Decide the **count and the spread of scales**
  here too: how many fragments, and how large the largest runs against the smallest. Both follow
  from the subject the way ground and rhythm do, and left undecided they come out as a dozen
  mid-sized pieces every time. Settle what the **ground** is while you are here: a photographic
  ground competes with everything laid over it at any opacity, so it works when the piece gives
  that competition a job — a scene the fragments interrupt, a field they are cut out of.
  Otherwise flat material — paper, textile, a printed sheet — with photographs entering as
  fragments on top of it.
- **Text treatment** — the register follows the movement, so decide it here rather than at the end:
  how type is set, how it is cut, whether it sits on the imagery or under it. Usually sparse and
  serving the image — but a philosophy may put type at the centre and make the imagery serve *it*,
  if it says so. Decide as well about the type that **arrives inside the fragments** — can labels,
  studio imprints, signage and price tickets bring their own lettering, often louder and better
  drawn than anything you will set. Does the piece's voice outrank the sources', match them, or
  hide among them? Not choosing is what leaves a title designed as though the page were empty; the
  default is **distinct, or largest** — compete or differ, but don't tie. What's never wanted is
  *explanation*: paragraphs mean the piece stopped being visual. Poster **furniture** is a
  different thing and usually wanted — dates, venue, a billing block, an edition number, a
  printer's imprint — small structured text, and often what makes a poster read as a poster rather
  than an image with a word on it.

**Three things the philosophy has to get right:**

- **Say each thing once.** Six dimensions, six passes. If colour turns up in three paragraphs the
  document has stopped making decisions and started reassuring itself. Go deeper instead of
  circling back.
- **Set the standard by describing the hand.** The finished piece has to look *made* — cut by
  someone with a scalpel, a cutting mat, and more patience than the job strictly required. Don't
  assert this once and move on; write the philosophy so that the standard is legible in how it
  talks about material. Describe the registration a fragment gets, how a seam disappears, what
  the maker would refuse to let past. A collage that reads as clip-art dropped onto a page has
  failed before anyone considers whether the concept was good.
- **Decide the aesthetic, not the artwork.** The philosophy fixes the register; execution still
  has to invent the composition. Over-specify and you have written a layout in prose and thrown
  away the interpretation that makes it worth doing.

Keep it **generic and reusable** — no mention of this particular commission. It should read like
a movement someone else could adopt for a different subject entirely. Output it as `philosophy.md`.

### BEFORE YOU MOVE ON — READ IT BACK

Five ways a philosophy fails, in the order they're worth checking. These are *tests* — answer each
against what you actually wrote, not against what you meant:

1. **Too thin to execute.** The commonest failure. For each of the six dimensions: could someone
   who has never seen the brief act on it without asking a question? A dimension that is a phrase
   rather than an argument gets improvised later, and improvisation is where drift enters.
2. **Drifted into a diagram.** Nothing overlaps, occludes or tears, and no sentence says that was
   intended. Commit to the default register or name the override.
3. **Never settles the reconciling move.** Point at the sentence. If you can't, it isn't there.
4. **Talks about text like a writer.** If the philosophy implies explanation, it will get
   paragraphs. Check the opposite too: a philosophy that has banned type outright has over-read
   the warning — poster furniture is not prose, and a hedge here becomes a ban downstream.
5. **A template in disguise.** Positions, fragment counts, a layout in prose — that leaves
   execution nothing to interpret.

---

## MOVEMENT 2 — DEDUCE THE SUBTLE REFERENCE

**Do this before sourcing a single image.** The philosophy settled how the piece looks. This
settles what it is *about* — and in collage those are not the same question, because the subject
arrives through the material itself rather than through anything drawn.

Find the specific, slightly obscure thread running under the brief and commit to it. Not the
stated topic, and not an illustration of it — the thing adjacent to it that someone who knows the
territory would recognise on sight and never need explained.

**The test is asymmetry.** Someone who knows the reference should feel it land. Everyone else
should see a composition that works completely on its own terms and never notice anything was
being alluded to. If the reference has to be pointed out, it wasn't embedded — it was captioned.
If the piece only works for people who get it, the composition is doing too little.

**The reference lives in the sourcing decisions.** Which archive you cut a figure out of *is* the
argument, made before a single fragment is placed. Carry the thread into Movement 3 as a
constraint on the material list, and let it stay unannounced.

---

## MOVEMENT 3 — SOURCE THE MATERIAL

Translate the philosophy + reference into a concrete **material list** — the specific subjects,
textures and backgrounds the composition needs, each named precisely enough to search for.

### SOURCING DOCTRINE — OPEN-LICENSED OR USER-SUPPLIED

Two legitimate sources, and nothing else, because the output has to be safe to print, publish and
sell: **open-licensed wells**, and **material the user points you at** — their own photographs,
scans, a folder of assets. Mix them freely when the piece wants it. Copy user-supplied files into
`sources/` like anything else so the build stays reproducible, and log them in `attributions.md`
as *supplied by the user* rather than sourced: you cannot vouch for rights you did not verify, and
the tiering below applies only to what you fetched yourself.

**Find the right archive before you start pulling.** The general wells below will return
*something* for almost any query, which is exactly the trap — they make it unnecessary to look for
the collection that actually holds this subject, and the piece ends up assembled from whatever is
easiest to find rather than from the best material that exists. So spend a search or two first:
look for the specialist, regional or national archive for this subject, in the language and country
it belongs to, and check whether it publishes openly. A national library, a university special
collection, a state archive, a museum in the region the work is about, a subject-specific
repository. Most of what is openly licensed in the world is not on the first list you think of.

**When a collection turns out to be right, pull deep from it — and cut more than one fragment from
each thing you pull.** Finding the archive is the expensive part, not taking things out of it:
inside a public-domain collection of a thousand can labels, the fifteenth costs a line in a
download loop and a row in `attributions.md`, and a representative handful is what leaves a piece
thin. One plate also yields a different fragment per crop, the same crop recut with a different
`--seed` is a genuinely different edge, and a cut fragment can be placed more than once at
different scales — `svgkit` stores each payload once, so repetition is free. The fragment count is
not the download count. Recutting and repetition are seasoning on a large pool rather than a
substitute for one: used to disguise a thin pool they only make the thinness rhythmic.

General wells, as a floor rather than a map:

- **Wikimedia Commons** — public-domain and CC imagery, huge archive.
- **Openverse** (openverse.org) — CC/PD search across many sources.
- **Europeana** and **DPLA** — aggregators across hundreds of European and US institutions.
- **Internet Archive** — books, ephemera, film stills, scanned periodicals.
- **Museum and library open access** — The Met, Rijksmuseum, Art Institute of Chicago, Smithsonian,
  NYPL, Biodiversity Heritage Library, and their equivalents anywhere else in the world.
- **Government image libraries** — NASA, NOAA, and national equivalents; usually public domain.
- **Unsplash / Pexels** — contemporary free-to-use photography.

**Query the archives' APIs rather than their pages** where they have one — `loc.gov/photos/?q=…&fo=json`
and the Wikimedia Commons `generator=search` endpoint with `iiprop=url|size|extmetadata` both return
dimensions and licence inline, so you tier-filter in `jq` instead of opening twenty pages. Fall back
to `WebSearch` / `WebFetch`, and to browser tools if any are available when a source needs
navigating. Download **high-resolution originals** into a `sources/` directory —
resolution matters, because cutting and scaling punishes small images. **Validate every download
is a real image** (`identify` / `file`) before using it: WebFetch sometimes reports a guessed URL
that 404s to an HTML error page of nonzero size that looks like a successful download. Keep
`sources/` as pristine originals; write processed cutouts and intermediate fragments to a scratch
working dir, never into `sources/`.

**Prefer *cuttable* subjects.** Extraction here is classical (`scripts/knockout.py`, PIL/numpy),
so it lifts a subject cleanly only off a flat ground **the subject contrasts with**. Flatness
alone is not the predictor: a pale dress on a pale studio sweep is a perfectly flat ground and
cannot be lifted at any tolerance, because subject and fill sit at the same value. Don't guess at
it — `scripts/survey.py` measures both and prints a verdict per source, and `knockout.py` says so
when a matte has eaten the subject. A subject on a busy background can't be knocked out cleanly
without ML matting (`rembg` is an opt-in ~170 MB dependency; install it only if a piece truly
demands it), so use such photos as torn **rectangles** instead. Choosing what you can actually cut
is half of good collage sourcing.

**Then look at what you actually got** — `scripts/survey.py sources/* --sheet contact.png` builds
a labelled contact sheet alongside the measurements. Composition is decided by the material, and a
directory listing is not the material.

### LICENSE COMPATIBILITY — WHAT THE SOURCES DO TO THE FINISHED PIECE

"Open-licensed" is not one thing. A collage is a derivative of *every* fragment in it, so the most
restrictive source sets the terms for the whole piece. **Ask the user about intended use before
sourcing** if the brief doesn't already make it clear, then prefer sources in this order:

| Tier | | |
|---|---|---|
| 1 | **PD / CC0 / US gov** | No strings. Default here — it keeps the piece unencumbered. |
| 2 | **CC BY** | Commercial use fine, credit required. Just ship `attributions.md`. |
| 3 | **CC BY-SA** | **Viral** — ShareAlike propagates, so the finished artwork must itself be CC BY-SA. Usually wrong for a commission, album cover, book jacket, anything sold. Only with the user's agreement, and say so in `attributions.md`. |
| 4 | **CC NC / ND** | ND is disqualifying outright — a collage *is* a derivative. NC bars commercial use of the result. Last resort, never silently. |
| 5 | **Unsplash / Pexels** | Own licences, not CC. Fine inside a composed collage; they forbid redistributing an image standalone. |

**Model-generated stock is not open-licensed material** and is out of scope wherever it's hosted.
This is *found* collage.

**Log every asset** in `attributions.md`: one row per file with source URL, creator and licence,
or *supplied by the user* for anything they provided. Close with whatever notices CC BY / CC BY-SA
require, and — if a copyleft or non-commercial source made it in — a plain line on what that means
for reusing the piece. This is what makes the work publishable, not bookkeeping.

**Hard rule:** never pull from general web search, watermarked stock, or a living artist's
portfolio. If nothing open-licensed fits a slot and the user has supplied nothing for it, **change
the composition** — different fragment, reframed idea, lean on texture. Never fabricate or generate
a substitute. Working only with what genuinely exists is part of the craft.

---

## MOVEMENT 4 — COMPOSE ON AN SVG SUBSTRATE

With philosophy, reference, and material in hand, assemble the collage. The deliverables are a
self-contained `.svg`, its `.png` render, and the build script that made them.

Reach for what the piece needs, in whatever order, and build what these steps don't cover — when a
philosophy wants an edge or a treatment the presets don't reach, write it against `cut.py
--style-file` / `treat.py --style-file` or import their cores, rather than settling for the nearest
preset. `svgkit.py` has no layout presets: invent the composition.

Only three things are fixed — open-licensed sources, a filter-free `.svg` that matches its `.png`,
and a saved build script. Filter-free is what makes the second one true: SVG filter primitives
render differently in every engine, so all raster effects happen in ImageMagick/PIL at Stage A and
SVG carries nothing but assembly and type.

**Read `references/pipeline-recipes.md` before running the stages below.** It holds the exact
commands and the traps for each one — font setup, text-to-path, rendering and the portability
check, asset validation, the raster recipes, and SVG assembly. Use it rather than re-deriving any
of it.

- **Stage A — cut & unify.** Cut each fragment's edge in the philosophy's edge language with
  **`cut.py`** (clean / rounded / scallop / pinking / torn / rough / burnt, any subset of sides,
  seeded; `--sticker` lays a die-cut keyline, and belongs *after* the treatment). Lift the
  silhouettes chosen at sourcing with **`knockout.py`**, then fray the real
  contour via `cut.py --from-alpha`. Apply the unifying treatment with **`treat.py`** —
  *identically* to every fragment, same style and seed, unless the philosophy overrode
  unification — so clashing sources fuse into one object.
- **Stage B — assemble (SVG).** Compose with **`svgkit.py`**: `Canvas` with embed-once, `place`
  with rotate+scale, `contact_shadow`, `text`, `clip_to` for a container silhouette, a `raw()`
  escape hatch, `render`. Place fragments per the default register — overlapping, occluding,
  colliding — or per whatever the philosophy named instead, in the order the philosophy said the
  stacking means, with baked or radial-gradient contact shadows on one consistent light. Pass
  `embed(..., max_width=)` at the width each fragment is drawn.
- **Stage C — text.** Optional, and free in register — whisper-labels to bold display type
  overlaid across the imagery, even fractured non-linearly (hard to do well; attempt with intent,
  not as a gimmick). Use system faces or download what the philosophy asks for into
  `./collage-fonts`; either way, vectorize to paths before shipping.
- **Stage D — render & verify.** Render with **inkscape**, then prove portability with
  `scripts/check_render.sh`. A PASS means the `.svg` and the shipped `.png` are the same picture in
  any renderer. A FAIL means the two engines disagree, which is usually a leaked filter or an
  un-vectorized font — read the diff image it writes before assuming which, because a grain-heavy
  piece can diverge on resampling alone. Then run the self-check below.

### THE COLLAGE SELF-CHECK — RUN IT BEFORE YOU CALL THE PIECE DONE

An internal gate, not a report. **Look at the rendered `.png`** and answer these for yourself,
naming specific fragments — vague answers mean you didn't look. Where the philosophy named an
override, the piece answers to the override instead, and you must be able to point at the
sentence. Then act on the result; none of this goes to the user.

1. **Occlusion** — name two fragments where one visibly sits in front of the other.
   *Override: a philosophy committed to a grid, or to isolated fragments.*
2. **Escape** — name the fragment whose silhouette breaks its bounding box or the canvas edge.
   *Override: a philosophy committed to contained, rectangular fragments.*
3. **Unification** — name the treatment (style + seed) applied to every fragment and confirm none
   escaped it. *Override: a philosophy committed to deliberate tonal clash — point at the sentence
   naming what governs it instead, and confirm the piece obeys that.*
4. **Density** — count the fragments, then look at the *shape* of the arrangement: do three or
   more share a baseline, and is the largest at least 3× the smallest? Coverage is not the
   measure. Even scale at even spacing is exactly what drift looks like, and it can be perfectly
   dense. *Override: a philosophy that fixed a different count, or asked for the regularity, and
   said what it is doing.*

A default that fails with no override means the piece **drifted** — it isn't finished. Fix it and
re-render. A reason constructed after the fact is not an override; it is the drift talking.

Iterate here until it passes. Ship the piece, not the checklist.

**Ship the `.svg`, the `.png`, and the build script — the script is a first-class deliverable.**
`philosophy.md` records the why; the build script records the how, and lets the piece be *edited*
rather than remade. Author the whole composition as one legible script in the output directory:

- **Re-runnable from the shipped folder** — include the Stage-A prep (cuts, treatments, knockouts)
  in the script, with paths relative to the output dir, so cloning the folder and running it
  reproduces the `.png`. Never leave it depending on a scratch directory.
- **Parametric** — fragment positions and scales, palette hexes, canvas size, rotation, opacity as
  named variables near the top, so the piece is tuned by changing values.
- **Legible** — comment the intent of each layer.

A collage you cannot regenerate or adjust is a dead end.

**The craft bar.** The piece has to survive close looking: seams that don't announce themselves,
the treatment reaching every fragment, every shadow answering to one light, nothing placed where
it merely fits. Two readings, both required — it resolves instantly into one object from across a
room, and rewards standing in front of. Follow your eye, with the philosophy as the thing you
argue with.

---

## FINAL POLISH PASS

**Assume the first render isn't good enough** — treat it as having come back with the note every
collagist eventually gets: *close, but it still looks assembled rather than made.* This pass is
not optional.

**Do not add more fragments to fix how it *reads*.** Reaching for one more image treats a
coherence problem as a content problem. (A count that came out thin is a different fault, caught
at the self-check and fixed before you arrive here.) Ask instead how what is already present reads
more as a single made object — usually:

- **Registration** — fragments that nearly align but don't.
- **Reconciliation** — a fragment still carrying its original colour temperature.
- **Light** — a shadow falling the wrong way. Every shadow answers to one lamp.
- **Edge** — a tear reading as an effect rather than as paper; recut with a different seed.

Adjust the build script, re-render, re-run the self-check.
