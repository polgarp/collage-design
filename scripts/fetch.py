#!/usr/bin/env python3
"""
fetch.py — pull source imagery from open archives, safely and politely.

WHY THIS IS A TOOL AND NOT A LOOP YOU WRITE EACH TIME

Every correctness bug in a two-piece test run lived in a hand-rolled downloader, and they
were written three times because each piece re-derived one. They are all invisible failures —
the log says success and the pool is quietly wrong:

  * FILENAME COLLISIONS. Naming files after the archive's TITLE collapses duplicates: a pull
    reported "179 downloaded, 0 failed" and left 168 files on disk, because eleven labels
    shared a subject name. Losing the images is the small half. The download log and the
    directory then disagree, so `attributions.md` credits surviving files to the wrong source
    rows — a licensing document going quietly wrong. Files are keyed on the archive's own
    IDENTIFIER here, and the count is asserted at the end.
  * A THROTTLE LOOKS LIKE A DOWNLOAD. An HTTP 429 body writes to disk as a nonzero-size
    non-image, indistinguishable from the stale-URL failure, so an impatient loop produces a
    corrupt pool rather than a fast one. Backoff is exponential and honours Retry-After.
  * MULTI-FRAME FILES. Some Commons files are animated GIFs whatever extension they were
    saved under (Muybridge sequences especially). `identify` confirms they are real images,
    because they are — they are just more than one. `magick in.jpg out.png` on one writes
    `out-0.png` and never `out.png`, and the build dies two stages downstream with a
    FileNotFoundError naming nothing. These are flagged at fetch time; append `[0]` to the
    input in Stage A.

POLITENESS IS A FEATURE. DO NOT OPTIMISE IT AWAY.

These archives — Wikimedia Commons, the Library of Congress, the Internet Archive — are
free, donation-funded, and the entire reason this skill can produce publishable work. The
delay floor below is not tuning; it is the cost of being allowed to keep doing this.

  * Hammering them imposes a cost on the commons to save you a few minutes.
  * It is self-defeating: past the rate limit you get 429 bodies that look like successful
    downloads, so you go faster and end up with a broken pool. One real run was throttled at
    file 132 of 179 at 0.4 s between requests.
  * Sustained abuse gets the user agent or IP blocked, which breaks the next person's run.

The speedup you want is on the compute side — `cut.py`/`treat.py --jobs` — which is
separable and where all the real time is. Leave the network alone.

USAGE

    fetch.py --out sources/ --json items.json
    fetch.py --out sources/ --prefix lab_ URL [URL ...]
    fetch.py --out sources/ --json items.json --attributions attributions.md

`--json` takes a list of records, which is the shape an archive API already returns:

    [{"url": "https://…/file.jpg",      # required
      "id": "ggbain.12345",             # required-ish: the archive's identifier. Falls back
                                        #   to a hash of the URL, which is collision-safe but
                                        #   unreadable — pass the real one.
      "title": "…", "creator": "…", "license": "PD", "source": "https://…/item/…"}]

Everything but `url` is optional and is carried into the attributions table verbatim.
"""
import argparse, hashlib, json, os, re, sys, time, urllib.error, urllib.request

# Wikimedia's etiquette asks for a descriptive agent with contact details. Identify the tool
# and leave a way to be told to stop; an anonymous scraper is the thing archives block.
UA = ("collage-design/1.0 (Claude skill for open-licensed collage art; "
      "https://github.com/polgarp/collage-design)")

# Floor on the gap between requests. Deliberately not exposed as "0" — see the module docs.
MIN_DELAY = 0.5
MAX_TRIES = 5

IMAGE_EXT = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "gif": "gif",
             "tiff": "tif", "webp": "webp"}

def slug(s, n=60):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", (s or "").lower())).strip("_")[:n]

def key_for(rec):
    """The filename stem. The archive's identifier if we have one, else a hash of the URL.

    Never the title: titles are not unique and collide silently. A title is still used as a
    readable PREFIX, but the identifier is what guarantees distinctness."""
    ident = rec.get("id") or hashlib.sha1(rec["url"].encode()).hexdigest()[:12]
    title = slug(rec.get("title"), 48)
    return f"{title}_{slug(str(ident), 24)}" if title else slug(str(ident), 32)

def get(url, tries=MAX_TRIES):
    """Fetch bytes, backing off exponentially on throttle and transient server errors."""
    delay = 1.0
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), r.headers.get_content_type()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 500, 502, 504) and attempt < tries:
                # Retry-After is authoritative when present; the archive is telling you the
                # number, and guessing a smaller one is how a pull gets blocked outright.
                wait = float(e.headers.get("Retry-After") or 0) or delay
                print(f"    HTTP {e.code}, waiting {wait:.0f}s (attempt {attempt}/{tries})",
                      file=sys.stderr)
                time.sleep(wait)
                delay = min(delay * 2, 60)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < tries:
                print(f"    {e}, retrying in {delay:.0f}s", file=sys.stderr)
                time.sleep(delay); delay = min(delay * 2, 60)
                continue
            raise
    raise RuntimeError(f"gave up after {tries} attempts: {url}")

def validate(path):
    """Confirm the bytes on disk are a real, usable image. Returns (format, n_frames).

    A 404 page and a throttle body are both nonzero-size non-images, so 'the file exists and
    has bytes' proves nothing. Frame count matters separately — see the module docs."""
    from PIL import Image
    with Image.open(path) as im:
        im.verify()                                  # catches truncated / non-image bytes
    with Image.open(path) as im:
        return im.format, getattr(im, "n_frames", 1)

