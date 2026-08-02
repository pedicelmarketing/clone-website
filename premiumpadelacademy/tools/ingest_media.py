#!/usr/bin/env python3
"""Copy the client's own photographs out of the mirror into the site.

Source of truth is the acquisition manifest, not a hand-written path list: every
file here was downloaded through mirror_assets.py and is hashed there. This step
only renames by layout slot, bounds the long edge, strips metadata and re-encodes.

EXIF is dropped deliberately — the originals came off phones and can carry GPS.
"""
import json
import sys
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
MIRROR = PROJECT / "mirror"
OUT = PROJECT / "site" / "assets"

# slot -> Wix media id. Slots are named for where they sit in the layout, so the
# HTML never has to mention a phone filename.
SLOTS = {
    "hero-home":    "b99928_5a996a196dfa41f08433f14a789e99fd~mv2.jpg",
    "coach-riki":   "b99928_d2622b2a02fc4f6f971b3a70e0c63802~mv2.png",
    "coach-juampi": "b99928_29a4cf960a4e4a0283a80fd6562ac0cd~mv2.jpeg",
    "elite":        "b99928_e60aaa6fdaa944728dc3fe0a61908b77~mv2.jpeg",
    "elite-inset":  "b99928_80a668776fb84ff9919d49cba1394994~mv2.jpeg",
    "expect":       "b99928_d3004220c4fb42cf902e0a5cafd4e503~mv2.jpeg",
    "expect-2":     "b99928_e08bd1de02784259b337db0fcc65fc61~mv2.jpeg",
    "hero-clubs":   "11062b_ff94e7c41c3c475b933c8d7835c67ed2~mv2.jpg",
    "club-1":       "b99928_ce35c6530d9f466aaec7c24ed4b6cef5~mv2.jpeg",
    "club-2":       "b99928_80a668776fb84ff9919d49cba1394994~mv2.jpeg",
    "club-3":       "b99928_1701cb938dc0418b8f8ddffc9d10f3ac~mv2.jpeg",
    "club-4":       "11062b_a7fd41d75482484ca10a04dd7e5b0c63~mv2.jpg",
    "hero-camps":   "b99928_b3772c2ecd1c4adf97425f0b23fb948e~mv2.jpeg",
    "camps-band":   "b99928_befb0959142e40289a7ccbde2cbe95a7~mv2.jpeg",
    "camps-method": "b99928_665f8b4a036742b59896ab25b10dfa8a~mv2.jpeg",
    "logo":         "b99928_610058862ab541dfaaa7b12ead80c5a7~mv2.png",
}

MAX_EDGE = 2000
QUALITY = 84

# The logo renders at 114x33; anything past this is dead weight even on retina.
LOGO_MAX_EDGE = 800


def hi_res_path(media_id: str) -> Path | None:
    """The bounded `fit` variant acquired through --extra-urls, if present."""
    ext = ".png" if media_id.endswith(".png") else ".jpg"
    p = MIRROR / "_external/static.wixstatic.com/media" / media_id / "v1/fit/w_2400,h_2400,q_90" / f"hi{ext}"
    return p if p.is_file() else None


def largest_variant(media_id: str) -> Path | None:
    """Fallback: the biggest per-slot variant Wix served during capture."""
    base = MIRROR / "_external/static.wixstatic.com/media" / media_id
    if not base.is_dir():
        return None
    best, best_px = None, -1
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        px = p.stat().st_size
        if px > best_px:
            best, best_px = p, px
    return best


def main() -> int:
    if not MIRROR.is_dir():
        print(f"error: no mirror at {MIRROR} — run mirror_assets.py first", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    written, provenance = [], {}

    for slot, media_id in SLOTS.items():
        src = hi_res_path(media_id) or largest_variant(media_id)
        if src is None:
            print(f"error: no acquired file for slot {slot} ({media_id})", file=sys.stderr)
            return 1

        with Image.open(src) as im:
            im = im.convert("RGBA")
            # Keep PNG only where alpha is actually used. Several of the source
            # photographs are PNGs with a fully opaque alpha channel, which costs
            # megabytes and buys nothing.
            alpha_low, _ = im.getchannel("A").getextrema()
            keep_alpha = alpha_low < 255

            before = im.size
            limit = LOGO_MAX_EDGE if slot == "logo" else MAX_EDGE
            im.thumbnail((limit, limit), Image.LANCZOS)

            if keep_alpha:
                dest = OUT / f"{slot}.png"
                clean = Image.new("RGBA", im.size)
                clean.putdata(list(im.getdata()))
                clean.save(dest, "PNG", optimize=True)
            else:
                dest = OUT / f"{slot}.jpg"
                clean = Image.new("RGB", im.convert("RGB").size)
                clean.putdata(list(im.convert("RGB").getdata()))
                clean.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)

        kb = dest.stat().st_size // 1024
        written.append((slot, before, im.size, kb))
        provenance[dest.name] = {
            "slot": slot,
            "wix_media_id": media_id,
            "acquired_from": str(src.relative_to(PROJECT)),
            "source_pixels": list(before),
            "shipped_pixels": list(im.size),
            "exif_stripped": True,
        }
        print(f"  {slot:14} {before[0]}x{before[1]} -> {im.size[0]}x{im.size[1]}  {kb}KB")

    (OUT / "media-provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    total = sum(w[3] for w in written)
    print(f"\n{len(written)} images -> {OUT.relative_to(PROJECT)}  ({total} KB total)")
    print("provenance: site/assets/media-provenance.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
