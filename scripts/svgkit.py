#!/usr/bin/env python3
"""
svgkit.py — composition plumbing for the collage assembly stage (Stage B).

This is the reusable *infrastructure* of composing an SVG: embedding images once, placing
fragments with scale/rotation, renderer-safe contact shadows, text, and rendering. It has
**no presets and no layout templates by design** — composition is the most creative part of a
collage and must be invented fresh per piece. Import this so your build script reuses the
fiddly, get-it-right-once plumbing and spends its effort on the layout.

Everything it emits is **filter-free and portable** (embedded <image> + <use>, radial-gradient
shadows, live <text>), so the shipped .svg matches its .png in any engine — keep it that way.

    import svgkit
    c = svgkit.Canvas(2400, 3600, bg="#0b1a24")
    tower = c.embed("fragments/tower.png", max_width=700)   # ONCE, at the size it's drawn
    c.contact_shadow(300, 900, 700, 1600)         # under the fragment (call before place)
    c.place(tower, x=300, y=900, w=700, rotate=-4, opacity=0.96)
    c.text("THE BODY CORPORATE", 200, 260, size=90, font="Anton", fill="#e8e2d0")
    c.raw('<path d="..." fill="#c33"/>')          # escape hatch: any custom SVG you invent
    c.save("collage.svg")
    svgkit.render("collage.svg", "collage.png", 2400, fontconfig=CONF)

Then, per doctrine: vectorize downloaded-font text (scripts/vectorize_text.sh) and verify the
shipped .svg == .png (scripts/check_render.sh) before shipping.
"""
import base64, io, os, subprocess
from PIL import Image

def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

class Canvas:
    def __init__(self, w, h, bg=None):
        self.w, self.h = int(w), int(h)
        self._defs, self._body, self._embedded, self._n = [], [], {}, 0
        if bg:
            self._body.append(f'<rect width="{self.w}" height="{self.h}" fill="{bg}"/>')

    def _id(self, pfx):
        self._n += 1
        return f"{pfx}{self._n}"

    def embed(self, path, max_width=None, jpeg_quality=90, colors=256):
        """Embed an image once (JPEG for opaque, quantized PNG for alpha) and return a handle.
        Re-embedding the same path is free — the payload is stored a single time.

        Pass `max_width` = the width you will place it at: embedding a fragment larger than
        it is drawn buys nothing visible and costs real megabytes. Oversized base64 is a hard
        failure, not just bloat — past libxml2's attribute limits `rsvg-convert` aborts with
        `Premature end of data in tag defs` on XML that is perfectly valid. Raise `colors`
        (or set it to 0) if palette banding shows on a large gradient fragment."""
        if path in self._embedded:
            return self._embedded[path]
        im = Image.open(path)
        if max_width and im.width > max_width:
            max_width = int(max_width)
            im = im.resize((max_width, max(1, round(im.height * max_width / im.width))),
                           Image.LANCZOS)
        alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        buf = io.BytesIO()
        if alpha:
            im = im.convert("RGBA")
            if colors:
                im = im.quantize(colors=int(colors), method=Image.FASTOCTREE)
            im.save(buf, "PNG", optimize=True); mime = "image/png"
        else:
            im.convert("RGB").save(buf, "JPEG", quality=jpeg_quality); mime = "image/jpeg"
        uri = f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"
        iid = self._id("img")
        self._defs.append(
            f'<image id="{iid}" width="{im.width}" height="{im.height}" xlink:href="{uri}"/>')
        self._embedded[path] = (iid, im.width, im.height)
        return self._embedded[path]

    def place(self, frag, x, y, w=None, h=None, rotate=0, opacity=1.0):
        """Place an embedded fragment. Give w OR h to scale (aspect kept); rotate about its
        centre. Returns (x, y, w, h) so you can chain placements off it."""
        iid, iw, ih = frag
        if w is None and h is None: w = iw
        if w is None: w = iw * (h / ih)
        if h is None: h = ih * (w / iw)
        s = w / iw
        cx, cy = x + w / 2, y + h / 2
        tr = f"translate({x:.2f} {y:.2f}) scale({s:.5f})"
        if rotate:
            tr = f"rotate({rotate:.3f} {cx:.2f} {cy:.2f}) " + tr
        op = f' opacity="{opacity:.3f}"' if opacity != 1.0 else ""
        self._body.append(f'<use xlink:href="#{iid}" transform="{tr}"{op}/>')
        return (x, y, w, h)

    def contact_shadow(self, x, y, w, h, dy=None, spread=1.1, opacity=0.45):
        """A renderer-safe soft shadow (radial gradient, no filters). Call BEFORE place()
        so it sits underneath."""
        gid = self._id("sg")
        self._defs.append(
            f'<radialGradient id="{gid}"><stop offset="0" stop-color="#000" '
            f'stop-opacity="{opacity:.3f}"/><stop offset="1" stop-color="#000" '
            f'stop-opacity="0"/></radialGradient>')
        dy = h * 0.03 if dy is None else dy
        cx, cy = x + w / 2, y + h / 2 + dy
        rx, ry = w * 0.5 * spread, h * 0.28 * spread
        self._body.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#{gid})"/>')

    def text(self, s, x, y, size=48, font="serif", fill="#111", anchor="start",
             rotate=0, spacing=0, weight=None, opacity=1.0):
        """A live <text> element. Vectorize downloaded fonts before shipping (see doctrine)."""
        a = (f'x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" '
             f'text-anchor="{anchor}"')
        if spacing: a += f' letter-spacing="{spacing}"'
        if weight:  a += f' font-weight="{weight}"'
        if opacity != 1.0: a += f' opacity="{opacity:.3f}"'
        if rotate:  a += f' transform="rotate({rotate} {x} {y})"'
        self._body.append(f'<text {a}>{_esc(s)}</text>')

    def raw(self, svg):
        """Escape hatch: append any custom SVG. Keep it filter-free for portability."""
        self._body.append(svg)

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<defs>{"".join(self._defs)}</defs>{"".join(self._body)}</svg>')

    def save(self, path):
        with open(path, "w") as f:
            f.write(self.svg())
        return path

def render(svg_path, png_path, width, fontconfig=None):
    """Render the shipping PNG with inkscape (the one committed renderer)."""
    env = dict(os.environ)
    if fontconfig:
        env["FONTCONFIG_FILE"] = fontconfig
    subprocess.run(["inkscape", svg_path, "--export-type=png",
                    f"--export-filename={png_path}", "-w", str(int(width))],
                   env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return png_path
