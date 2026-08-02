#!/usr/bin/env python3
"""Remove the reviews section when it holds no real reviews.

strip_demo_reviews.py reverts the fabricated reviews to clearly-marked empty
slots, which is the right state for the working build: the design stays visible
and the placeholders are obviously placeholders.

On a public site that same state reads as an unfinished page — six "Pendiente"
cards and a dash where the rating should be. So for the public build the whole
section comes out instead, along with the nav link that points at it.

This is deliberately conservative: it refuses to run if any review card still
carries real content, so it can never delete genuine reviews.

    python3 tools/hide_empty_reviews.py --root build
    python3 tools/hide_empty_reviews.py --root build --check

Restore by re-running deploy/build_public.sh, which rebuilds from site-v2/.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

SECTION = re.compile(r'[ \t]*<section class="reviews-section".*?</section>\n', re.S)
NAV_LINK = re.compile(r'[ \t]*<li><a href="[^"]*#resenas"[^>]*>[^<]*</a></li>\n')
NAV_LINK_INLINE = re.compile(r'<a href="[^"]*#resenas"[^>]*>[^<]*</a>')


def has_real_reviews(section: str) -> bool:
    """True if any card carries content that is not a marked placeholder."""
    cards = re.findall(r'<figure class="review[^"]*".*?</figure>', section, re.S)
    for card in cards:
        if 'is-placeholder' in card or 'data-demo="true"' in card:
            continue
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="build")
    ap.add_argument("--check", action="store_true",
                    help="report only; exit 1 if a reviews section is still present")
    args = ap.parse_args()

    root = PROJECT / args.root
    if not root.is_dir():
        sys.exit(f"FATAL: {root} is not a directory")

    total = 0
    for page in sorted(root.glob("*.html")):
        html = page.read_text(encoding="utf-8")
        match = SECTION.search(html)

        if match and has_real_reviews(match.group(0)):
            sys.exit(f"REFUSING: {page.name} contains real review content — "
                     f"remove this step from the build instead of deleting it")

        out = html
        if match:
            out = SECTION.sub("", out, count=1)
            total += 1
            if args.check:
                print(f"  {page.name}: reviews section present")

        # The section is gone, so any anchor to it would be a dead link.
        out = NAV_LINK.sub("", out)
        out = NAV_LINK_INLINE.sub("", out)

        if not args.check and out != html:
            page.write_text(out, encoding="utf-8")
            print(f"  {page.name}: reviews section removed")

    if args.check:
        if total:
            print(f"\nFAIL: {total} reviews section(s) still present.")
            return 1
        print("OK: no reviews section.")
        return 0

    print(f"\n{total} reviews section(s) removed." if total
          else "Nothing to remove — no reviews section found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
