#!/usr/bin/env python3
"""Fetch the brand's REAL photography locally (local-first asset strategy).

Why local-first
---------------
The operator chose local-first over CDN or hotlinking: copy the brand's images
into the project and optimise at build time. No vendor account, no runtime
dependency on someone else's CDN staying up, and the deliverable is
self-contained. The cost is repo size and an explicit fetch step — this script.

Why it exists at all
--------------------
The pipeline rendered pages with ZERO images for its entire life, because the
first brand's site was WAF-blocked so its brief had almost no usable photography.
A site with no real photography cannot beat a real reference site regardless of
how good the layout is.

Honesty rules (consistent with the rest of the pipeline)
-------------------------------------------------------
- Only downloads URLs listed in the brand brief's `real_photo_inventory`. It
  never goes looking for images elsewhere.
- Verifies each download is really an image (magic bytes), not an HTML error
  page served with a 200 — a common failure that silently yields broken pages.
- Records provenance per asset: source URL, brand-brief licence string, bytes,
  dimensions, sha256. Assets whose licence is not brand-owned are downloaded but
  FLAGGED so a later step can decide whether to ship them.
- Reports failures loudly and exits nonzero if nothing could be fetched.
"""

import argparse
import hashlib
import json
import struct
import sys
import urllib.error
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) web-designer-asset-fetch/1.0"

MAGIC = [
    (b"\xff\xd8\xff", ".jpg", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png", "png"),
    (b"GIF87a", ".gif", "gif"),
    (b"GIF89a", ".gif", "gif"),
    (b"RIFF", ".webp", "webp"),
    (b"<svg", ".svg", "svg"),
    (b"<?xml", ".svg", "svg"),
]


def sniff(data: bytes):
    head = data[:16].lstrip()
    for prefix, ext, name in MAGIC:
        if data.startswith(prefix) or head.startswith(prefix):
            if name == "webp" and b"WEBP" not in data[:16]:
                continue
            return ext, name
    return None


def dimensions(data: bytes, kind: str):
    """Best-effort intrinsic size without pulling in Pillow."""
    try:
        if kind == "png" and len(data) > 24:
            w, h = struct.unpack(">II", data[16:24])
            return int(w), int(h)
        if kind == "jpeg":
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return int(w), int(h)
                seg = struct.unpack(">H", data[i + 2:i + 4])[0]
                i += 2 + seg
        if kind == "webp" and b"VP8 " in data[:40]:
            idx = data.index(b"VP8 ") + 14
            w = struct.unpack("<H", data[idx:idx + 2])[0] & 0x3FFF
            h = struct.unpack("<H", data[idx + 2:idx + 4])[0] & 0x3FFF
            return int(w), int(h)
    except Exception:  # noqa: BLE001 - dimensions are informational only
        return None
    return None


def fetch(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand-brief", required=True)
    ap.add_argument("-o", "--out", required=True,
                    help="directory for images + ASSET-MANIFEST.json")
    ap.add_argument("--max", type=int, default=0, help="cap asset count (0 = all)")
    args = ap.parse_args(argv)

    brief_path = Path(args.brand_brief).resolve()
    if not brief_path.is_file():
        raise SystemExit(f"brand brief not found: {brief_path}")
    brief = json.loads(brief_path.read_text(encoding="utf-8"))

    inventory = brief.get("real_photo_inventory") or []
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if not inventory:
        # Not an error: an honest brief for a blocked brand legitimately has none.
        # Say so clearly rather than emitting an empty dir that looks "fetched".
        print("brand brief lists NO real photos (real_photo_inventory empty). "
              "Nothing to fetch — the site will render without brand photography.",
              file=sys.stderr)
        (out / "ASSET-MANIFEST.json").write_text(json.dumps({
            "schema_version": "1.0", "brand_brief": str(brief_path),
            "counts": {"requested": 0, "fetched": 0, "failed": 0},
            "not_brand_owned": [], "assets": [], "failed": [],
            "note": "brand brief contained no real_photo_inventory entries",
        }, indent=2) + "\n")
        print(str(out))
        return 0

    if args.max:
        inventory = inventory[:args.max]

    assets, failed = [], []
    for i, entry in enumerate(inventory, 1):
        url = entry.get("url")
        subject = entry.get("subject") or ""
        license_str = entry.get("license") or "unknown"
        if not url:
            failed.append({"index": i, "reason": "entry has no url"})
            continue
        try:
            data = fetch(url)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            failed.append({"index": i, "url": url, "reason": f"fetch failed: {exc}"})
            print(f"  [{i}/{len(inventory)}] FAILED {url[:66]} — {exc}", file=sys.stderr)
            continue

        kind = sniff(data)
        if kind is None:
            # A 200 that isn't an image is the classic silent failure: an HTML
            # error/consent page saved as .jpg yields a broken <img> later.
            failed.append({"index": i, "url": url, "bytes": len(data),
                           "reason": "not an image (magic-byte check failed)"})
            print(f"  [{i}/{len(inventory)}] NOT AN IMAGE {url[:60]}", file=sys.stderr)
            continue

        ext, name = kind
        digest = hashlib.sha256(data).hexdigest()
        fname = f"{i:02d}-{digest[:10]}{ext}"
        (out / fname).write_bytes(data)
        dims = dimensions(data, name)
        brand_owned = "brand-owned" in license_str.lower()
        assets.append({
            "file": fname, "source_url": url, "subject": subject,
            "license": license_str, "brand_owned": brand_owned,
            "format": name, "bytes": len(data),
            "width": dims[0] if dims else None,
            "height": dims[1] if dims else None,
            "sha256": digest,
        })
        flag = "" if brand_owned else "  [LICENCE not brand-owned — review before shipping]"
        size = f", {dims[0]}x{dims[1]}" if dims else ""
        print(f"  [{i}/{len(inventory)}] ok {fname} ({len(data)//1024} KB{size}){flag}",
              file=sys.stderr)

    manifest = {
        "schema_version": "1.0",
        "brand_brief": str(brief_path),
        "counts": {"requested": len(inventory), "fetched": len(assets),
                   "failed": len(failed)},
        "not_brand_owned": [a["file"] for a in assets if not a["brand_owned"]],
        "assets": assets,
        "failed": failed,
    }
    (out / "ASSET-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\n{len(assets)}/{len(inventory)} assets fetched -> {out}", file=sys.stderr)
    if not assets:
        raise SystemExit("no assets could be fetched; refusing to report success")
    print(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
