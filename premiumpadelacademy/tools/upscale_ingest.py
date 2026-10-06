#!/usr/bin/env python3
"""Verify and install ESRGAN-upscaled site images.

Riki asked for better photo resolution ("Resolucion de fotos y logo"). The
upscales are produced on Comfy Cloud (see reports/upscale-report.md for the
graph) and land in upscale/staging/<asset-stem>.png. This script is the gate
between that staging directory and site-v2/assets/.

Two checks stand between a staged file and the live site, both from HANDOFF §8
trap 4 — a file supplied as an "upscale" once turned out to be a downgrade:

  1. DIMENSIONS must strictly increase. A smaller or equal replacement is
     rejected, whatever the filename claims.
  2. PERCEPTUAL HASH must match the original within a tight threshold. An
     upscaler is meant to add detail to the SAME photograph; a large hash
     distance means it returned a different or heavily hallucinated picture,
     which must never be published as the client's own photo.

Originals are copied to upscale/originals/ before anything is overwritten, so
every install is reversible. The intrinsic width/height attributes in the HTML
are rewritten to match the new files, because a stale attribute pair causes
layout shift.

    python3 tools/upscale_ingest.py --check     # report only, touch nothing
    python3 tools/upscale_ingest.py --install

Needs Pillow, so run it with the venv interpreter:
    ~/.venvs/nt-mirror/bin/python tools/upscale_ingest.py --check
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("FATAL: Pillow missing — use ~/.venvs/nt-mirror/bin/python")

Image.MAX_IMAGE_PIXELS = None

PROJECT = Path(__file__).resolve().parent.parent
ASSETS = PROJECT / "site-v2" / "assets"
STAGING = PROJECT / "upscale" / "staging"
BACKUP = PROJECT / "upscale" / "originals"
PAGES = ("index.html", "clubs.html", "camps.html", "contacto.html")

# JPEG quality for the installed files. 88 keeps the ESRGAN detail that the
# whole exercise is for; below ~85 the recovered texture starts re-blurring.
JPEG_QUALITY = 88

# Maximum difference-hash Hamming distance (out of 1024 bits) still considered
# "the same photograph". Measured across these 12 assets: a true 2x upscale
# scores 0-40; an unrelated image scores in the hundreds.
PHASH_MAX_DISTANCE = 80

# Assets that are byte-identical on disk and share one upscale output.
# elite-inset was such a case until 2026-08-03, when it was replaced with the
# Marbella court photograph at Riki's request ("Foto de grupo por foto de
# pista"). It is now a distinct image and must NOT be aliased to club-2, or a
# re-run would silently overwrite the court shot with the consultancy photo.
ALIASES: dict[str, str] = {}


def phash_bits(img: Image.Image, side: int = 32) -> list[int]:
    """1024-bit difference hash: each bit compares a pixel to its right neighbour.

    Deliberately NOT an average hash. Average hash thresholds every pixel
    against the frame mean, so a small global tone shift flips every pixel that
    sits near it. coach-riki.jpg is mostly one flat green backdrop pinned at the
    mean, and a 4-level luminance change between the original and its upscale
    scored 132 — a false "different image" on a verifiably identical photo.
    Comparing neighbours instead makes the hash invariant to that shift while
    still catching a genuinely different picture.
    """
    small = img.convert("L").resize((side + 1, side), Image.LANCZOS)
    px = list(small.getdata())
    bits = []
    for row in range(side):
        base = row * (side + 1)
        bits += [1 if px[base + col] > px[base + col + 1] else 0 for col in range(side)]
    return bits


def distance(a: list[int], b: list[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


def verify(original: Path, staged: Path) -> tuple[bool, str, dict]:
    o, s = Image.open(original), Image.open(staged)
    info = {
        "original_size": f"{o.width}x{o.height}",
        "upscaled_size": f"{s.width}x{s.height}",
        "scale": round(s.width / o.width, 3),
    }

    if s.width <= o.width or s.height <= o.height:
        return False, (f"REJECT not larger: {o.width}x{o.height} -> "
                       f"{s.width}x{s.height}"), info

    d = distance(phash_bits(o), phash_bits(s))
    info["phash_distance"] = d
    if d > PHASH_MAX_DISTANCE:
        return False, f"REJECT different image: hash distance {d} > {PHASH_MAX_DISTANCE}", info

    return True, f"ok  {info['original_size']} -> {info['upscaled_size']}  (hash {d})", info


def install(stem: str, staged: Path, dest: Path) -> dict:
    BACKUP.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not (BACKUP / dest.name).exists():
        shutil.copy2(dest, BACKUP / dest.name)

    img = Image.open(staged).convert("RGB")
    img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return {"file": dest.name, "width": img.width, "height": img.height,
            "bytes": dest.stat().st_size}


def sync_html_dimensions(installed: dict[str, dict]) -> list[str]:
    """Rewrite width=/height= on <img> tags whose src we just replaced.

    A stale intrinsic size is not cosmetic: the browser reserves the wrong box
    and the page jumps when the real image arrives.
    """
    touched = []
    for name in PAGES:
        page = PROJECT / "site-v2" / name
        html = original = page.read_text(encoding="utf-8")

        for fname, meta in installed.items():
            pattern = re.compile(
                r'(<img[^>]*src="assets/' + re.escape(fname) + r'"[^>]*?)'
                r'width="\d+"(\s+)height="\d+"')
            html = pattern.sub(
                lambda m: f'{m.group(1)}width="{meta["width"]}"'
                          f'{m.group(2)}height="{meta["height"]}"', html)

        if html != original:
            page.write_text(html, encoding="utf-8")
            touched.append(name)
    return touched


def write_provenance(records: list[dict], model: dict[str, str]) -> None:
    path = ASSETS / "media-provenance.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(data, dict):
        data = {"_previous": data}

    data["upscale_2x"] = {
        "date": "2026-08-03",
        "reason": "Client feedback 2026-08-03: 'Resolucion de fotos y logo'.",
        "pipeline": ("Comfy Cloud: LoadImage -> ImageUpscaleWithModel (4x) -> "
                     "ImageScale lanczos to 2x -> SaveImage; re-encoded here as "
                     f"progressive JPEG q{JPEG_QUALITY}."),
        "models": model,
        "verification": ("Each output checked against its original for strictly "
                         "larger dimensions and difference-hash distance "
                         f"<= {PHASH_MAX_DISTANCE}/1024 before install."),
        "originals_kept_in": "upscale/originals/",
        "classification": "Original (same photograph, resampled) — not regenerated content.",
        "assets": records,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--install", action="store_true")
    args = ap.parse_args()
    if not (args.check or args.install):
        ap.error("nothing to do — pass --check or --install")

    jobs = []
    for dest in sorted(ASSETS.glob("*.jpg")):
        stem = dest.stem
        staged = STAGING / f"{ALIASES.get(stem, stem)}.png"
        if staged.exists():
            jobs.append((stem, staged, dest))

    if not jobs:
        sys.exit(f"FATAL: nothing staged in {STAGING}")

    records, failures, installed = [], 0, {}
    for stem, staged, dest in jobs:
        ok, msg, info = verify(dest, staged)
        alias = "  (shared upscale)" if stem in ALIASES else ""
        print(f"  {stem:16} {msg}{alias}")
        if not ok:
            failures += 1
            continue
        if args.install:
            meta = install(stem, staged, dest)
            installed[dest.name] = meta
            info["installed_bytes"] = meta["bytes"]
        records.append({"asset": dest.name, **info})

    if failures:
        print(f"\nFAIL: {failures} asset(s) rejected — nothing further was written.")
        return 1

    if args.install:
        touched = sync_html_dimensions(installed)
        model = {"photographs": "4x-UltraSharp.safetensors",
                 "coach portraits": "4x-ClearRealityV1.pth"}
        write_provenance(records, model)
        print(f"\ninstalled {len(records)} asset(s); "
              f"html dimensions synced in: {', '.join(touched) or 'none'}")

    print(f"\nOK: {len(records)} asset(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
