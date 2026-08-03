#!/usr/bin/env python3
"""Generate responsive image variants and wire them into srcset/sizes.

Context. The 2x ESRGAN upscale (tools/upscale_ingest.py) did what Riki asked —
"Resolucion de fotos y logo" — but it left site-v2/assets at ~16 MB, and the
home page alone pulled ~8 MB. Sharper photos are not worth a site that takes
ten seconds to paint, so the masters stay on disk as the quality source and the
pages serve width-matched derivatives instead.

Which widths are worth generating is a MEASURED question, not a guessed one.
`--measure` drives a real browser over all four routes at 390/768/1440 and
records the peak CSS width each <img> actually occupies; `--build` then emits
only the rungs that measurement justifies, and writes a `sizes` attribute
derived from the same numbers. Nothing here is hand-tuned.

    python3 tools/static_range.py site-v2 8713 &
    ~/.venvs/nt-mirror/bin/python tools/responsive_images.py --measure
    ~/.venvs/nt-mirror/bin/python tools/responsive_images.py --build
    ~/.venvs/nt-mirror/bin/python tools/responsive_images.py --check

--measure needs Playwright; --build needs Pillow. Both live in
~/.venvs/nt-mirror/bin/python, not in system python3.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / "site-v2"
ASSETS = ROOT / "assets"
VARIANTS = ASSETS / "r"
MEASUREMENTS = PROJECT / "reports" / "image-render-widths.json"
PAGES = ("index.html", "clubs.html", "camps.html", "contacto.html")

BASE = "http://127.0.0.1:8713"
VIEWPORTS = (("mobile", 390), ("tablet", 768), ("desktop", 1440))

# Candidate widths. A rung is emitted only if measurement justifies it, so this
# is an upper bound on what can be produced, not a list of what will be.
LADDER = (400, 600, 800, 1200, 1600, 2000, 2600, 3200)

# Retina headroom. 2 covers every mainstream high-DPI display; going to 3 would
# roughly double the bytes for detail almost nobody can resolve.
DPR = 2

JPEG_QUALITY = 82   # derivatives are viewed at their native size, so they can
                    # sit below the master's 88 without visible loss


def measure() -> dict:
    from playwright.sync_api import sync_playwright

    peak: dict[str, dict[str, int]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, width in VIEWPORTS:
            page = browser.new_page(viewport={"width": width, "height": 900},
                                    device_scale_factor=1)
            for route in PAGES:
                page.goto(f"{BASE}/{route}", wait_until="networkidle")
                # The scroll-reveal animation leaves below-fold images at zero
                # size until they enter the viewport, so measure after a full
                # scroll — same reason tools/qa/shot4.py scrolls before capture.
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(700)
                rows = page.evaluate("""() => [...document.images].map(i => [
                    i.getAttribute('src'), Math.round(i.getBoundingClientRect().width)])""")
                for src, css_width in rows:
                    if not src or ".jpg" not in src:
                        continue
                    name = src.split("/")[-1]
                    slot = peak.setdefault(name, {})
                    slot[label] = max(slot.get(label, 0), css_width)
            page.close()
        browser.close()

    MEASUREMENTS.parent.mkdir(parents=True, exist_ok=True)
    MEASUREMENTS.write_text(json.dumps(peak, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(f"measured {len(peak)} image(s) -> {MEASUREMENTS.relative_to(PROJECT)}")
    for name in sorted(peak):
        print(f"  {name:22} {peak[name]}")
    return peak


def load_measurements() -> dict:
    if not MEASUREMENTS.exists():
        sys.exit(f"FATAL: {MEASUREMENTS} missing — run --measure first "
                 "(with the site served on 8713)")
    return json.loads(MEASUREMENTS.read_text(encoding="utf-8"))


def rungs_for(needed: int, master_width: int) -> list[int]:
    """Ladder rungs up to the first one that covers `needed`, capped at master."""
    cap = min(master_width, needed)
    out = [w for w in LADDER if w < cap]
    out.append(cap)                      # exact top rung; never upsample
    return sorted(set(out))


def sizes_for(peak: dict[str, int]) -> str:
    """A `sizes` list read straight off the measured CSS widths."""
    mobile = peak.get("mobile") or peak.get("tablet") or peak.get("desktop") or 0
    tablet = peak.get("tablet") or mobile
    desktop = peak.get("desktop") or tablet
    return (f"(max-width: 430px) {mobile}px, "
            f"(max-width: 820px) {tablet}px, "
            f"{desktop}px")


def build(peak: dict) -> dict:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    VARIANTS.mkdir(parents=True, exist_ok=True)
    plan: dict[str, dict] = {}

    for name, widths in sorted(peak.items()):
        master = ASSETS / name
        if not master.exists():
            print(f"  {name:22} SKIP — no master on disk")
            continue

        img = Image.open(master)
        needed = math.ceil(max(widths.values()) * DPR)
        targets = rungs_for(needed, img.width)

        emitted = []
        for w in targets:
            h = round(img.height * w / img.width)
            out = VARIANTS / f"{master.stem}-{w}.jpg"
            if not out.exists() or out.stat().st_mtime < master.stat().st_mtime:
                img.convert("RGB").resize((w, h), Image.LANCZOS).save(
                    out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
            emitted.append((w, out))

        plan[name] = {
            "master": f"{img.width}x{img.height}",
            "needed_at_dpr2": needed,
            "srcset": ", ".join(f"assets/r/{o.name} {w}w" for w, o in emitted),
            "sizes": sizes_for(widths),
            "fallback": f"assets/r/{emitted[-1][1].name}",
            "bytes": sum(o.stat().st_size for _, o in emitted),
        }
        rung_list = "/".join(str(w) for w, _ in emitted)
        print(f"  {name:22} master {img.width:>4}px  needs {needed:>4}px  "
              f"-> {rung_list}")

    return plan


def rewrite(plan: dict) -> list[str]:
    """Add srcset/sizes to every <img> whose src names a planned master.

    The src is repointed at the largest derivative rather than the master, so a
    browser without srcset support still gets a sane file instead of a 2 MB one.
    Re-running is idempotent: any existing srcset/sizes on the tag is dropped
    before the fresh pair goes on.
    """
    touched = []
    for route in PAGES:
        page = ROOT / route
        html = original = page.read_text(encoding="utf-8")

        for name, meta in plan.items():
            tag_re = re.compile(
                r'<img\b(?=[^>]*\bsrc="assets/(?:r/[^"]*|' + re.escape(name) + r')")[^>]*>')

            def patch(m: re.Match) -> str:
                tag = m.group(0)
                stem = re.escape(Path(name).stem)
                if not re.search(r'src="assets/(?:' + stem + r'\.jpg|r/' + stem + r'-\d+\.jpg)"', tag):
                    return tag
                tag = re.sub(r'\s+srcset="[^"]*"', "", tag)
                tag = re.sub(r'\s+sizes="[^"]*"', "", tag)
                tag = re.sub(r'src="assets/[^"]*"', f'src="{meta["fallback"]}"', tag)
                return (tag[:-2].rstrip() +
                        f'\n       srcset="{meta["srcset"]}"'
                        f'\n       sizes="{meta["sizes"]}" />')

            html = tag_re.sub(patch, html)

        if html != original:
            page.write_text(html, encoding="utf-8")
            touched.append(route)
    return touched


def check() -> int:
    problems = 0
    for route in PAGES:
        html = (ROOT / route).read_text(encoding="utf-8")
        bare = re.findall(r'<img\b(?![^>]*srcset)[^>]*src="assets/[^"]*\.jpg"[^>]*>', html)
        missing = [s for s in re.findall(r'srcset="([^"]*)"', html)
                   for part in s.split(",")
                   if not (ROOT / part.strip().split()[0]).exists()]
        print(f"  {route:14} {html.count('srcset=')} responsive img(s), "
              f"{len(bare)} without srcset")
        problems += len(bare) + len(missing)
    print(f"\n{'FAIL' if problems else 'OK'}: {problems} problem(s).")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not any((args.measure, args.build, args.check)):
        ap.error("nothing to do — pass --measure, --build or --check")

    if args.measure:
        measure()
    if args.build:
        plan = build(load_measurements())
        touched = rewrite(plan)
        total = sum(m["bytes"] for m in plan.values())
        print(f"\n{len(plan)} asset(s), {total/1e6:.1f} MB of derivatives")
        print(f"pages updated: {', '.join(touched) or 'none'}")
    if args.check:
        return check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
