#!/usr/bin/env python3
"""
survey.py — look at the material before composing with it.

Three jobs, all about replacing a judgement with a measurement:

  1. A CONTACT SHEET of everything in sources/, so the pool can be seen at once. Composition
     decisions track looking at the material more than anything else in a run, and a folder
     of filenames is not looking at it.

  2. CAN A SUBJECT ACTUALLY BE CUT OUT OF THIS? Not predicted from input statistics — this
     runs the real matte from knockout.py across a tolerance sweep and measures the SHAPE of
     what comes back. See `--knockout-sheet` to look at the silhouettes rather than trust the
     word.

  3. FLAT-COLOUR CROPS (`--find-patch`), for material used as pigment rather than as picture.

WHY THE VERDICT IS COMPUTED THE EXPENSIVE WAY

This used to guess from two input statistics: border variance ("is there one flat ground?")
and subject/ground contrast ("is there a subject to lift?"). Measured against real pools,
that guess was wrong in both directions and wrong often enough to change what got made:

  * FALSE POSITIVES. On archive scans the border is uniform because it is a SCAN FRAME or a
    mount, not a studio sweep — and something in the frame is always far from it, because
    photographs contain things. Both terms satisfied, verdict "liftable", and the knockout
    hands back the whole photograph as a rectangle with its black frame trimmed. On one
    290-file pool this rated 111 sources liftable; the piece built from it shipped ONE
    silhouette.
  * FALSE NEGATIVES. Border variance is measured across the whole file, so gridded plates,
    mounted prints and anything with a caption strip read as "ground is busy" even when the
    crop you actually intend to cut is clean. A plate is not a fragment — measure the crop
    (`--grid`, `--crop`).

An agent that tries three confident "liftable" sources, gets three rectangles, and falls
back to torn rectangles for the rest of the piece is behaving reasonably. It was handed a
predictor that did not predict. Running the actual operation costs a few seconds per source
and cannot disagree with the tool it is predicting.

Usage:
    survey.py sources/*.jpg                           # the table
    survey.py sources/*.jpg --sheet contact.png       # + a labelled contact sheet
    survey.py sources/*.jpg --knockout-sheet ko.png   # + the mattes, to look at
    survey.py plate.jpg --grid 4x5                    # measure each cell of a gridded plate
    survey.py plate.jpg --crop 900x900+1200+800       # measure one specific crop
    survey.py sources/*.jpg --liftable                # only the ones worth cutting
    survey.py sources/*.jpg --find-patch 900 900      # best flat-colour crops in each source

`--find-patch` is the third job, and it generalises past colour. A philosophy dimension
written precisely enough can be turned into a SELECTOR: "colour as ingredient, never colour
as scene" means "no structure", structure is edges, edges are variance — so ranking candidate
crops by saturation minus luminance-variance finds fields of pigment and rejects anything
with a subject in it. The variance penalty is the load-bearing term; a scorer that rewards
only saturation and hue-uniformity picks whole flowers, because a flower is both.

When a dimension can be written as a score, the machine picks better crops than the eye does,
and it looks at the whole source at once.
"""
import argparse, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The tool the verdict predicts. ASSESS_EDGE comes from there too — the assessment
# resolution is knockout.py's business, so that `survey.py` and `knockout.py --report`
# cannot reach different verdicts about the same file (they used to).
from knockout import ASSESS_EDGE, assess, matte, sample_bg

# ---- measurement ----

def border_std(arr):
    """How even the ground is around the edge. Reported for context only — it is NOT the
    verdict any more, because a uniform border is usually a scan frame (see module docs)."""
    h, w, _ = arr.shape
    b = max(2, min(h, w) // 40)
    ring = np.concatenate([arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
                           arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3)])
    return float(ring.std(axis=0).mean())

def saturation(arr):
    mx, mn = arr.max(-1), arr.min(-1)
    return float(np.mean((mx - mn) / np.maximum(mx, 1e-6)))

def _thumb(im, edge):
    im = im.convert("RGB")
    if max(im.size) > edge:
        im = im.copy(); im.thumbnail((edge, edge), Image.LANCZOS)
    return np.asarray(im).astype(float)

