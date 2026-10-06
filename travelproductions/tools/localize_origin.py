#!/usr/bin/env python3
"""Construction-time accommodation: resolve absolute source-origin URLs to local paths.

Why this is needed
------------------
The capture stores each response byte-for-byte, so the WordPress/Elementor output
still addresses its own assets absolutely (``https://travelproductions.film/...``).
Served from ``127.0.0.1``, those requests leave the mirror entirely: the browser
fetches them from the live site, and cross-origin font loads are then refused by
CORS. The files are present locally — ``serve.py`` resolves every one of them
through ``mirror-manifest.json.route_map``, including the ``?ver=`` query
variants — they were simply never asked for.

Scope of the change
-------------------
One transformation, applied to captured text assets only: the literal origin
prefix is replaced with ``/`` so the reference becomes root-relative and the
local server answers it. Nothing else is touched — no copy, no markup, no
layout, no media selection, no behaviour. Every rewritten byte is recoverable
because the pre-edit file is copied to ``mirror-pristine/`` first (and the
manifest independently records each file's source URL and sha256).

Provenance is appended to ``mirror-manifest.json.local_modifications`` with
``phase: construction``, per the skill's accommodation rule.

Usage
-----
    python3 tools/localize_origin.py mirror            # apply
    python3 tools/localize_origin.py mirror --check     # report only, change nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

ORIGIN = "https://travelproductions.film"
# Protocol-relative form appears in some Elementor/WordPress inline JSON.
ORIGIN_SCHEMELESS = "//travelproductions.film"
TEXT_SUFFIXES = (".html", ".css", ".js", ".json")
ACTOR = "nt-site-mirror operator (localize_origin.py)"


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rewrite(text: str) -> tuple[str, int]:
    """Return the localized text and the number of references resolved.

    Escaped JSON forms (``https:\\/\\/travelproductions.film``) are handled too;
    WordPress inline settings blobs use them heavily, and missing them would
    leave live-origin fetches behind exactly where they are hardest to see.
    """
    replacements = (
        (ORIGIN + "/", "/"),
        (ORIGIN, ""),
        ("https:\\/\\/travelproductions.film\\/", "\\/"),
        ("https:\\/\\/travelproductions.film", ""),
        (ORIGIN_SCHEMELESS + "/", "/"),
    )
    count = 0
    for needle, value in replacements:
        found = text.count(needle)
        if found:
            text = text.replace(needle, value)
            count += found
    return text, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mirror", help="mirror root containing mirror-manifest.json")
    parser.add_argument("--check", action="store_true", help="report without writing")
    parser.add_argument(
        "--pristine",
        default=None,
        help="directory for pre-edit copies (default: <mirror>/../mirror-pristine)",
    )
    args = parser.parse_args()

    mirror = os.path.abspath(args.mirror)
    manifest_path = os.path.join(mirror, "mirror-manifest.json")
    if not os.path.isfile(manifest_path):
        print("No mirror-manifest.json under %s" % mirror, file=sys.stderr)
        return 2
    pristine = os.path.abspath(
        args.pristine or os.path.join(mirror, os.pardir, "mirror-pristine")
    )

    edits: list[dict] = []
    total_refs = 0
    for root, _dirs, files in os.walk(mirror):
        for name in sorted(files):
            if not name.endswith(TEXT_SUFFIXES):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, mirror)
            if rel == "mirror-manifest.json":
                continue
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as handle:
                original = handle.read()
            updated, refs = rewrite(original)
            if not refs or updated == original:
                continue
            total_refs += refs
            record = {
                "path": rel,
                "references_resolved": refs,
                "sha256_before": sha256_file(path),
            }
            if not args.check:
                backup = os.path.join(pristine, rel)
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                if not os.path.exists(backup):
                    shutil.copy2(path, backup)
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as handle:
                    handle.write(updated)
                record["sha256_after"] = sha256_file(path)
                record["pristine_copy"] = os.path.relpath(backup, mirror)
            edits.append(record)

    print(
        "%s %d file(s), %d absolute source-origin reference(s)"
        % ("Would localize" if args.check else "Localized", len(edits), total_refs)
    )
    if args.check or not edits:
        return 0

    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest.setdefault("local_modifications", []).append(
        {
            "phase": "construction",
            "actor": ACTOR,
            "tool": "tools/localize_origin.py",
            "applied_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "reason": (
                "Captured WordPress/Elementor output addresses its own assets at the "
                "absolute source origin. Served from loopback those requests leave the "
                "mirror and cross-origin font loads are refused by CORS, so the local "
                "baseline could not render its own typography or media. Every target is "
                "already present locally and resolvable through route_map."
            ),
            "change": (
                "Replaced the literal source-origin prefix (plain, escaped-JSON and "
                "protocol-relative forms) with a root-relative path in captured "
                "text assets. No copy, markup, layout, media selection or behaviour "
                "was altered."
            ),
            "scope": "captured .html/.css/.js/.json under the mirror root",
            "reproducible_with": "python3 tools/localize_origin.py mirror",
            "pristine_copies": os.path.relpath(pristine, mirror),
            "validation_evidence": (
                "Re-run viewports.py over the declared route x viewport matrix and "
                "confirm no request targets the source origin."
            ),
            "files": edits,
        }
    )
    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=False)
        handle.write("\n")
    os.replace(tmp, manifest_path)
    print("Recorded provenance in mirror-manifest.json.local_modifications")
    print("Pristine pre-edit copies: %s" % pristine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
