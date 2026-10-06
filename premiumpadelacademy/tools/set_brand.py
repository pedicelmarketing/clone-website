#!/usr/bin/env python3
"""Rename the site brand across every page.

The academy trades as "Nexum Padel" (nexumpadel.es, info@nexumpadel.es, and the
logo artwork Riki supplied on 2026-08-03). The build was written under the
earlier working name "Premium Padel Academy", which survived in the <title>,
the header wordmark, image alt text and the copyright line on all four routes.

Those strings are identical on every page, so they are swept from here rather
than hand-edited four times — same reasoning as tools/set_contact_email.py.
Page-unique headings (the index <h1>, the clubs <h1>, the contacto eyebrow) are
listed explicitly below because each reads differently in context.

    python3 tools/set_brand.py --check     # exit 1 if the old name survives
    python3 tools/set_brand.py --apply

Stdlib only, to match the rest of the tooling in this repo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PAGES = ("index.html", "clubs.html", "camps.html", "contacto.html")

OLD = "Premium Padel Academy"
NEW = "Nexum Padel"

# Applied to every page. Ordered: the longest, most specific patterns first so a
# broad rule never eats a string a narrower rule was meant to handle.
COMMON = [
    # The old strapline led with "alto rendimiento", which Riki asked us to drop
    # ("Quitar alto rendimiento", 2026-08-03) — the academy takes every level,
    # not just competitors.
    ("<p>Academia de pádel de alto rendimiento con sede en Marbella.</p>",
     "<p>Academia de pádel en Marbella, España.</p>"),
    (f'aria-label="{OLD} — inicio"', f'aria-label="{NEW} — inicio"'),
    (f'<span class="brand-word">{OLD}</span>', f'<span class="brand-word">{NEW}</span>'),
    (f'alt="{OLD}"', f'alt="{NEW}"'),
    (f"© 2026 {OLD}.", f"© 2026 {NEW}."),
    (f"| {OLD}", f"| {NEW}"),
]

# name -> [(old, new)]. Headings that only exist on one route.
PER_PAGE = {
    # The clubs H1 was the only English sentence on a lang="es" page.
    "clubs.html": [
        (f"<h1>{OLD} in your club</h1>", f"<h1>{NEW} en tu club</h1>"),
    ],
    "contacto.html": [
        (f'<p class="eyebrow">{OLD} · Marbella</p>',
         f'<p class="eyebrow">{NEW} · Marbella</p>'),
    ],
    "index.html": [
        (f"<h1>{OLD}</h1>", f"<h1>{NEW}</h1>"),
    ],
}


def rules_for(name: str) -> list[tuple[str, str]]:
    return PER_PAGE.get(name, []) + COMMON


def apply(root: Path) -> int:
    touched = 0
    for name in PAGES:
        page = root / name
        if not page.exists():
            sys.exit(f"FATAL: {page} missing")
        html = original = page.read_text(encoding="utf-8")
        for old, new in rules_for(name):
            html = html.replace(old, new)
        if html != original:
            page.write_text(html, encoding="utf-8")
            touched += 1
            print(f"  rewrote {name}")
        else:
            print(f"  {name} already current")
    return touched


def check(root: Path) -> int:
    problems = 0
    for name in PAGES:
        html = (root / name).read_text(encoding="utf-8")
        n = html.count(OLD)
        # The <html lang> attribute is not touched here; only the brand string.
        print(f"  {name:14} {n} occurrence(s) of {OLD!r}")
        problems += n
    print(f"\n{'FAIL' if problems else 'OK'}: {problems} leftover(s).")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site-v2")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    root = PROJECT / args.root
    if not args.apply and not args.check:
        ap.error("nothing to do — pass --apply or --check")

    if args.apply:
        apply(root)
    return check(root) if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
