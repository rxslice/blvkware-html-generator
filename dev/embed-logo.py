#!/usr/bin/env python3
"""Derive every logo asset from the one master image, then patch the sources.

    python dev/embed-logo.py

`assets/blvkware-logo.webp` is the logo exactly as the owner supplied it and is
never modified or re-drawn — only decoded, cropped to the artwork, and resized.
Everything else on the site and in the tools is generated from it here, so the
brand can never drift between surfaces.

Re-running is safe: each patch site is delimited, so the script replaces its own
previous output rather than stacking.

Needs Pillow (`pip install pillow`). The dev server and the static build stay
stdlib-only; this runs ahead of them, by hand, when the logo changes.
"""

import base64
import io
import os
import re
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("ERROR: this script needs Pillow and numpy.  pip install pillow numpy")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "assets", "blvkware-logo.webp")
ASSETS = os.path.join(ROOT, "docs", "assets")

# Bounding box of the actual artwork inside the master, measured with a
# luminance threshold — the source carries a wide flat-black margin that would
# otherwise shrink the mark to nothing at favicon sizes.
ART_BOX = (104, 51, 1149, 1155)

PNG_SIZES = [
    (512, "logo-512.png"),
    (192, "logo-192.png"),
    (96, "logo-96.png"),
    (48, "favicon-48.png"),
]

# Inline copy for the single-file tools. WebP keeps this at a few KB where the
# equivalent PNG costs ~27 KB in every page.
INLINE_PX = 160


def square(im):
    """Crop to a centred square that holds the whole artwork, nothing clipped."""
    w, h = im.size
    x0, y0, x1, y1 = ART_BOX
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    half = max(x1 - x0, y1 - y0) / 2.0
    box = (int(round(cx - half)), int(round(cy - half)),
           int(round(cx + half)), int(round(cy + half)))
    return im.crop((max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3])))


def resize(img, size):
    """Downscale in linear light.

    The mark is thin brass linework on black. Averaging those strokes in sRGB
    space crushes them toward black, and below ~48px the whole emblem turns into
    a dark smudge. Converting to linear, resampling, then converting back keeps
    their true luminance — the difference is dramatic at favicon and nav sizes.
    """
    a = np.asarray(img, dtype=np.float32) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    chans = [np.asarray(Image.fromarray(lin[:, :, c], mode="F")
                        .resize((size, size), Image.LANCZOS)) for c in range(3)]
    out = np.clip(np.stack(chans, -1), 0.0, 1.0)
    srgb = np.where(out <= 0.0031308, out * 12.92, 1.055 * out ** (1 / 2.4) - 0.055)
    return Image.fromarray((np.clip(srgb, 0, 1) * 255).round().astype(np.uint8), "RGB")


def data_uri(img, size, fmt, **kw):
    buf = io.BytesIO()
    resize(img, size).save(buf, fmt, **kw)
    mime = "image/webp" if fmt == "WEBP" else "image/png"
    return "data:%s;base64,%s" % (mime, base64.b64encode(buf.getvalue()).decode("ascii")), len(buf.getvalue())


def patch(path, pattern, replacement, label):
    """Swap one delimited region. A miss is an error, never a silent no-op."""
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    new, n = re.subn(pattern, lambda m: replacement, src, count=1)
    if n != 1:
        print("  FAILED  %s - anchor not found in %s" % (label, os.path.basename(path)))
        return False
    if new == src:
        print("  ok      %s (already current)" % label)
        return True
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    print("  patched %s" % label)
    return True


def main():
    if not os.path.isfile(MASTER):
        print("ERROR: master logo missing at assets/blvkware-logo.webp")
        return 1
    if not os.path.isdir(ASSETS):
        os.makedirs(ASSETS)

    im = Image.open(MASTER).convert("RGB")
    print("master  %s  %dx%d" % (os.path.basename(MASTER), im.size[0], im.size[1]))
    sq = square(im)
    print("artwork cropped to %dx%d" % sq.size)

    for size, name in PNG_SIZES:
        p = os.path.join(ASSETS, name)
        resize(sq, size).save(p, "PNG", optimize=True)
        print("  %-16s %4dpx  %6.1f KB" % (name, size, os.path.getsize(p) / 1024.0))

    # Landscape card for link previews.
    og = Image.new("RGB", (1200, 630), (7, 6, 4))
    og.paste(resize(sq, 520), ((1200 - 520) // 2, (630 - 520) // 2))
    og.save(os.path.join(ASSETS, "og.png"), "PNG", optimize=True)
    print("  %-16s          %6.1f KB" % ("og.png", os.path.getsize(os.path.join(ASSETS, "og.png")) / 1024.0))

    uri, raw = data_uri(sq, INLINE_PX, "WEBP", quality=88, method=6)
    print("  inline data URI  %dpx  %.1f KB raw / %.1f KB encoded"
          % (INLINE_PX, raw / 1024.0, len(uri) / 1024.0))

    ok = True

    # --- app.html: every <use href="#i-blvkmark"/> keeps working untouched ---
    ok &= patch(
        os.path.join(ROOT, "app.html"),
        r'<symbol id="i-blvkmark"[^>]*>[\s\S]*?</symbol>',
        '<symbol id="i-blvkmark" viewBox="0 0 64 64">\n'
        '    <image href="' + uri + '" x="0" y="0" width="64" height="64"/>\n'
        '  </symbol>',
        "app.html brand symbol")

    # --- tools that carry the mark inline in a <span class="mark"> ---
    for name in ("scry.html", "augur.html"):
        ok &= patch(
            os.path.join(ROOT, name),
            r'<span class="mark">[\s\S]*?</span>',
            '<span class="mark">\n'
            '        <img src="' + uri + '" alt="" width="160" height="160">\n'
            '      </span>',
            name + " brand mark")

    # --- marketing site: real file, it is not a single-file artifact ---
    ok &= patch(
        os.path.join(ROOT, "site", "index.html"),
        r'<span class="logo-mark" aria-hidden="true">[\s\S]*?</span>',
        '<span class="logo-mark" aria-hidden="true">\n'
        '                    <img src="/assets/logo-192.png" alt="" width="192" height="192">\n'
        '                </span>',
        "site brand mark")

    print("done" if ok else "FINISHED WITH ERRORS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
