#!/usr/bin/env python3
"""Change the contact address shown across the site.

The address appears in mailto: hrefs, in visible link text, in the footer of
every page, and in js/contact.js. Doing it by hand across four pages invites a
half-finished swap where the visible text and the mailto: disagree — so this
does all of them at once and verifies the result.

    python3 tools/set_contact_email.py info@nexumpadel.es
    python3 tools/set_contact_email.py --show

Case is preserved as written in the argument. The old address is matched
case-insensitively, because the site carried it capitalised inconsistently
(Infopremiumpadelacademy@… in text, lowercase in some hrefs).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TARGETS = ("*.html", "js/*.js")


def files(root: Path) -> list[Path]:
    out: list[Path] = []
    for pattern in TARGETS:
        out.extend(sorted(root.glob(pattern)))
    return out


def current(root: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    for path in files(root):
        for match in EMAIL_RE.findall(path.read_text(encoding="utf-8")):
            found[match] = found.get(match, 0) + 1
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("email", nargs="?")
    ap.add_argument("--root", default="site-v2")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    root = PROJECT / args.root
    if not root.is_dir():
        sys.exit(f"FATAL: {root} is not a directory")

    before = current(root)
    if args.show or not args.email:
        for addr, n in sorted(before.items(), key=lambda kv: -kv[1]):
            print(f"  {addr:44} {n}")
        return 0

    new = args.email
    if not EMAIL_RE.fullmatch(new):
        sys.exit(f"FATAL: {new!r} is not a valid email address")

    olds = [a for a in before if a.lower() != new.lower()]
    if not olds:
        print(f"Already {new} everywhere — nothing to do.")
        return 0
    if len(olds) > 1:
        sys.exit(f"FATAL: more than one address present {olds}; "
                 f"resolve by hand so nothing is swapped by accident")
    old = olds[0]

    print(f"==> {old}  ->  {new}")
    total = 0
    for path in files(root):
        text = path.read_text(encoding="utf-8")
        swapped = re.sub(re.escape(old), new, text, flags=re.I)
        n = len(re.findall(re.escape(old), text, flags=re.I))
        if n:
            path.write_text(swapped, encoding="utf-8")
            print(f"    {path.relative_to(root)}: {n}")
            total += n

    after = current(root)
    stale = [a for a in after if a.lower() == old.lower()]
    if stale:
        sys.exit(f"FATAL: {old} still present after the swap")
    if after.get(new, 0) != total:
        sys.exit(f"FATAL: expected {total} occurrences of {new}, found {after.get(new, 0)}")

    print(f"\n{total} occurrence(s) updated; {new} is now the only address on the site.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
