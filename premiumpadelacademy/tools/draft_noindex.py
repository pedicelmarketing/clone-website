#!/usr/bin/env python3
"""Add or remove the draft noindex marker on the public build.

The site goes live on a real domain before the client has approved it, and it
carries example reviews rather than real ones. Keeping search engines out while
that is true means the example content is not indexed, cached or surfaced in
results as a standing claim — and it means the approved version gets indexed
cleanly rather than inheriting a draft's history.

This is a one-line change, fully reversible:

    python3 tools/draft_noindex.py --root build --on      # while unapproved
    python3 tools/draft_noindex.py --root build --off     # at launch
    python3 tools/draft_noindex.py --root build --check

Removing it is the last step before announcing the site.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ANCHOR = '<meta name="viewport" content="width=device-width, initial-scale=1" />'
TAG = ('\n<!-- Draft: not yet approved by the client, and the reviews on this page are\n'
       '     examples rather than real ones. Remove this tag at launch:\n'
       '     python3 tools/draft_noindex.py --root build --off -->\n'
       '<meta name="robots" content="noindex, nofollow" />')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="build")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--on", action="store_true")
    group.add_argument("--off", action="store_true")
    group.add_argument("--check", action="store_true")
    args = ap.parse_args()

    root = PROJECT / args.root
    if not root.is_dir():
        sys.exit(f"FATAL: {root} is not a directory")

    pages = sorted(root.glob("*.html"))
    if not pages:
        sys.exit(f"FATAL: no pages in {root}")

    present = 0
    for page in pages:
        html = page.read_text(encoding="utf-8")
        has = 'name="robots"' in html

        if args.check:
            present += has
            print(f"  {page.name:14} noindex={'yes' if has else 'no'}")
            continue

        if args.on and not has:
            if ANCHOR not in html:
                sys.exit(f"FATAL: anchor meta not found in {page.name}")
            page.write_text(html.replace(ANCHOR, ANCHOR + TAG, 1), encoding="utf-8")
            print(f"  {page.name}: noindex added")
        elif args.off and has:
            page.write_text(html.replace(TAG, "", 1), encoding="utf-8")
            print(f"  {page.name}: noindex removed")

    if args.check:
        print(f"\n{present}/{len(pages)} page(s) carry noindex.")
        return 0

    # Self-check against what is actually on disk now.
    want = args.on
    bad = [p.name for p in pages
           if ('name="robots"' in p.read_text(encoding="utf-8")) != want]
    if bad:
        sys.exit(f"FATAL: {', '.join(bad)} did not end up in the expected state")
    print(f"\nall {len(pages)} page(s) {'now carry' if want else 'are clear of'} noindex.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
