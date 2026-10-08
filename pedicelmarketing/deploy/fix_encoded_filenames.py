#!/usr/bin/env python3
"""Phase A5b - reconcile percent-encoded filenames with how web servers resolve paths.

Construction-time accommodation (nt-site-mirror SKILL.md, 'local path/origin resolution').
No content, branding, layout or behaviour change - only on-disk names.

The problem: mirror_assets.py stores an asset using the raw URL path, so
".../Careers%20Image.webp" lands on disk with a literal three-character "%20" in the
filename. Every web server (the skill's serve.py, and nginx in production) URL-decodes the
request path *before* the filesystem lookup, so it looks for "Careers Image.webp" - which
does not exist. Result: a silent 404 on 51 assets that were downloaded successfully.

The fix: rename each file to the single-URL-decoded form, which is exactly what a server
resolves the reference to. Markup is left untouched - "%20" in an href is the correct
canonical URL form and matches what Webflow itself served.

Double-encoded names behave correctly under the same rule: "...strategy%2520(1).webp"
decodes once to "...strategy%20(1).webp", which is what the browser will request.

The manifest's source_url_map local_path values are updated to match, and the rename is
recorded in mirror-manifest.json#local_modifications with full provenance.

Run with --check to preview.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import unquote


def plan_renames(mirror: str) -> list[tuple[str, str]]:
    """Bottom-up so a directory is only renamed after its children."""
    pairs: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(mirror, topdown=False):
        for name in files + dirs:
            if "%" not in name:
                continue
            decoded = unquote(name)
            if decoded == name or not decoded or "/" in decoded:
                continue
            pairs.append((os.path.join(root, name), os.path.join(root, decoded)))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mirror")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    mirror = os.path.abspath(args.mirror)
    pairs = plan_renames(mirror)
    print(f"percent-encoded names found: {len(pairs)}")

    renamed, collided, skipped = 0, [], 0
    for src, dst in pairs:
        if os.path.exists(dst):
            # Both forms present: the decoded one is what the server will serve, so keep it
            # and leave the encoded duplicate rather than destroying either.
            collided.append(os.path.relpath(dst, mirror))
            skipped += 1
            continue
        if args.check:
            renamed += 1
            continue
        os.rename(src, dst)
        renamed += 1

    print(f"renamed : {renamed}{' (dry run)' if args.check else ''}")
    print(f"skipped : {skipped} (target already existed)")
    for path in collided[:5]:
        print(f"    collision: {path}")

    if args.check or not renamed:
        return 0

    # Keep the manifest honest: local_path must describe where the file actually is.
    manifest_path = os.path.join(mirror, "mirror-manifest.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)

    updated = 0
    for url, info in (manifest.get("source_url_map") or {}).items():
        if isinstance(info, dict) and "%" in (info.get("local_path") or ""):
            decoded = unquote(info["local_path"])
            if decoded != info["local_path"]:
                info["local_path"] = decoded
                updated += 1
    for entry in manifest.get("downloaded") or []:
        if "%" in (entry.get("path") or ""):
            entry["path"] = unquote(entry["path"])

    manifest.setdefault("local_modifications", []).append({
        "phase": "construction",
        "actor": "deploy/fix_encoded_filenames.py",
        "file": "_external/**",
        "reason": (
            "mirror_assets.py stores assets under the raw URL path, leaving a literal '%20' "
            "in filenames. Web servers URL-decode the request path before the filesystem "
            "lookup, so those assets 404 despite having downloaded successfully "
            "(51 distinct 404s observed in the local serve.py access log). Renamed each to "
            "its single-URL-decoded form so the reference in the markup resolves. Markup is "
            "unchanged - '%20' in an href remains the correct canonical URL form."
        ),
        "before": "example: _external/.../64a2995238dba40820b377b0_Careers%20Image.webp",
        "after": "example: _external/.../64a2995238dba40820b377b0_Careers Image.webp",
        "files_renamed": renamed,
        "source_url_map_entries_updated": updated,
        "validation": "re-run deploy/rewrite_refs.py gates + local 404-log sweep",
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    os.replace(tmp, manifest_path)
    print(f"manifest: {updated} source_url_map paths updated, local_modifications recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