def measure(path, im=None, label=None, edge=ASSESS_EDGE, glob=False):
    """Measure one frame — a whole file, or a crop of one if `im` is supplied."""
    if im is None:
        im = Image.open(path)
    full = im.size
    arr = _thumb(im, edge)
    m = assess(arr, glob=glob)
    m.update(path=path, label=label or os.path.basename(path), size=full,
             mp=full[0] * full[1] / 1e6, flat=border_std(arr), sat=saturation(arr))
    return m

def parse_crop(s):
    """'900x900+1200+800' -> (w, h, x, y). Same spelling as ImageMagick's -crop."""
    m = re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", s)
    if not m:
        raise argparse.ArgumentTypeError(f"crop must look like WxH+X+Y, got {s!r}")
    return tuple(int(g) for g in m.groups())

def grid_cells(im, rows, cols, margin=0.02):
    """Split a plate into its cells. A gridded source — a Muybridge plate, a contact sheet,
    a sheet of labels — is measured wrong as a whole file every time: the plate's surround is
    a flat ground and its cells are not, so the file-level verdict describes a frame nobody
    is going to cut. The small inset drops the rules between cells."""
    W, H = im.size
    cw, ch = W / cols, H / rows
    mx, my = cw * margin, ch * margin
    for r in range(rows):
        for c in range(cols):
            box = (int(c * cw + mx), int(r * ch + my),
                   int((c + 1) * cw - mx), int((r + 1) * ch - my))
            yield f"r{r + 1}c{c + 1}", im.crop(box), box

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

# ---- sheets ----

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
        d.text((cx + 8, cy + cell + 2), f"{i + 1}. {m['label'][:34]}", font=f, fill=(232, 226, 208))
        d.text((cx + 8, cy + cell + 18),
               f"{m['size'][0]}x{m['size'][1]}  {m['verdict'][:30]}", font=f, fill=(150, 150, 156))
    sheet.save(out_path)
    return out_path

def _checker(w, h, sq=12):
    a = np.indices((h, w)).sum(0) // sq % 2
    return Image.fromarray((np.where(a, 210, 170)).astype("uint8")).convert("RGB")

