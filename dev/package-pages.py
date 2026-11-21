"""Package the verified storefront, including the hidden agent discovery endpoints."""
import argparse
import json
import os
from pathlib import Path
import re
import tarfile
import tempfile

REQUIRED = (
    "CNAME", ".nojekyll", "index.html", "pricing/index.html", "hallux/index.html",
    "cordon/index.html", "hallux/checkout/index.html", "docs/payment/index.html",
    "terms/index.html", "privacy/index.html", "refund/index.html", "legal/index.html",
    "robots.txt", "sitemap.xml", ".well-known/ai-catalog.json", ".well-known/mcp.json",
    ".well-known/api-catalog", ".well-known/agent-skills/index.json",
)


def package(root, target):
    if root.is_symlink() or not root.is_dir() or target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Supply a site directory and an archive destination outside it")
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink() or any(part.startswith(".") and
                not (index == 0 and part in {".nojekyll", ".well-known"})
                for index, part in enumerate(relative.parts)):
            raise ValueError(f"Unexpected hidden path or symbolic link: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"Unexpected file type: {relative}")
        if path.suffix in {".html", ".json", ".txt", ".xml"} and re.search(
                rb"\{\{HALLUX_[A-Z0-9_]+\}\}", path.read_bytes()):
            raise ValueError(f"Unresolved HALLUX token: {relative}")
        files.append(relative)
    missing = sorted(set(REQUIRED) - {str(p) for p in files})
    if missing:
        raise ValueError("Missing release files: " + ", ".join(missing))
    if (root / "CNAME").read_text().strip() != "blvkware.dev":
        raise ValueError("Unexpected production domain")
    catalog = json.loads((root / ".well-known/ai-catalog.json").read_text())
    services = {entry["id"]: entry for entry in catalog["entries"]}
    if not {"hallux", "cordon", "hallux-mcp", "cordon-mcp"} <= services.keys():
        raise ValueError("Production catalog is missing an API or MCP entry")
    hallux = services["hallux"]
    pricing = hallux["pricing"]
    rail = hallux["payment"]["apiKey"]
    offered = [(p["usd"], p["credits"]) for p in pricing["purchasable"]]
    sold = [(p["usd"], p["identifiers"]) for p in rail.get("packs", [])]
    if (not sold or sold != offered or rail.get("settlementConfigured") is not True
            or rail.get("buy") != pricing["buy"]):
        raise ValueError("Catalog pricing and live checkout packs disagree")

    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
        pending = Path(temp.name)
    try:
        with tarfile.open(pending, "w", dereference=True) as archive:
            for relative in files:
                archive.add(root / relative, arcname="./" + relative.as_posix(), recursive=False)
        os.replace(pending, target)
    finally:
        pending.unlink(missing_ok=True)
    print(f"Packaged {len(files)} public files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    package(args.site, args.archive)
