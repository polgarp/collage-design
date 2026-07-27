#!/usr/bin/env python3
"""
survey.py — look at the material before composing with it.

Two jobs, both about replacing a judgement with a measurement:

  1. A CONTACT SHEET of everything in sources/, so the pool can be seen at once. Composition
     decisions track looking at the material more than anything else in a run, and a folder
     of filenames is not looking at it.

  2. MEASUREMENTS the eye is bad at. "Flat/neutral ground" is a border-variance question and
     "cuttable subject" is a subject/ground contrast question — both are numbers, and both
     predict whether knockout.py will work before you spend three attempts finding out.

Usage:
    survey.py sources/*.jpg                          # the table
    survey.py sources/*.jpg --sheet contact.png      # + a labelled contact sheet
    survey.py sources/*.jpg --find-patch 900 900     # best flat-colour crops in each source

`--find-patch` is the third job, and it generalises past colour. A philosophy dimension
written precisely enough can be turned into a SELECTOR: "colour as ingredient, never colour
as scene" means "no structure", structure is edges, edges are variance — so ranking candidate
crops by saturation minus luminance-variance finds fields of pigment and rejects anything
with a subject in it. The variance penalty is the load-bearing term; a scorer that rewards
only saturation and hue-uniformity picks whole flowers, because a flower is both.

When a dimension can be written as a score, the machine picks better crops than the eye does,
and it looks at the whole source at once.
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from knockout import sample_bg, separation      # same measurements the knockout tool uses

# ---- measurement ----

def border_std(arr):
    """How even the ground is around the edge — the flat/neutral question, measured.
    High means the border is not one ground at all (a busy photograph, or a mount)."""
    h, w, _ = arr.shape
    b = max(2, min(h, w) // 40)
    ring = np.concatenate([arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
                           arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3)])
    return float(ring.std(axis=0).mean())

def saturation(arr):
    mx, mn = arr.max(-1), arr.min(-1)
    return float(np.mean((mx - mn) / np.maximum(mx, 1e-6)))

def measure(path, long_edge=700):
    im = Image.open(path)
    full = im.size
    im = im.convert("RGB")
    if max(im.size) > long_edge:                 # measuring a thumbnail is enough and quick
        im.thumbnail((long_edge, long_edge), Image.LANCZOS)
    arr = np.asarray(im).astype(float)
    bg = sample_bg(arr)
    flat, sep = border_std(arr), separation(arr, bg)
    if sep < 40:      verdict = "NO — subject at ground value"
    elif flat > 26:   verdict = "no — ground is busy"
    elif sep < 80:    verdict = "marginal"
    else:             verdict = "liftable"
    return dict(path=path, size=full, mp=full[0] * full[1] / 1e6, flat=flat,
                sep=sep, sat=saturation(arr), bg=bg.astype(int).tolist(), verdict=verdict)

# ---- patch scoring (sliding window over a thumbnail, via summed-area tables) ----

def _integral(a):
    return np.pad(a, ((1, 0), (1, 0))).cumsum(0).cumsum(1)

def _win_mean(a, kh, kw):
    I = _integral(a)
    s = I[kh:, kw:] - I[:-kh, kw:] - I[kh:, :-kw] + I[:-kh, :-kw]
    return s / (kh * kw)

def score_patches(path, pw, ph, top=3, margin=0.06, long_edge=420):
    """Rank candidate crops as fields of colour rather than pictures of things.

        score = 2.0*saturation − 2.4*luminance_std − 1.6*per-channel chroma_std

    Margin exclusion keeps the window off the corners, where the photographer's logo and
    the plate's caption live."""
    im = Image.open(path).convert("RGB")
    W, H = im.size
    sc = min(1.0, long_edge / max(W, H))
    t = im.resize((max(8, int(W * sc)), max(8, int(H * sc))), Image.LANCZOS)
    a = np.asarray(t).astype(float)
    kh, kw = max(4, int(ph * sc)), max(4, int(pw * sc))
    if kh >= a.shape[0] or kw >= a.shape[1]:
        return []

    lum = a @ np.array([0.2126, 0.7152, 0.0722])
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)

    m_l = _win_mean(lum, kh, kw)
    v_l = np.maximum(_win_mean(lum ** 2, kh, kw) - m_l ** 2, 0)
    m_s = _win_mean(sat, kh, kw)
    chroma = np.zeros_like(m_l)
    for c in range(3):
        m_c = _win_mean(a[..., c], kh, kw)
        chroma += np.sqrt(np.maximum(_win_mean(a[..., c] ** 2, kh, kw) - m_c ** 2, 0))
    score = 2.0 * m_s - 2.4 * (np.sqrt(v_l) / 255.0) - 1.6 * (chroma / 3 / 255.0)

    my, mx_ = int(a.shape[0] * margin), int(a.shape[1] * margin)
    score[:my, :] = score[-my - 1:, :] = -9e9
    score[:, :mx_] = score[:, -mx_ - 1:] = -9e9

    out = []
    for _ in range(top):
        y, x = np.unravel_index(int(np.argmax(score)), score.shape)
        if score[y, x] < -1e8:
            break
        out.append((float(score[y, x]), int(x / sc), int(y / sc)))
        score[max(0, y - kh):y + kh, max(0, x - kw):x + kw] = -9e9   # don't return the same field twice
    return out

