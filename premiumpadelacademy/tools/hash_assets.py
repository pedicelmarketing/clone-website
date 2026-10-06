#!/usr/bin/env python3
"""Give CSS and JS content-addressed filenames so caching can be trusted.

The bug this exists to prevent, observed in production on 2026-08-03:

    nginx serves css/styles.css with `Cache-Control: immutable, max-age=31536000`
    while the HTML is only cached for 5 minutes. A returning visitor therefore
    picks up new markup against a stylesheet up to a year old. When the social
    links shipped, that combination rendered the Instagram <svg> with no
    matching rules at all — browser-default `fill: black` at 387x387 px, a
    giant black square in the footer. `immutable` means the browser will not
    even revalidate, so it does not heal on its own.

`immutable` is not the mistake; a stable filename is. Once the URL carries a
hash of the contents, a changed file is a different URL, the year-long cache is
correct, and a stale pairing cannot occur — the new HTML simply asks for a name
the old cache has never seen.

    python3 tools/hash_assets.py --root build
    python3 tools/hash_assets.py --root build --check

Run after every other transform, so the hash covers the final bytes. Idempotent:
already-hashed files are left alone.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ASSET_DIRS = ("css", "js")
HASHED = re.compile(r"\.[0-9a-f]{8}\.(css|js)$")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="build")
    ap.add_argument("--check", action="store_true",
                    help="verify every css/js reference is hashed; exit 1 if not")
    args = ap.parse_args()

    root = PROJECT / args.root
    if not root.is_dir():
        sys.exit(f"FATAL: {root} is not a directory")

    pages = sorted(root.rglob("*.html"))
    if not pages:
        sys.exit(f"FATAL: no pages under {root}")

    if args.check:
        bad = 0
        for page in pages:
            html = page.read_text(encoding="utf-8")
            for ref in re.findall(r'(?:href|src)="([^"]+\.(?:css|js))"', html):
                if ref.startswith(("http://", "https://", "//")):
                    continue
                if not HASHED.search(ref):
                    print(f"  FAIL: {page.relative_to(root)} -> {ref} (unhashed)")
                    bad += 1
        print(f"\n{'FAIL' if bad else 'OK'}: {bad} unhashed reference(s).")
        return 1 if bad else 0

    # rename, collecting old-name -> new-name
    renames: dict[str, str] = {}
    for folder in ASSET_DIRS:
        directory = root / folder
        if not directory.is_dir():
            continue
        for asset in sorted(directory.iterdir()):
            if not asset.is_file() or asset.suffix not in (".css", ".js"):
                continue
            if HASHED.search(asset.name):
                continue
            new_name = f"{asset.stem}.{digest(asset)}{asset.suffix}"
            asset.rename(directory / new_name)
            renames[f"{folder}/{asset.name}"] = f"{folder}/{new_name}"
            print(f"  {folder}/{asset.name} -> {new_name}")

    if not renames:
        print("Nothing to hash — all assets already content-addressed.")
        return 0

    # Rewrite references. Pages live at two depths (/, /en/), and reach these
    # assets with "css/…" or "../css/…", so the old path is matched wherever it
    # appears inside the attribute rather than anchored to the string start.
    rewritten = 0
    for page in pages:
        html = original = page.read_text(encoding="utf-8")
        for old, new in renames.items():
            html = re.sub(rf'((?:href|src)="[^"]*?){re.escape(old)}(")',
                          rf"\g<1>{new}\g<2>", html)
        if html != original:
            page.write_text(html, encoding="utf-8")
            rewritten += 1

    # Self-check against what is now on disk: every reference resolves, and none
    # still points at an unhashed name.
    problems = 0
    for page in pages:
        html = page.read_text(encoding="utf-8")
        for ref in re.findall(r'(?:href|src)="([^"]+\.(?:css|js))"', html):
            if ref.startswith(("http://", "https://", "//")):
                continue
            if not HASHED.search(ref):
                print(f"  FAIL: {page.relative_to(root)} still references {ref}")
                problems += 1
            elif not (page.parent / ref).exists():
                print(f"  FAIL: {page.relative_to(root)} -> {ref} does not exist")
                problems += 1

    print(f"\n{len(renames)} asset(s) hashed, {rewritten} page(s) rewritten.")
    if problems:
        print(f"FAIL: {problems} broken reference(s).")
        return 1
    print("OK: every css/js reference is hashed and resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
