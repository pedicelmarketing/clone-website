#!/usr/bin/env python3
"""Turn the captured mirror into the padel academy's route structure.

Two jobs, both mechanical and both repeatable:

1. **Move the routes.** The source is a Spanish WordPress site at ``/es/<slug>/_/``;
   the deliverable is a seven-route English site. Each captured document moves to
   its new home and every internal link is rewritten to match.

2. **Make the assets plain-hostable.** Elementor addresses its assets with
   ``?ver=`` cache-busting queries, and the capture stored those under
   collision-safe filenames (``post-286__q_81c2868f7aedaa02.css``). The mirror
   only resolved them because ``serve.py`` consulted the manifest's route map.
   A client deliverable has to work on ordinary static hosting, so every such
   reference is rewritten to the real filename it already points at on disk.

Nothing here touches copy, layout or media — that is the next step, and it is
kept separate on purpose so this pass stays reviewable.

Usage:
    python3 tools/restructure.py site            # apply
    python3 tools/restructure.py site --check    # report only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from urllib.parse import urlsplit

# Source route -> new route. Order matters: longer paths first so a prefix
# replacement can never eat a longer sibling.
ROUTES = [
    ("/es/sobre-nosotros/", "/coaches/"),
    ("/es/condiciones-legales/", None),   # dropped from the brief
    ("/es/escena-3d/", "/marbella/"),
    ("/es/servicios/", "/coaching/"),
    ("/es/trabajos/", "/programmes/"),
    ("/es/contacto/", "/contact/"),
    ("/es/inicio/", "/"),
]

TEXT_SUFFIXES = (".html", ".css", ".js", ".json")


def build_asset_map(mirror: str) -> dict[str, str]:
    """Map every captured URL's path+query to the local file that holds it."""
    with open(os.path.join(mirror, "mirror-manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    mapping: dict[str, str] = {}
    for entry in manifest.get("downloaded", []):
        url, path = entry.get("url"), entry.get("path")
        if not url or not path:
            continue
        parts = urlsplit(url)
        if parts.netloc != "travelproductions.film":
            continue
        ref = parts.path + (("?" + parts.query) if parts.query else "")
        mapping[ref] = "/" + path
    return mapping


def move_routes(mirror: str, check: bool) -> list[str]:
    notes = []
    for old, new in ROUTES:
        src = os.path.join(mirror, old.strip("/").replace("/", os.sep), "_", "index.html")
        if not os.path.isfile(src):
            notes.append("missing, skipped: %s" % old)
            continue
        if new is None:
            notes.append("DROP  %s" % old)
            if not check:
                shutil.rmtree(os.path.join(mirror, "es", old.strip("/").split("/")[-1]),
                              ignore_errors=True)
            continue
        dst_dir = mirror if new == "/" else os.path.join(mirror, new.strip("/"))
        dst = os.path.join(dst_dir, "index.html")
        notes.append("MOVE  %-26s -> %s" % (old, new))
        if not check:
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src, dst)
    if not check:
        shutil.rmtree(os.path.join(mirror, "es"), ignore_errors=True)
    return notes


def rewrite_text(text: str, assets: dict[str, str]) -> tuple[str, int, int]:
    """Resolve ?ver= asset references, then repoint internal routes."""
    asset_hits = 0

    def sub_asset(match: re.Match) -> str:
        nonlocal asset_hits
        ref = match.group(0)
        local = assets.get(ref)
        if local:
            asset_hits += 1
            return local
        # No query variant on record: drop the cache-buster rather than leave a
        # reference the static host will 404 on.
        bare = ref.split("?", 1)[0]
        if assets.get(bare):
            asset_hits += 1
            return assets[bare]
        return bare

    text = re.sub(r"/(?:wp-content|wp-includes)/[^\"'()\s>]*?\?ver=[^\"'()\s>]*", sub_asset, text)

    route_hits = 0
    for old, new in ROUTES:
        if new is None:
            continue
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            route_hits += count
    return text, asset_hits, route_hits


def add_bare_aliases(mirror: str, check: bool) -> None:
    """Hard-link every hashed asset to its plain filename.

    Elementor builds some asset URLs at runtime with its own ``?ver=`` value,
    so no static rewrite can catch them — ``dialog.min.js`` is one. Static hosts
    ignore the query when resolving a file, so a plain-named copy answers every
    version variant at once. Hard links, so this costs no extra disk.

    A plain name claimed by two different hashed files is ambiguous; those are
    reported and skipped rather than resolved by guesswork.
    """
    claims: dict[str, list[str]] = {}
    for root, _dirs, names in os.walk(mirror):
        for name in names:
            if "__q_" not in name:
                continue
            base, _, ext = name.rpartition(".")
            plain = base.split("__q_")[0] + "." + ext
            claims.setdefault(os.path.join(root, plain), []).append(os.path.join(root, name))

    made = skipped = ambiguous = 0
    for target, sources in sorted(claims.items()):
        if len(sources) > 1:
            ambiguous += 1
            print("  ambiguous, skipped: %s (%d candidates)"
                  % (os.path.relpath(target, mirror), len(sources)))
            continue
        if os.path.exists(target):
            skipped += 1
            continue
        made += 1
        if not check:
            os.link(sources[0], target)
    print("%s %d bare-name alias(es); %d already present, %d ambiguous"
          % ("would add" if check else "added", made, skipped, ambiguous))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mirror")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    mirror = os.path.abspath(args.mirror)

    assets = build_asset_map(mirror)
    print("asset references on record: %d" % len(assets))

    for note in move_routes(mirror, args.check):
        print("  " + note)

    files = a_total = r_total = 0
    for root, _dirs, names in os.walk(mirror):
        for name in sorted(names):
            if not name.endswith(TEXT_SUFFIXES) or name == "mirror-manifest.json":
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="surrogateescape") as fh:
                original = fh.read()
            updated, a, r = rewrite_text(original, assets)
            if updated == original:
                continue
            files += 1
            a_total += a
            r_total += r
            if not args.check:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(updated)

    add_bare_aliases(mirror, args.check)

    verb = "would rewrite" if args.check else "rewrote"
    print("%s %d file(s): %d asset reference(s), %d route link(s)"
          % (verb, files, a_total, r_total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
