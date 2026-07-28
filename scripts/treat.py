#!/usr/bin/env python3
"""
treat.py — unify a fragment's colour/tone for collage ("the reconciling treatment").

Disparate sources arrive in clashing colour and light; a treatment applied IDENTICALLY to every
fragment (same style, same seed) is what turns a pile into one object. Operates on RGB and
preserves alpha, so it works on cutouts. PIL/numpy only.

Usage:
    treat.py --style STYLE [options] IN OUT.png
    treat.py --list

Styles — worked examples of ONE pattern, not a closed menu:
  duotone     luminance → two-colour ramp     (--dark HEX --light HEX)
  tritone     luminance → three-stop ramp     (--dark --mid --light HEX)
  splittone   tint shadows vs highlights      (--dark shadow, --light highlight)
  desaturate  toward grey                      (--amount 0..1)
  grain       seeded film grain                (--amount, --seed)

Invent a treatment — don't force a preset. A treatment is a function
(rgb float array HxWx3, params, rng) → rgb float array. Make your own and reuse the plumbing:
  • drop-in:  treat.py --style-file my_treat.py in.png out.png   (file defines treat(rgb, p, rng))
  • import:   from treat import load, save_rgb, lum   (do your own array math)

A custom treatment takes its OWN parameters with --param KEY=VALUE (repeatable), read inside
as p.params["KEY"] — so it need not squat on --amount or hard-code constants at module level.
Numeric-looking values arrive as floats. Keep them identical across fragments: they are part
of the treatment, and the cohesion rule below covers them too.

Cohesion rule: run the SAME style + seed over EVERY fragment, or they won't read as one object.
"""
import argparse, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batch

TREATMENTS = {}
def treatment(name, helptext):
    def reg(fn): TREATMENTS[name] = (fn, helptext); return fn
    return reg

def _hex(s):
    s = (s or "").lstrip("#")
    return np.array([int(s[i:i+2], 16) for i in (0, 2, 4)], float)

def lum(rgb):  # 0..1 luminance, reuse when inventing
    return (rgb @ np.array([0.2126, 0.7152, 0.0722])) / 255.0

@treatment("duotone", "luminance → two-colour ramp (--dark --light)")
def t_duotone(rgb, p, rng):
    d = _hex(p.dark or "#101820"); l = _hex(p.light or "#e8e2d0")
    t = lum(rgb)[..., None]
    return d * (1 - t) + l * t

@treatment("tritone", "luminance → three-stop ramp (--dark --mid --light)")
def t_tritone(rgb, p, rng):
    d = _hex(p.dark or "#0a1014"); m = _hex(p.mid or "#4a6a72"); l = _hex(p.light or "#e8e2d0")
    t = lum(rgb)
    lo = np.clip(t / 0.5, 0, 1)[..., None]
    hi = np.clip((t - 0.5) / 0.5, 0, 1)[..., None]
    return np.where(t[..., None] < 0.5, d * (1 - lo) + m * lo, m * (1 - hi) + l * hi)

@treatment("splittone", "tint shadows vs highlights (--dark shadow, --light highlight)")
def t_splittone(rgb, p, rng):
    d = _hex(p.dark or "#243b4a"); l = _hex(p.light or "#f0e6c8")
    g = lum(rgb)[..., None]
    tint = d * (1 - g) + l * g          # hue that shifts with tone
    return 0.55 * (g * 255) + 0.45 * tint  # keep contrast, lay tint over it

@treatment("desaturate", "toward grey (--amount 0..1)")
def t_desaturate(rgb, p, rng):
    a = p.amount if p.amount is not None else 1.0
    g = lum(rgb)[..., None] * 255
    return rgb * (1 - a) + g * a

@treatment("grain", "seeded film grain (--amount, --seed)")
def t_grain(rgb, p, rng):
    a = p.amount if p.amount is not None else 0.12
    n = rng.standard_normal(rgb.shape[:2])[..., None] * (a * 255)
    return rgb + n

# ---- reusable plumbing (import these when inventing a treatment) ----

def load(path):
    return Image.open(path).convert("RGBA")

def save_rgb(src_img, rgb, out_path):
    """Recombine treated RGB with the source's alpha and save. Reuse when inventing."""
    rgb = np.clip(rgb, 0, 255).astype("uint8")
    a = np.asarray(src_img.split()[3])
    img = Image.fromarray(np.dstack([rgb, a]), "RGBA")
    img.save(out_path)
    return img

def parse_params(pairs):
    """KEY=VALUE pairs for a --style-file, coerced to float where they look numeric. Without
    it a custom treatment can only receive --amount, so it hard-codes its constants and stops
    being tunable from the build script."""
    out = {}
    for kv in pairs or []:
        if "=" not in kv:
            sys.exit(f"--param takes KEY=VALUE, got '{kv}'")
        k, v = kv.split("=", 1)
        try:
            out[k.strip()] = float(v)
        except ValueError:
            out[k.strip()] = v
    return out

def _resolve(args):
    if args.style_file:
        import importlib.util
        spec = importlib.util.spec_from_file_location("user_treat", args.style_file)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.treat, "custom"
    return TREATMENTS[args.style][0], args.style

def build(args):
    if args.list:
        w = max(len(n) for n in TREATMENTS)
        for n, (_, h) in TREATMENTS.items():
            print(f"  {n:<{w}}  {h}")
        return 0
    if not args.style_file and (not args.style or args.style not in TREATMENTS):
        sys.exit(f"--style must be one of: {', '.join(TREATMENTS)} (or --style-file FILE, or --list)")
    if not (args.input and args.output):
        sys.exit("need IN and OUT paths")
    img = load(args.input)
    rgb = np.asarray(img)[..., :3].astype(float)
    args.params = parse_params(args.param)
    rng = np.random.default_rng(args.seed)
    fn, name = _resolve(args)
    save_rgb(img, fn(rgb, args, rng), args.output)
    if not getattr(args, "quiet", False):
        print(f"treat '{name}' -> {args.output}  ({img.width}x{img.height}, seed={args.seed})")
    return 0

def main():
    ap = argparse.ArgumentParser(description="Unify a fragment's colour/tone for collage.")
    ap.add_argument("input", nargs="?"); ap.add_argument("output", nargs="?")
    ap.add_argument("--style")
    ap.add_argument("--style-file", dest="style_file", default=None,
                    help="a .py file defining treat(rgb,p,rng)->rgb; invent a treatment without editing this tool")
    ap.add_argument("--param", action="append", default=[], metavar="KEY=VALUE",
                    help="repeatable; arrives as p.params['KEY'] in a --style-file, so a "
                         "custom treatment can take its own parameters")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dark"); ap.add_argument("--mid"); ap.add_argument("--light")
    ap.add_argument("--amount", type=float, default=None)
    ap.add_argument("--seed", type=int, default=0)
    batch.add_args(ap)
    args = ap.parse_args()
    sys.exit(batch.run(ap, args, "treat") if args.manifest else build(args))

if __name__ == "__main__":
    main()