# ---- contact sheet ----

def _font(px):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, px)
        except OSError:
            continue
    return ImageFont.load_default()

def contact_sheet(rows, out_path, cols=5, cell=380):
    lab = 34
    n = len(rows)
    r = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, r * (cell + lab)), (26, 26, 28))
    d = ImageDraw.Draw(sheet)
    f = _font(15)
    for i, m in enumerate(rows):
        cx, cy = (i % cols) * cell, (i // cols) * (cell + lab)
        im = Image.open(m["path"]).convert("RGB")
        im.thumbnail((cell - 12, cell - 12), Image.LANCZOS)
        sheet.paste(im, (cx + (cell - im.width) // 2, cy + (cell - im.height) // 2))
        name = os.path.basename(m["path"])
        d.text((cx + 8, cy + cell + 2), f"{i + 1}. {name[:34]}", font=f, fill=(232, 226, 208))
        d.text((cx + 8, cy + cell + 18),
               f"{m['size'][0]}x{m['size'][1]}  {m['verdict']}", font=f, fill=(150, 150, 156))
    sheet.save(out_path)
    return out_path

def main():
    ap = argparse.ArgumentParser(description="Look at the source pool, and measure it.")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--sheet", help="write a labelled contact sheet here")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--cell", type=int, default=380)
    ap.add_argument("--find-patch", dest="patch", nargs=2, type=int, metavar=("W", "H"),
                    help="rank flat-colour crops of this size in each source")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--margin", type=float, default=0.06,
                    help="fraction of each edge excluded from patch search (logos, captions)")
    a = ap.parse_args()

    rows = []
    print(f"{'#':>3}  {'file':<30} {'size':>11} {'MP':>5} {'ground':>7} {'contrast':>9} "
          f"{'sat':>5}  verdict")
    for i, p in enumerate(a.images, 1):
        try:
            m = measure(p)
        except Exception as e:                   # a stray .txt or a 404-HTML "download"
            print(f"{i:>3}  {os.path.basename(p):<30} !! unreadable: {e}")
            continue
        rows.append(m)
        print(f"{i:>3}  {os.path.basename(p)[:30]:<30} {m['size'][0]:>5}x{m['size'][1]:<5} "
              f"{m['mp']:>5.1f} {m['flat']:>7.1f} {m['sep']:>9.0f} {m['sat']:>5.2f}  "
              f"{m['verdict']}")

    if a.patch:
        pw, ph = a.patch
        print(f"\nflattest {pw}x{ph} fields (paste straight into magick -crop):")
        for m in rows:
            for s, x, y in score_patches(m["path"], pw, ph, a.top, a.margin):
                print(f"  {os.path.basename(m['path'])[:30]:<30} score {s:+.3f}   "
                      f"-crop {pw}x{ph}+{x}+{y}")

    if a.sheet and rows:
        print(f"\ncontact sheet -> {contact_sheet(rows, a.sheet, a.cols, a.cell)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