def fetch_one(rec, outdir, prefix, delay):
    url = rec["url"]
    stem = prefix + key_for(rec)
    tmp = os.path.join(outdir, stem + ".part")
    data, ctype = get(url)
    ext = IMAGE_EXT.get((ctype or "").split("/")[-1].lower()) \
        or IMAGE_EXT.get(os.path.splitext(url.split("?")[0])[1].lstrip(".").lower()) or "jpg"
    dest = os.path.join(outdir, f"{stem}.{ext}")

    if os.path.exists(dest):
        # Not an error: re-running a pull should be cheap and idempotent. Wiping sources/ and
        # re-fetching 179 files to recover 11 missing ones cost four minutes in a real run.
        return dest, "exists", None
    with open(tmp, "wb") as fh:
        fh.write(data)
    try:
        fmt, frames = validate(tmp)
    except Exception as e:
        os.remove(tmp)
        raise RuntimeError(f"not a usable image ({e}) — likely a 404 page or a throttle body")
    os.replace(tmp, dest)
    time.sleep(max(delay, MIN_DELAY))
    return dest, fmt, frames

def attributions_table(rows):
    out = ["| File | Title | Creator | Licence | Source |", "|---|---|---|---|---|"]
    for r in rows:
        out.append("| `{}` | {} | {} | {} | {} |".format(
            os.path.basename(r["file"]), r.get("title", "") or "—",
            r.get("creator", "") or "—", r.get("license", "") or "**UNVERIFIED**",
            f"<{r['source']}>" if r.get("source") else f"<{r['url']}>"))
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser(description="Fetch open-licensed sources, safely and politely.")
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--out", required=True, help="directory for pristine originals")
    ap.add_argument("--json", dest="jsonfile", help="file of records: url, id, title, creator, "
                                                    "license, source")
    ap.add_argument("--prefix", default="", help="prepended to every filename, e.g. 'lab_'")
    ap.add_argument("--delay", type=float, default=1.0,
                    help=f"seconds between requests (floor {MIN_DELAY}; read the module docs "
                         f"before reaching for this)")
    ap.add_argument("--attributions", help="write the source table here (Markdown)")
    a = ap.parse_args()

    recs = []
    if a.jsonfile:
        with open(a.jsonfile) as fh:
            recs += json.load(fh)
    recs += [{"url": u} for u in a.urls]
    if not recs:
        ap.error("nothing to fetch: pass URLs or --json")

    os.makedirs(a.out, exist_ok=True)
    before = {f for f in os.listdir(a.out) if not f.endswith(".part")}

    # A collision check BEFORE the network, so it is a one-line fix rather than a re-pull.
    stems = {}
    for r in recs:
        stems.setdefault(a.prefix + key_for(r), []).append(r["url"])
    clashes = {k: v for k, v in stems.items() if len(v) > 1}
    if clashes:
        for k, v in list(clashes.items())[:5]:
            print(f"  COLLISION: {k} <- {len(v)} URLs", file=sys.stderr)
        sys.exit(f"{len(clashes)} filename collisions. Records need distinct 'id' values —\n"
                 f"the archive's identifier, not the title. Nothing was downloaded.")

    ok, failed, multi = [], [], []
    for i, rec in enumerate(recs, 1):
        try:
            dest, fmt, frames = fetch_one(rec, a.out, a.prefix, a.delay)
            row = dict(rec, file=dest)
            ok.append(row)
            note = ""
            if frames and frames > 1:
                multi.append(dest)
                note = f"  ** {frames} FRAMES — use '{os.path.basename(dest)}[0]' in Stage A **"
            print(f"[{i}/{len(recs)}] {os.path.basename(dest)} ({fmt}){note}")
        except Exception as e:
            failed.append((rec.get("url"), str(e)))
            print(f"[{i}/{len(recs)}] FAILED {rec.get('url')}: {e}", file=sys.stderr)

    after = {f for f in os.listdir(a.out) if not f.endswith(".part")}
    written = len(after - before)

    print(f"\n{len(ok)} ok, {len(failed)} failed, {written} new files on disk")
    if multi:
        print(f"{len(multi)} multi-frame file(s): append [0] to the input in Stage A, or the "
              f"build fails\ntwo stages later with a FileNotFoundError that names nothing.")

    # The assert the notes asked for. Reported-vs-on-disk is the check that would have caught
    # the silent overwrite, and it is worth failing the run over: every downstream artefact,
    # attributions.md included, is keyed on this correspondence.
    fresh = [r for r in ok if os.path.basename(r["file"]) not in before]
    if written != len(fresh):
        sys.exit(f"MISMATCH: reported {len(fresh)} new downloads but {written} new files "
                 f"appeared.\nSomething overwrote something. Do not trust attributions.md "
                 f"from this run.")

    if a.attributions and ok:
        with open(a.attributions, "w") as fh:
            fh.write("# Attributions\n\n" + attributions_table(ok) + "\n")
        print(f"attributions -> {a.attributions}")
        if any(not r.get("license") for r in ok):
            print("  NOTE: some rows have no licence. Fill them in before shipping — an\n"
                  "  unverified licence is not a permissive one.", file=sys.stderr)
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