def knockout_sheet(rows, out_path, cols=5, cell=380, edge=ASSESS_EDGE, glob=False):
    """Show the actual matte for each source, over a checkerboard, labelled with the numbers.

    The point of this sheet is that a knockout failure is invisible in a word. "liftable"
    and "no — whole frame" look identical in a table until you see that one of them is a
    rectangle. Composition is decided by looking at the material; so is cuttability."""
    lab = 48
    n = len(rows)
    r = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, r * (cell + lab)), (26, 26, 28))
    d = ImageDraw.Draw(sheet)
    f, fs = _font(15), _font(13)
    for i, m in enumerate(rows):
        cx, cy = (i % cols) * cell, (i // cols) * (cell + lab)
        im = Image.open(m["path"]).convert("RGB")
        if m.get("box"):
            im = im.crop(m["box"])
        if m.get("shave"):                 # reproduce exactly what assess() measured —
            w, h = im.size                 # a sheet showing a different matte from the
            dx = int(w * m["shave"] / 100) # verdict is worse than no sheet at all
            dy = int(h * m["shave"] / 100)
            im = im.crop((dx, dy, w - dx, h - dy))
        im.thumbnail((cell - 12, cell - 12), Image.LANCZOS)
        arr = np.asarray(im).astype(float)
        a = matte(arr, sample_bg(arr), m["tol"], glob)
        cut = Image.merge("RGBA", (*im.split(), Image.fromarray(a, "L")))
        back = _checker(im.width, im.height)
        back.paste(cut, (0, 0), cut)
        sheet.paste(back, (cx + (cell - im.width) // 2, cy + (cell - im.height) // 2))
        ok = m["verdict"].startswith("liftable")
        d.text((cx + 8, cy + cell + 2), f"{i + 1}. {m['label'][:34]}", font=f,
               fill=(232, 226, 208))
        d.text((cx + 8, cy + cell + 18), m["verdict"][:44], font=fs,
               fill=(150, 220, 150) if ok else (220, 140, 130))
        d.text((cx + 8, cy + cell + 33),
               f"kept {m['kept']:.0f}%  solidity {m['solidity']:.2f}  tol {m['tol']:g}",
               font=fs, fill=(150, 150, 156))
    sheet.save(out_path)
    return out_path

# ---- cli ----

HDR = (f"{'#':>3}  {'file':<34} {'size':>11} {'MP':>5} {'kept':>5} {'solid':>6} "
       f"{'span':>5} {'tol':>4} {'sat':>5}  verdict")

def _row(i, m):
    return (f"{i:>3}  {m['label'][:34]:<34} {m['size'][0]:>5}x{m['size'][1]:<5} "
            f"{m['mp']:>5.1f} {m['kept']:>4.0f}% {m['solidity']:>6.2f} {m['span']:>4.0%} "
            f"{m['tol']:>4g} {m['sat']:>5.2f}  {m['verdict']}")

def main():
    ap = argparse.ArgumentParser(description="Look at the source pool, and measure it.")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--sheet", help="write a labelled contact sheet here")
    ap.add_argument("--knockout-sheet", dest="ko_sheet",
                    help="write a sheet of the actual mattes, over a checkerboard")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--cell", type=int, default=380)
    ap.add_argument("--grid", help="measure each cell of a gridded plate, e.g. 4x5")
    ap.add_argument("--crop", type=parse_crop, help="measure one crop only: WxH+X+Y")
    ap.add_argument("--global", dest="glob", action="store_true",
                    help="assess with global keying (scattered line-art, specimen plates)")
    ap.add_argument("--liftable", action="store_true", help="print only liftable rows")
    ap.add_argument("--find-patch", dest="patch", nargs=2, type=int, metavar=("W", "H"),
                    help="rank flat-colour crops of this size in each source")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--margin", type=float, default=0.06,
                    help="fraction of each edge excluded from patch search (logos, captions)")
    a = ap.parse_args()

    if a.grid:
        try:
            rows_n, cols_n = (int(x) for x in a.grid.lower().split("x"))
        except ValueError:
            ap.error("--grid must look like ROWSxCOLS, e.g. 4x5")

    rows = []
    print(HDR)
    i = 0
    for p in a.images:
        try:
            im = Image.open(p)
            if a.crop:
                w, h, x, y = a.crop
                frames = [(f"{os.path.basename(p)}[{x}+{y}]",
                           im.crop((x, y, x + w, y + h)), (x, y, x + w, y + h))]
            elif a.grid:
                frames = [(f"{os.path.basename(p)[:22]}:{tag}", sub, box)
                          for tag, sub, box in grid_cells(im, rows_n, cols_n)]
            else:
                frames = [(os.path.basename(p), im, None)]

            for label, sub, box in frames:
                m = measure(p, im=sub, label=label, glob=a.glob)
                m["box"] = box
                if a.liftable and not m["verdict"].startswith("liftable"):
                    continue
                rows.append(m); i += 1
                print(_row(i, m))
        except Exception as e:                   # a stray .txt or a 404-HTML "download"
            i += 1
            print(f"{i:>3}  {os.path.basename(p):<34} !! unreadable: {e}")
            continue

    lift = sum(r["verdict"].startswith("liftable") for r in rows)
    print(f"\n{lift} of {len(rows)} frames can actually be cut out.")
    if rows and not lift:
        print("  Nothing here is a knockout. That is a normal answer for documentary and\n"
              "  press photography — but check the framing before accepting it: try --grid on\n"
              "  any gridded plate, and --crop on a source whose subject sits clear of the\n"
              "  clutter. Otherwise these are torn rectangles, and the piece needs its escape\n"
              "  from a fragment bleeding off the canvas edge instead.")

    if a.patch:
        pw, ph = a.patch
        print(f"\nflattest {pw}x{ph} fields (paste straight into magick -crop):")
        for m in rows:
            for s, x, y in score_patches(m["path"], pw, ph, a.top, a.margin):
                print(f"  {m['label'][:30]:<30} score {s:+.3f}   -crop {pw}x{ph}+{x}+{y}")

    if a.sheet and rows:
        print(f"\ncontact sheet -> {contact_sheet(rows, a.sheet, a.cols, a.cell)}")
    if a.ko_sheet and rows:
        print(f"knockout sheet -> "
              f"{knockout_sheet(rows, a.ko_sheet, a.cols, a.cell, glob=a.glob)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
