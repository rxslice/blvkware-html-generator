#!/usr/bin/env python3
"""
Render the kit graphics to PNG with headless Microsoft Edge.

    python marketing/kits/render.py            # every kit, every format
    python marketing/kits/render.py operator   # one kit

Writes marketing/kits/out/<kit>-<format>.png. The template is plain HTML in
the site's own design system, so a change of price or wording is an edit to
template.html and a re-run, not a design job.

Sizes follow what each destination asks for:
  Gumroad thumbnail  square, at least 600x600       -> 600x600 CSS px at 2x
  Gumroad covers     at least 1280x720              -> 1280x720 CSS px at 2x
  Ads                the platforms' standard sizes  -> exact pixels at 1x
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TEMPLATE = HERE / "template.html"

EDGE_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
]

#: format -> (css width, css height, device scale, output suffix)
FORMATS = {
    "thumb": (600, 600, 2, "gumroad-thumbnail"),
    "hero": (1280, 720, 2, "gumroad-cover-1-hero"),
    "inside": (1280, 720, 2, "gumroad-cover-2-inside"),
    "how": (1280, 720, 2, "gumroad-cover-3-how"),
    "square": (1080, 1080, 1, "ad-square-1080x1080"),
    "landscape": (1200, 628, 1, "ad-landscape-1200x628"),
    "story": (1080, 1920, 1, "ad-story-1080x1920"),
}
KITS = ("operator", "deputy")


def browser() -> Path:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise SystemExit("no Edge or Chrome found for headless rendering")


def render(kit: str, fmt: str) -> Path:
    width, height, scale, suffix = FORMATS[fmt]
    target = OUT / f"{kit}-{suffix}.png"
    url = TEMPLATE.as_uri() + f"?kit={kit}&fmt={fmt}"
    subprocess.run(
        [
            str(browser()),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--allow-file-access-from-files",
            f"--force-device-scale-factor={scale}",
            f"--window-size={width},{height}",
            # Time for the web fonts: without it the first frame is a fallback face.
            "--virtual-time-budget=10000",
            f"--screenshot={target}",
            url,
        ],
        check=True,
        capture_output=True,
    )
    return target


def main() -> int:
    OUT.mkdir(exist_ok=True)
    kits = [k for k in sys.argv[1:] if k in KITS] or list(KITS)
    for kit in kits:
        for fmt in FORMATS:
            path = render(kit, fmt)
            print(f"{path.relative_to(HERE)}  {path.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
