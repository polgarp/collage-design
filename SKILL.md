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
- **The bundled toolkit is a reference implementation, not the requirement.** `scripts/` covers
  fetching, surveying the pool, edge-cutting, silhouette extraction, unifying treatments and SVG
  assembly; `references/pipeline-recipes.md` holds the exact commands and the traps for each. Use
  them — they encode failures that are expensive to rediscover. But what this skill actually
  demands is the judgement in Movements 1–3 and the invariants in Movement 4. If you have better
  tools, use them and meet the same bar.
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
  specimen spilling past any implied frame. This is settled at *sourcing*, not composition: it
  depends on finding material a subject can be lifted out of, which is Movement 3's job and is
  measured there rather than guessed. Most pools contain some; plates, sequences and anything shot
  against a sweep or a night ground are usually rich in them, and the measurement finds them per
  *crop*, so a source that looks hopeless whole is often not. A pool that genuinely holds none —
  labels and ephemera cropped to their own printed border, say — takes the escape from a fragment
  bleeding off the **canvas edge** instead. Reach for that because the material was measured and
  came back empty, not before looking.
- **Edges are visible and physical** — torn fiber, knife-cut bevel, cast shadow. Every fragment
  shows how it was severed; the edge is where the piece declares it was cut by someone.
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
  subject and ground. It is an unforgiving register: it wants many small fragments rather than a
  few big ones, and it wants them inside the silhouette rather than scattered across its bounding
  box, or the outline does no work and the piece reads as random shapes.
  Shadows default to paper lifting a millimetre off paper: tight, close, one light.
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
  default is **distinct, or largest** — compete or differ, and let the two voices be told apart.
  Keep type in service of the image: a word, a label, a line. The moment it explains, the piece has
  stopped being visual and started being a caption. Poster **furniture** is a
  different thing and usually wanted — dates, venue, a billing block, an edition number, a
  printer's imprint — small structured text, and often what makes a poster read as a poster rather
  than an image with a word on it.

**Three things the philosophy has to get right:**

- **Say each thing once.** Six dimensions, six passes. If colour turns up in three paragraphs the
  document has stopped making decisions and started reassuring itself. Go deeper instead of
  circling back.
- **Set the standard by describing the hand.** The finished piece has to look *made* — cut by
  someone with a scalpel, a cutting mat, and more patience than the job strictly required. Carry
  that standard through every paragraph rather than asserting it once: write so it is legible in
  how the document talks about material. Describe the registration a fragment gets, how a seam
  disappears, what the maker would refuse to let past. A collage that reads as clip-art dropped
  onto a page has failed before anyone considers whether the concept was good.
- **Decide the aesthetic, not the artwork.** The philosophy fixes the register; execution still
  has to invent the composition. Over-specify and you have written a layout in prose and thrown
  away the interpretation that makes it worth doing.

Keep it **generic and reusable** — no mention of this particular commission. It should read like
a movement someone else could adopt for a different subject entirely. Output it as `philosophy.md`.

### BEFORE YOU MOVE ON — READ IT BACK

Five ways a philosophy fails, in the order they're worth checking. These are *tests* — answer each
against what you actually wrote, not against what you meant:

1. **Decides nothing.** The commonest failure, and thickness disguises it — a paragraph can be
   rich, well-written and still rule nothing out. So for each of the six dimensions, name what it
   **rules out**: the move a later movement is now forbidden to make. A dimension that forbids
   nothing has not decided anything, and gets improvised at execution time — which is where drift
   enters. This is the whole load-bearing job of the document: the skill stays broad on purpose,
   and the philosophy is where a piece gets its constraints.
2. **Drifted into a diagram.** Nothing overlaps, occludes or tears, and no sentence says that was
   intended. Commit to the default register or name the override.
3. **Never settles the reconciling move.** Point at the sentence. If you can't, it isn't there.
4. **Talks about text like a writer.** If the philosophy implies explanation, it will get
   paragraphs. Check the opposite too: a philosophy that has banned type outright has over-read
   the warning — poster furniture is not prose, and a hedge here becomes a ban downstream.
