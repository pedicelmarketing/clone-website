#!/usr/bin/env python3
"""Render the social links block in the footer of every page.

Riki asked for the academy's Instagram alongside the contact address
("Y cambiar correos electrónicos y añadir Instagram de página", 2026-08-03).
The block is identical on all four routes, so it is generated from one manifest
(site-v2/assets/socials.json) between <!-- social:start --> and
<!-- social:end --> markers — same pattern as tools/partner_logos.py, so
re-rendering is idempotent and never touches the rest of the page.

Adding a network means adding an entry to socials.json with a matching glyph in
ICONS below; nothing else changes.

    python3 tools/social_links.py --render
    python3 tools/social_links.py --check     # exit 1 if a page is out of sync

Stdlib only, to match the rest of the tooling in this repo.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PAGES = ("index.html", "clubs.html", "camps.html", "contacto.html",
         "privacidad.html")

START = "      <!-- social:start -->"
END = "      <!-- social:end -->"

# Anchor: the close of the footer's last column. The block lands AFTER the
# contact <ul>, not inside it — the previous anchor started at "</ul>" and so
# inserted <ul class="socials"> as a direct child of another <ul>, which is
# invalid HTML. This exact markup is on all four pages (verified by --check).
ANCHOR = """    </div>
  </div>
  <div class="container footer-bottom">"""

# Single-path glyphs, drawn on a 24x24 box to match the icons already in the
# build (camps.html features). No external icon font.
ICONS = {
    "instagram": (
        '<rect x="3" y="3" width="18" height="18" rx="5.4" />'
        '<circle cx="12" cy="12" r="4.1" />'
        '<circle cx="17.2" cy="6.8" r="1.2" fill="currentColor" stroke="none" />'
    ),
    "tiktok": (
        '<path d="M14 3v11.4a3.4 3.4 0 1 1-2.8-3.35" />'
        '<path d="M14 3c.4 2.4 2 4 4.6 4.2" />'
    ),
    "facebook": (
        '<path d="M14.6 21v-8h2.6l.4-3.1h-3V7.9c0-.9.25-1.5 1.55-1.5h1.6V3.6'
        'c-.3-.04-1.3-.13-2.45-.13-2.42 0-4.1 1.48-4.1 4.2V9.9H8.5V13h2.7v8z" />'
    ),
}

BLOCK = """{start}
      <!-- Redes. Generated from assets/socials.json by tools/social_links.py
           — do not hand-edit; re-render instead. -->
      <ul class="socials">
{items}      </ul>
{end}"""

ITEM = """        <li>
          <a class="social" href="{url}" target="_blank" rel="noopener noreferrer" aria-label="{label}">
            <span class="social-chip" aria-hidden="true"><svg viewBox="0 0 24 24">{icon}</svg></span>
            <span class="social-handle">{handle}</span>
          </a>
        </li>
"""


def esc(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))


def load(root: Path) -> dict:
    path = root / "assets" / "socials.json"
    if not path.exists():
        sys.exit(f"FATAL: {path} missing")
    return json.loads(path.read_text(encoding="utf-8"))


def render(data: dict) -> tuple[str, int]:
    items = ""
    for net in data.get("networks") or []:
        key = net["network"]
        if key not in ICONS:
            sys.exit(f"FATAL: no glyph for network {key!r} — add one to ICONS")
        items += ITEM.format(
            url=esc(net["url"]),
            label=esc(net.get("label") or f"{key.title()}: {net['handle']}"),
            handle=esc(net["handle"]),
            icon=ICONS[key],
        )
    return BLOCK.format(start=START, items=items, end=END), len(data.get("networks") or [])


def apply(root: Path, block: str) -> list[str]:
    touched = []
    existing = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)

    for name in PAGES:
        page = root / name
        if not page.exists():
            sys.exit(f"FATAL: {page} missing")
        html = page.read_text(encoding="utf-8")

        if existing.search(html):
            out = existing.sub(lambda _: block, html, count=1)
        else:
            if ANCHOR not in html:
                sys.exit(f"FATAL: footer anchor not found in {name} — "
                         "the footer markup drifted; re-check ANCHOR")
            out = html.replace(ANCHOR, f"{block}\n{ANCHOR}", 1)

        if out != html:
            page.write_text(out, encoding="utf-8")
            touched.append(name)

        final = page.read_text(encoding="utf-8")
        if final.count(START) != 1 or final.count(END) != 1:
            sys.exit(f"FATAL: {name} has {final.count(START)} social blocks")
        if final.index(START) < final.index("<footer"):
            sys.exit(f"FATAL: social block landed outside the footer in {name}")

    return touched


def check(root: Path, data: dict) -> int:
    expected, n = render(data)
    problems = 0
    for name in PAGES:
        html = (root / name).read_text(encoding="utf-8")
        if expected not in html:
            print(f"  {name:14} OUT OF SYNC — re-run --render")
            problems += 1
        else:
            print(f"  {name:14} {n} network(s), in sync")
    print(f"\n{'FAIL' if problems else 'OK'}: {problems} problem(s).")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site-v2")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    root = PROJECT / args.root
    data = load(root)

    if args.check and not args.render:
        return check(root, data)
    if not args.render:
        ap.error("nothing to do — pass --render or --check")

    block, n = render(data)
    touched = apply(root, block)
    print(f"rendered {n} network(s)")
    print(f"pages updated: {', '.join(touched) if touched else 'none (already current)'}")
    return check(root, data) if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
