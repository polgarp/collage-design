# collage-design

A Claude skill that makes **cut-and-layer collage**: it goes and finds real, open-licensed
photographs and printed material, cuts them, unifies them into one palette, and composes a
finished art piece as a portable `.svg` plus its `.png`.

It writes a *collage philosophy* first — an aesthetic movement invented for the brief, deciding
where the material comes from, how it is torn or knife-cut, how it stacks, and what treatment
reconciles a dozen clashing archives into one object — then sources against that philosophy and
composes to it.

## Install

```bash
git clone https://github.com/polgarp/collage-design.git ~/.claude/skills/collage-design
~/.claude/skills/collage-design/scripts/check_deps.sh
```

## Requirements

- **Real source imagery** — either web access, so it can pull from open-licensed archives, or a
  folder of your own you point it at. It works from both, and stops rather than inventing pictures
  if it has neither.
- **ImageMagick, Inkscape, librsvg, fontconfig, Python + Pillow + NumPy.** `check_deps.sh` prints
  the install line for anything missing. No ML dependencies.
- **Time and tokens.** Roughly 100–150k tokens for one piece, and a long run. Output is a 5–10 MB
  `.svg` and a 10–20 MB `.png` — the fragments are embedded rather than linked, which is what makes
  the `.svg` self-contained. This is not a thirty-second tool.

## What you get

| | |
|---|---|
| `philosophy.md` | The aesthetic movement invented for the piece |
| `sources/` | Original downloads, unmodified |
| `attributions.md` | Every asset with URL, creator, licence — and what those licences mean for reusing the result |
| `<piece>.svg` / `.png` | Self-contained and filter-free / the shipping render |
| `build_*.py` | Parametric build script, so the piece can be edited rather than remade |

Three things are measured rather than assumed: `check_render.sh` proves the `.svg` and `.png` are
the same picture in any renderer, `survey.py` scores each source for whether a subject can actually
be cut out of it, and an internal self-check on the render — occlusion, frame-breaking cutout,
treatment coverage, fragment count and scale spread — drives iteration before anything is called
done.

## Extending it

`cut.py` ships seven edge styles and `treat.py` five treatments, but both are built around one
extension point, a drop-in file, or importing the plumbing — and both pass custom parameters
through, so an invented style is a first-class citizen rather than a squatter on `--radius`:

```bash
cut.py   --style-file my_edge.py  --param fade=0.45 in.jpg out.png   # def mask(w, h, p, rng)
treat.py --style-file my_treat.py --param warmth=0.6 in.png out.png  # def treat(rgb, p, rng)
cut.py   --sticker 16 treated.png sticker.png     # die-cut keyline following the silhouette
```

`svgkit.py` ships no layout presets at all, composition has to be invented per piece, so the
library only handles embed-once, placement, renderer-safe shadows, text, and clipping a group of
fragments into a container silhouette.

## Licensing

Apache 2.0 (`LICENSE.txt`). Derived from Anthropic's `canvas-design` — see `NOTICE.md`.

**Artwork you make with it is a separate question.** A collage is a derivative of every fragment
in it, so the most restrictive source sets the terms for the whole piece. The skill prefers public
domain / CC0, flags CC BY as needing credit, warns that **CC BY-SA is viral** and makes your
finished artwork copyleft, and treats CC ND as disqualifying. That reasoning ships in every
`attributions.md`.
