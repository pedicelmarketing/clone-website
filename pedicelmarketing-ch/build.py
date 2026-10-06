"""pages/ (English templates) + strings/<lang>.json -> dist/ (de at /, fr at /fr/, en at /en/).

python3 build.py            # all languages; exit 1 listing untranslated strings
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from textlayer import HOST, LANGS, MissingTranslation, localize, prefix

HERE = Path(__file__).parent
PAGES, STRINGS, DIST, ASSETS = HERE / "pages", HERE / "strings", HERE / "dist", HERE / "assets"
MIRROR = Path(os.environ.get("MIRROR", "/home/openclaw/Coding/ Cloning Sites/clone-website/pedicelmarketing/mirror"))


def routes() -> list[tuple[str, Path]]:
    if not PAGES.is_dir():
        return []
    out = []
    for f in sorted(PAGES.rglob("index.html")):
        rel = f.parent.relative_to(PAGES).as_posix()
        out.append(("/" if rel == "." else f"/{rel}/", f))
    return out


def tmap(lang: str) -> dict[str, str]:
    f = STRINGS / f"{lang}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lang", choices=[*LANGS, "all"], default="all", help="language to build (default all)")
    args = ap.parse_args(argv)
    build_langs = LANGS if args.lang == "all" else (args.lang,)
    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()
    failed = 0
    for lang in build_langs:
        m = tmap(lang)
        for route, src in routes():
            try:
                html = localize(src.read_text(encoding="utf-8"), lang, route, m)
            except MissingTranslation as e:
                failed += len(e.missing)
                print(f"[{lang}] {route}: {len(e.missing)} untranslated, e.g. {e.missing[0]!r}")
                continue
            dest = DIST / prefix(lang).lstrip("/") / route.strip("/") / "index.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(html, encoding="utf-8")
    if (DIST / "404" / "index.html").exists():
        shutil.copy(DIST / "404" / "index.html", DIST / "404.html")
    if ASSETS.is_dir():
        shutil.copytree(ASSETS, DIST / "assets", dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.md"))
    if (MIRROR / "_external").exists():
        (DIST / "_external").symlink_to(MIRROR / "_external")
    else:
        print(f"warning: {MIRROR / '_external'} not found, dist/_external not linked (set MIRROR=...)")
    urls = [f"{HOST}{prefix(l)}{r}" for l in LANGS for r, _ in routes() if r != "/404/"]
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {HOST}/sitemap.xml\n")
    print(f"build: {len(routes())} pages x {len(build_langs)} languages" + (f", {failed} untranslated" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