5. **A template in disguise.** Positions, a fragment-by-fragment layout in prose, an arrangement
   described rather than a register decided — that leaves execution nothing to interpret. A
   *count* and a scale ratio are not this: they bound the composition without drawing it.

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
random seed is a genuinely different edge, and a cut fragment can be placed more than once at
different scales — a repeated placement should cost nothing but a line. The fragment count is
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

**Query the archives' APIs rather than their pages** where they have one: they return licence and
dimensions inline, so you can filter for what is usable *before* downloading anything rather than
opening twenty pages to find out. Fall back to search and fetch tools, and to a browser if one is
available when a source needs navigating.

**Download with the bundled fetcher rather than a loop written for the occasion.** A bulk pull
fails in ways that are silent by nature — the log reports success and the pool is quietly wrong,
with files missing and `attributions.md` crediting the survivors to the wrong rows. That is a
licensing document going wrong, which is the most expensive failure available here. Use something
that guards against it.

**Be polite, and don't optimise it away.** These archives are free and donation-funded, and going
faster than they allow corrupts the pool rather than speeding it up. The speedup worth having is on
local processing, which is a different resource entirely.

Download **high-resolution originals** into `sources/` — resolution matters, because cutting and
scaling punishes small images. It is a reason to prefer big scans, not always a reason to reject
small ones: where a whole archive shares a low ceiling, let the pool set the canvas size instead of
fighting it, and the same material that looked marginal is drawn at native resolution. Keep
`sources/` as pristine originals; write processed cutouts and intermediate fragments to a scratch
working dir, never into `sources/`.

**Prefer *cuttable* subjects.** Choosing what you can actually cut is half of good collage
sourcing, and it is a measurement rather than a judgement — so measure it, per source, before
composing anything around material that may not survive extraction.

**What usually defeats a knockout is framing, not contrast.** The reflex worry — a subject sitting
at the same value as its ground, a pale dress on a pale sweep — is real, unfixable at any
tolerance, and rare. The common failures are both about what is in the frame:

- **The flat thing is usually the scan frame.** Archive photography is mounted or scanned with a
  border, so a uniform edge means nothing: keying against it trims the border and returns the whole
  photograph as a rectangle. A test that only asks "is the border flat?" calls that a success.
- **A plate is not a fragment.** Gridded plates, contact sheets and mounted prints measure as
  hopeless whole and are often clean cell by cell. Measure the *crop you actually intend to cut*,
  never the file as it happens to be framed.

So check the crops before concluding a pool has nothing in it. Where a piece
genuinely needs a subject off a genuinely busy ground, ML matting is available as an opt-in extra.
Otherwise such photos are torn **rectangles**, which is an honest answer and not a lesser one.

**Then look at what you actually got** — the pool as a contact sheet, and the cutouts as actual
mattes. A verdict is a word; a knockout that quietly returned a rectangle looks fine in a table and
is obvious on sight. Composition is decided by the material, and a directory listing is not the
material.

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

## MOVEMENT 4 — COMPOSE

With philosophy, reference, and material in hand, assemble the collage. The deliverables are a
self-contained `.svg`, its `.png` render, and the build script that made them.

### THE INVARIANTS

Four things must be true of the finished piece. They are properties of the artifact, not of any
particular toolchain, and they are what everything else here is in service of:

1. **Every fragment is open-licensed or user-supplied**, and logged in `attributions.md`.
2. **The `.svg` is self-contained and renderer-independent** — the same picture in any engine.
   SVG's own effect primitives render *completely differently* across renderers, so none of them
   survive into the shipped file: every raster effect is baked into the fragments beforehand, and
   the SVG carries only embedded images, plain geometry and outlined text. Don't assume this
   holds — render in a second engine and diff.
3. **Text is vectorized, and set in the face you asked for.** Both halves matter. Font resolution
   fails *silently*: an unavailable family is substituted with no error, and once outlined nothing
   downstream can detect it — a render compared against itself will pass happily. Verify the family
   resolves before converting to paths.
