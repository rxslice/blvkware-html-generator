#!/usr/bin/env python3
"""
Embed a PayPal donation QR into app.html as a data URI.

    1. Save your PayPal QR image to  assets/paypal-qr.png
    2. python dev/embed-qr.py [--paypal https://paypal.me/yourhandle]

Your image is embedded verbatim — it is never decoded or re-encoded, so the
payment destination cannot be altered. The only processing is an optional
downscale if the source is far larger than it needs to be, which is skipped
entirely unless Pillow is installed.

Run it again any time to replace the embedded code.
"""

import argparse
import base64
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.html")
DEFAULT_QR = os.path.join(ROOT, "assets", "paypal-qr.png")

# A QR only needs to be crisp, not large; 512px is plenty for a 178px panel on
# a 2x display. Anything bigger just inflates app.html.
MAX_PX = 512


def optimise(raw, path):
    """Downscale only if oversized. Returns (bytes, mime, note)."""
    ext = os.path.splitext(path)[1].lower()
    mime = "image/svg+xml" if ext == ".svg" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    if mime == "image/svg+xml":
        return raw, mime, "svg embedded as-is"
    try:
        from PIL import Image
    except ImportError:
        return raw, mime, "Pillow not installed - embedded at original size"

    try:
        im = Image.open(io.BytesIO(raw))
    except Exception:
        return raw, mime, "not decodable by Pillow - embedded as-is"

    w, h = im.size
    if max(w, h) <= MAX_PX:
        return raw, mime, "already %dx%d - embedded as-is" % (w, h)

    # NEAREST keeps QR module edges hard; smooth filters blur them and can cost
    # you scans on a marginal camera.
    scale = MAX_PX / float(max(w, h))
    im = im.convert("RGB").resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), "image/png", "downscaled %dx%d -> %dx%d" % (w, h, im.size[0], im.size[1])


def main():
    ap = argparse.ArgumentParser(description="Embed a donation QR into app.html.")
    ap.add_argument("--image", default=DEFAULT_QR, help="path to the QR image")
    ap.add_argument("--paypal", help="donation URL, e.g. https://paypal.me/yourhandle")
    args = ap.parse_args()

    if not os.path.isfile(args.image):
        print("ERROR: no image at %s" % args.image)
        print("Save your PayPal QR there (or pass --image PATH) and run again.")
        return 1

    with open(args.image, "rb") as fh:
        raw = fh.read()
    data, mime, note = optimise(raw, args.image)
    uri = "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))

    with io.open(APP, encoding="utf-8") as fh:
        src = fh.read()

    new, n = re.subn(r"(qr:\s*)'[^']*'", lambda m: m.group(1) + "'" + uri + "'", src, count=1)
    if not n:
        print("ERROR: could not find the `qr:` field in app.html.")
        return 1

    if args.paypal:
        if not re.match(r"^https://", args.paypal):
            print("ERROR: --paypal must be an https:// URL.")
            return 1
        new, n2 = re.subn(r"(paypal:\s*)'[^']*'",
                          lambda m: m.group(1) + "'" + args.paypal + "'", new, count=1)
        if not n2:
            print("WARNING: could not find the `paypal:` field; link not set.")

    with io.open(APP, "w", encoding="utf-8") as fh:
        fh.write(new)

    print("Embedded %s" % os.path.relpath(args.image, ROOT))
    print("  %s" % note)
    print("  data URI: %.1f KB" % (len(uri) / 1024.0))
    if args.paypal:
        print("  paypal:   %s" % args.paypal)
    else:
        print("  paypal:   not set - pass --paypal to enable the button")
    print("Reload the page to see it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
