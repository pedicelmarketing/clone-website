"""Local visual QA of dist/: screenshots + layout / 404 / hero assertions.

    python3 -m http.server 8090 --bind 127.0.0.1 -d dist &
    python3 qa_shots.py                       # base http://127.0.0.1:8090
    QA_BASE=http://127.0.0.1:8187 python3 qa_shots.py
    python3 qa_shots.py --base http://127.0.0.1:8187

For every URL in dist/sitemap.xml: full-page screenshots at 1440x900 and 390x844 into
shots/<lang>/<route>-<w>.png (after scrolling the page once so Webflow scroll-into-view
animations have run). Fails (exit 1) on:
  - horizontal scroll (scrollWidth > innerWidth) at 390, 1440, and also at 768 and 1024
    (checked without screenshots);
  - any same-origin HTTP response >= 400;
  - the home H1 not visible on load without scrolling (box inside the viewport and
    computed opacity > 0.5) at 390x900, 390x844 and 1440x900, in every language;
  - on any page at 390x900, an H1 that starts inside the first screen but is invisible;
  - the language switcher not visible inside the opened mobile menu at 390.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
HOST = "https://pedicelmarketing.ch"
SIZES = [(1440, 900), (390, 844)]
SCROLL_ONLY_SIZES = [(768, 1024), (1024, 768)]
HERO_SIZES = [(390, 900), (390, 844), (1440, 900)]
HERO_RUNS = 3  # the hero race was intermittent; check each case several times
LANG_HOMES = {"de": "/", "fr": "/fr/", "en": "/en/"}

HERO_JS = """() => {
  const h = document.querySelector('h1');
  if (!h) return {ok: false, why: 'no h1'};
  const r = h.getBoundingClientRect();
  let op = 1;
  for (let e = h; e; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
  const inView = r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= innerHeight + 1
                 && r.left >= 0 && r.right <= innerWidth + 1;
  return {ok: inView && op > 0.5, op: Math.round(op * 100) / 100,
          box: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)],
          scrollY: scrollY, text: h.innerText.slice(0, 40)};
}"""

SCROLL_THROUGH_JS = """async () => {
  const step = Math.max(200, innerHeight / 2);
  for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
    scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
  }
  scrollTo(0, 0); await new Promise(r => setTimeout(r, 400));
}"""


def lang_and_name(path: str) -> tuple[str, str]:
    parts = [p for p in path.strip("/").split("/") if p]
    lang = "de"
    if parts and parts[0] in ("fr", "en"):
        lang = parts.pop(0)
    return lang, "_".join(parts) or "home"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=os.environ.get("QA_BASE", "http://127.0.0.1:8090"))
    ap.add_argument("--no-shots", action="store_true", help="assertions only, skip full-page screenshots")
    args = ap.parse_args(argv)
    base = args.base.rstrip("/")
    origin = urlparse(base).netloc
    paths = [u.replace(HOST, "", 1) or "/"
             for u in re.findall(r"<loc>(.*?)</loc>", (HERE / "dist/sitemap.xml").read_text())]
    bad: list[str] = []
    seen_404: set[str] = set()

    def on_response(resp, page_url):
        if urlparse(resp.url).netloc == origin and resp.status >= 400 and resp.url not in seen_404:
            seen_404.add(resp.url)
            bad.append(f"HTTP {resp.status} {resp.url.replace(base, '')} (from {page_url})")

    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:  # bundled browser not downloaded for this playwright version
            b = p.chromium.launch(channel="chrome")

        # 1. Home H1 visible on first paint, no scrolling, fresh context per check.
        for lang, home in LANG_HOMES.items():
            for w, h in HERO_SIZES:
                for run in range(HERO_RUNS):
                    ctx = b.new_context(viewport={"width": w, "height": h})
                    pg = ctx.new_page()
                    pg.goto(base + home, wait_until="networkidle")
                    pg.wait_for_timeout(1500)  # past Webflow IX2 init + slide-in duration
                    res = pg.evaluate(HERO_JS)
                    if not res["ok"]:
                        bad.append(f"home H1 not visible [{lang} {w}x{h} run {run + 1}]: {res}")
                    ctx.close()

        # 1b. Every page at 390x900: an H1 that starts inside the first viewport must be visible.
        ctx = b.new_context(viewport={"width": 390, "height": 900})
        pg = ctx.new_page()
        for path in paths:
            pg.goto(base + path, wait_until="networkidle")
            pg.wait_for_timeout(1200)
            res = pg.evaluate(HERO_JS)
            if res.get("box") and res["box"][1] < 900 and res["op"] <= 0.5:
                bad.append(f"first-screen H1 invisible [390x900] {path}: {res}")
        ctx.close()

        # 2. Screenshots, horizontal scroll, same-origin 4xx/5xx.
        for w, h in SIZES:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = ctx.new_page()
            for path in paths:
                url = base + path
                handler = lambda r, u=path: on_response(r, u)
                pg.on("response", handler)
                pg.goto(url, wait_until="networkidle")
                lang, name = lang_and_name(path)
                if pg.evaluate("document.documentElement.scrollWidth > innerWidth"):
                    sw = pg.evaluate("document.documentElement.scrollWidth")
                    bad.append(f"horizontal scroll at {w} ({sw}px): {path}")
                if not args.no_shots:
                    pg.evaluate(SCROLL_THROUGH_JS)
                    out = HERE / "shots" / lang / f"{name}-{w}.png"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    pg.screenshot(path=str(out), full_page=True)
                pg.remove_listener("response", handler)
            ctx.close()

        # 2b. Tablet / small-desktop widths: horizontal scroll only, no screenshots.
        for w, h in SCROLL_ONLY_SIZES:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = ctx.new_page()
            for path in paths:
                pg.goto(base + path, wait_until="load")
                if pg.evaluate("document.documentElement.scrollWidth > innerWidth"):
                    sw = pg.evaluate("document.documentElement.scrollWidth")
                    bad.append(f"horizontal scroll at {w} ({sw}px): {path}")
            ctx.close()

        # 3. Language switcher inside the opened mobile menu.
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        pg = ctx.new_page()
        for lang, home in LANG_HOMES.items():
            pg.goto(base + home, wait_until="networkidle")
            pg.click(".w-nav-button")
            pg.wait_for_timeout(700)
            sw = pg.locator(".w-nav-menu .lang-switch").first
            if not sw.is_visible():
                bad.append(f"language switcher not visible in mobile menu: {home}")
            if not args.no_shots:
                out = HERE / "shots" / lang / "menu-open-390.png"
                out.parent.mkdir(parents=True, exist_ok=True)
                pg.screenshot(path=str(out))
        ctx.close()
        b.close()

    hero_checks = len(LANG_HOMES) * len(HERO_SIZES) * HERO_RUNS
    print("\n".join(bad) or f"qa: {len(paths)} pages x {len(SIZES)} widths shot, "
          f"no horizontal scroll at {len(SIZES) + len(SCROLL_ONLY_SIZES)} widths; "
          f"home H1 visible in {hero_checks}/{hero_checks} load checks; no same-origin 4xx/5xx; "
          f"mobile-menu switcher ok in {len(LANG_HOMES)} languages")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