4. **The build is re-runnable and parametric.** One legible script, shipped alongside the piece,
   that regenerates it from the folder it ships in — fragment preparation included, depending on
   nothing left behind in a scratch directory. Everything a person would want to nudge is a named
   value they can find and change, not a number buried in a call. `philosophy.md` records the why;
   the script records the how, and is what lets the piece be *edited* rather than remade. A collage
   you cannot regenerate or adjust is a dead end.

### THE WORK

Not a fixed pipeline — reach for what the piece needs. The philosophy already decided the edge
language, the reconciling move, what the stacking means and how type is set; execution is where
those get applied rather than reconsidered. Three things only come up here:

- **Build what the philosophy asked for.** Where it named an edge or a treatment your tools don't
  cover, make that one — the register was decided on purpose, and a piece assembled from the
  nearest available approximations ends up looking like whatever was easy.
- **Fray a knockout's contour.** A silhouette lifted with a machine-clean outline reads as a
  die-stamp, not as something cut by hand — the one place a cutout betrays itself.
- **The treatment must reach every fragment identically.** It is the mechanism that makes a dozen
  archives one object, so a single fragment that escaped it is visible immediately. This is the
  thing most likely to slip when fragments are prepared in batches.

### ORDER

Usually: prepare fragments, then compose. Two things disturb that, and both are cheaper to know
than to discover:

- **A treatment that reads a fragment's position must wait for the layout.** If the reconciling
  move samples a field across the finished sheet — an ageing that varies with where a fragment
  sits — then nothing can be treated until the composition is settled. Compute the layout first,
  then prepare each fragment for the place it lands.
- **That also makes repetition expensive.** Placing one cut fragment several times at different
  scales is normally free, because the payload is stored once. A position-dependent treatment
  removes that saving entirely: every placement needs its own treated copy. Decide which of the two
  you want before building the pool.

Then render, prove the `.svg` and `.png` are the same picture, and run the self-check below.

**`references/pipeline-recipes.md` has the commands and the traps** — fonts, text-to-path, the
portability check, querying archives and validating what comes back, the raster recipes, SVG
assembly, and the shape of the build script. Read it rather than re-deriving any of it; each entry
is there because it cost something to learn.

### THE COLLAGE SELF-CHECK — RUN IT BEFORE YOU CALL THE PIECE DONE

An internal gate, not a report. **Look at the rendered `.png`** and answer these for yourself,
naming specific fragments — vague answers mean you didn't look. Where the philosophy named an
override, the piece answers to the override instead, and you must be able to point at the
sentence. Then act on the result; none of this goes to the user.

1. **Occlusion** — name two fragments where one visibly sits in front of the other.
   *Override: a philosophy committed to a grid, or to isolated fragments.*
2. **Escape** — name the fragment whose silhouette breaks its bounding box or the canvas edge.
   A canvas-edge bleed satisfies the letter of this and is the cheap answer; if the pool held
   liftable material and none of it was cut out, that is drift rather than a decision. The
   sourcing survey already answered whether it did, so answer this from that evidence.
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
re-render. A reason constructed after the fact is not an override; it is the drift talking. The
exception is a philosophy constraint the material has actually disproved: amend it in
`philosophy.md`, with the reason, and re-check against the amended text. Writing it down is what
separates an amendment from an excuse — it is what made the constraint binding to begin with.

Iterate here until it passes. Ship the piece, not the checklist.

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

**Work with what is already on the page.** How a piece *reads* is a coherence problem, and reaching
for one more image treats it as a content problem — the fragments are rarely what's missing. (A
count that came out thin is a different fault, caught at the self-check and fixed before you arrive
here.) Ask what would make the present material read as a single made object — usually:

- **Registration** — fragments that nearly align but don't.
- **Reconciliation** — a fragment still carrying its original colour temperature.
- **Light** — a shadow falling the wrong way. Every shadow answers to one lamp.
- **Edge** — a tear reading as an effect rather than as paper; recut with a different seed.

Adjust the build script, re-render, re-run the self-check.
