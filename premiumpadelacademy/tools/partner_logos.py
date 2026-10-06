#!/usr/bin/env python3
"""Render the 'Colaboradores' logo band at the bottom of every page.

The band is identical on all four routes, so it is generated from one manifest
(site-v2/assets/partners.json) rather than hand-edited four times. The markup
lives between <!-- partners:start --> and <!-- partners:end --> markers, so
re-rendering is idempotent and never touches the rest of the page.

Slots beyond the logos listed render as marked empty placeholders — that is what
reserves the space the client asked for. They carry data-placeholder="true" so a
pre-publish gate can find them, exactly like the demo-review tagging.

    python3 tools/partner_logos.py --render
    python3 tools/partner_logos.py --add ~/logo.svg --name "Club X" --url https://…
    python3 tools/partner_logos.py --check              # exit 1 if an asset is missing
    python3 tools/partner_logos.py --render --no-placeholders   # public build

Stdlib only, to match the rest of the tooling in this repo.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PAGES = ("index.html", "clubs.html", "camps.html", "contacto.html")

START = "      <!-- partners:start -->"
END = "      <!-- partners:end -->"

# Rendered between the markers. Kept at the same indent as the surrounding
# sections so the emitted HTML reads like the hand-written markup around it.
BAND = """{start}
      <!-- Colaboradores. Generated from assets/partners.json by
           tools/partner_logos.py — do not hand-edit; re-render instead. -->
      <section class="partners" aria-labelledby="partners-title">
        <div class="container">
          <div class="partners-head" data-anim="rise">
            <p class="eyebrow" id="partners-title">Colaboradores</p>
            <span class="rule"></span>
          </div>
          <ul class="partners-grid stagger">
{tiles}          </ul>
        </div>
      </section>
{end}"""

LOGO_TILE = """            <li class="partner">
              <a href="{url}" target="_blank" rel="noopener noreferrer">
                <img src="assets/{file}" alt="{name}" height="{height}" loading="lazy" />
              </a>
            </li>
"""

LOGO_TILE_NOLINK = """            <li class="partner">
              <img src="assets/{file}" alt="{name}" height="{height}" loading="lazy" />
            </li>
"""

SLOT_TILE = """            <li class="partner is-empty" data-placeholder="true">
              <span>Espacio disponible</span>
            </li>
"""


def esc(value: str) -> str:
    """Escape for an HTML attribute value."""
    return (value.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))


def slugify(name: str) -> str:
    ascii_name = (unicodedata.normalize("NFKD", name)
                  .encode("ascii", "ignore").decode("ascii"))
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "logo"


def load(root: Path) -> dict:
    path = root / "assets" / "partners.json"
    if not path.exists():
        sys.exit(f"FATAL: {path} missing")
    return json.loads(path.read_text(encoding="utf-8"))


def save(root: Path, data: dict) -> None:
    path = root / "assets" / "partners.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def render(data: dict, placeholders: bool = True) -> tuple[str, int, int]:
    logos = data.get("logos") or []
    tiles = ""
    for logo in logos:
        template = LOGO_TILE if logo.get("url") else LOGO_TILE_NOLINK
        tiles += template.format(
            url=esc(logo.get("url", "")),
            file=esc(logo["file"]),
            name=esc(logo["name"]),
            height=int(logo.get("height", 26)),
        )

    empty = max(0, int(data.get("slots", 6)) - len(logos)) if placeholders else 0
    tiles += SLOT_TILE * empty
    return BAND.format(start=START, tiles=tiles, end=END), len(logos), empty


def apply(root: Path, band: str) -> list[str]:
    """Insert or replace the band as the last child of <main> on every page."""
    touched = []
    existing = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)

    for name in PAGES:
        page = root / name
        if not page.exists():
            sys.exit(f"FATAL: {page} missing")
        html = page.read_text(encoding="utf-8")

        if existing.search(html):
            out = existing.sub(lambda _: band, html, count=1)
        else:
            if "</main>" not in html:
                sys.exit(f"FATAL: no </main> in {name} — cannot place the band")
            out = html.replace("\n</main>", f"\n\n{band}\n\n</main>", 1)

        if out != html:
            page.write_text(out, encoding="utf-8")
            touched.append(name)

        # Self-check: exactly one band, and it is inside <main>.
        final = page.read_text(encoding="utf-8")
        if final.count(START) != 1 or final.count(END) != 1:
            sys.exit(f"FATAL: {name} has {final.count(START)} bands after render")
        if final.index(START) > final.index("</main>"):
            sys.exit(f"FATAL: band landed outside <main> in {name}")

    return touched


def check(root: Path, data: dict) -> int:
    problems = 0
    for logo in data.get("logos") or []:
        asset = root / "assets" / logo["file"]
        if not asset.exists():
            print(f"  MISSING asset: assets/{logo['file']} ({logo['name']})")
            problems += 1

    for name in PAGES:
        html = (root / name).read_text(encoding="utf-8")
        n = html.count('data-placeholder="true"')
        imgs = html.count('class="partner">')
        print(f"  {name:14} {imgs} logo tile(s), {n} empty slot(s)")
        if html.count(START) != 1:
            print(f"    ERROR: {html.count(START)} band markers")
            problems += 1

    print(f"\n{'FAIL' if problems else 'OK'}: {problems} problem(s).")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site-v2")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-placeholders", action="store_true",
                    help="render only real logos (public build)")
    ap.add_argument("--add", metavar="FILE", help="logo file to add")
    ap.add_argument("--name")
    ap.add_argument("--url", default="")
    ap.add_argument("--height", type=int, default=26)
    args = ap.parse_args()

    root = PROJECT / args.root
    data = load(root)

    if args.add:
        if not args.name:
            sys.exit("--add requires --name")
        src = Path(args.add).expanduser()
        if not src.exists():
            sys.exit(f"FATAL: {src} not found")
        dest_name = f"logo-{slugify(args.name)}{src.suffix.lower()}"
        shutil.copy2(src, root / "assets" / dest_name)
        data.setdefault("logos", []).append({
            "name": args.name, "file": dest_name,
            "url": args.url, "height": args.height,
        })
        if len(data["logos"]) > data.get("slots", 6):
            data["slots"] = len(data["logos"])
        save(root, data)
        print(f"added {args.name} -> assets/{dest_name}")
        args.render = True

    if args.check and not args.render:
        return check(root, data)

    if not args.render:
        ap.error("nothing to do — pass --render, --add or --check")

    band, n_logos, n_empty = render(data, placeholders=not args.no_placeholders)
    touched = apply(root, band)
    print(f"rendered {n_logos} logo(s) + {n_empty} empty slot(s)")
    print(f"pages updated: {', '.join(touched) if touched else 'none (already current)'}")
    return check(root, data) if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
