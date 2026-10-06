#!/usr/bin/env python3
"""Emit robots.txt and sitemap.xml into a build tree.

Both files are derived from the routes the site actually has, so they cannot
drift from it, and both track the build's indexing state:

  draft  (noindex)  -> robots.txt disallowing everything, NO sitemap.
                       A sitemap advertising pages that carry noindex is a
                       contradiction; better to publish none at all.
  launch (--allow-index) -> robots.txt allowing everything and pointing at a
                       sitemap listing every route, with hreflang alternates so
                       Google pairs the Spanish and English versions instead of
                       treating them as duplicates.

    python3 tools/seo_files.py --root build --launch
    python3 tools/seo_files.py --root build            # draft

Stdlib only, to match the rest of the tooling in this repo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SITE_URL = "https://nexumpadel.es"

# Spanish route -> English route. Mirrors tools/build_en.py ROUTES; kept here
# rather than imported so this stays runnable on a tree build_en never touched.
ROUTES = {
    "index.html": "index.html",
    "clubs.html": "clubs.html",
    "camps.html": "camps.html",
    "contacto.html": "contact.html",
    "privacidad.html": "privacy.html",
}

# Rough priority: the home page first, legal last. Google largely ignores these
# now, but they cost nothing and still express intent to other crawlers.
PRIORITY = {"index.html": "1.0", "clubs.html": "0.8", "camps.html": "0.8",
            "contacto.html": "0.7", "privacidad.html": "0.3"}


def urls() -> list[tuple[str, str, str]]:
    """(loc, es_alternate, en_alternate) for every route, both languages."""
    out = []
    for es, en in ROUTES.items():
        es_url = f"{SITE_URL}/{es}"
        en_url = f"{SITE_URL}/en/{en}"
        out.append((es_url, es_url, en_url))
        out.append((en_url, es_url, en_url))
    return out


def sitemap(lastmod: str) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
             '        xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, es_url, en_url in urls():
        route = loc.rsplit("/", 1)[-1]
        lines += [
            "  <url>",
            f"    <loc>{loc}</loc>",
            f'    <xhtml:link rel="alternate" hreflang="es" href="{es_url}" />',
            f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}" />',
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{es_url}" />',
            f"    <lastmod>{lastmod}</lastmod>",
            f"    <priority>{PRIORITY.get(route, '0.5')}</priority>",
            "  </url>",
        ]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="build")
    ap.add_argument("--launch", action="store_true",
                    help="indexable build: allow crawling and emit a sitemap")
    ap.add_argument("--lastmod", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    root = PROJECT / args.root
    if not (root / "index.html").exists():
        sys.exit(f"FATAL: {root}/index.html missing")

    sm = root / "sitemap.xml"
    if args.launch:
        (root / "robots.txt").write_text(
            "User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
        sm.write_text(sitemap(args.lastmod), encoding="utf-8")
        print(f"  robots.txt: crawling allowed；sitemap.xml: {len(urls())} URL(s)"
              .replace("；", "; "))
    else:
        (root / "robots.txt").write_text(
            "# Unapproved draft — every page also carries a noindex meta tag.\n"
            "User-agent: *\n"
            "Disallow: /\n", encoding="utf-8")
        if sm.exists():
            sm.unlink()
        print("  robots.txt: crawling disallowed (draft); no sitemap emitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
