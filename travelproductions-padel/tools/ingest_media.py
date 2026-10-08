#!/usr/bin/env python3
"""Replace the stock imagery with the academy's own photographs.

The first media pass filled the emptied slots from Wikimedia Commons. That was
placeholder-grade by design: it carried attribution obligations, and three of
the images were CC BY-SA, whose share-alike terms are a poor fit for a client
site. The academy has since supplied its own photography, so all of it goes.

Every slot name that `apply_media.py` and `prepare_deploy.py` already address
is kept, so nothing downstream has to know the source changed. Three new names
are added for the routes that gained content: `coaches`, `camps`, `courts`.

Each image is:

* re-encoded through Pillow, which drops EXIF — these came off phones, and
  location metadata has no business on a public site;
* bounded to 2200px on the long edge, which is past what any container asks for;
* saved progressive at q82, the point where these particular frames stop
  gaining visible quality.

The licence position inverts completely: these are the client's own files, so
there is nothing to attribute and nothing to share alike. `credits.json` is
rewritten to say exactly that rather than being deleted, because the manifest
is what a later reader checks.

Usage:  python3 tools/ingest_media.py site [--check]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

from PIL import Image

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..",
                       "examples", "riki-coach", "Assets")

MAX_EDGE = 2200
QUALITY = 82

# slot name -> (source file, what it shows)
# The slot names are the ones the layout already references; the descriptions
# are what the frame actually contains, recorded so a later reader can re-place
# an image without opening all 28 originals.
SLOTS = {
    "hero":       ("WhatsApp Image 2026-07-31 at 11.13.53 (4).jpeg",
                   "Wide aerial of the padel complex with the coastline behind"),
    "lessons":    ("WhatsApp Image 2026-07-19 at 16.48.23.jpeg",
                   "Coach working with a group on a blue padel court"),
    "group":      ("WhatsApp Image 2026-07-19 at 16.48.23 (1).jpeg",
                   "Four players at the net with paddles"),
    "technical":  ("WhatsApp Image 2026-07-19 at 16.48.24 (1).jpeg",
                   "Coach and junior player mid-rally"),
    "physical":   ("WhatsApp Image 2026-07-19 at 16.48.24 (2).jpeg",
                   "Player moving to the ball, coach alongside"),
    "match":      ("WhatsApp Image 2026-07-30 at 12.39.29 (3).jpeg",
                   "Competitive match play, lunging to reach the ball"),
    "programmes": ("WhatsApp Image 2026-07-31 at 11.13.52.jpeg",
                   "Aerial of the club with players across several courts"),
    "club":       ("WhatsApp Image 2026-07-31 at 11.13.53 (2).jpeg",
                   "Aerial of the courts with the mountains behind"),
    "camps":      ("WhatsApp Image 2026-07-31 at 11.13.53 (1).jpeg",
                   "Courts with La Concha rising behind them"),
    "courts":     ("WhatsApp Image 2026-07-19 at 16.48.24 (3).jpeg",
                   "Empty indoor courts, landscape framing"),
    "coaches":    ("WhatsApp Image 2026-07-19 at 16.48.24 (4).jpeg",
                   "Coach portrait, full length"),
    "marbella":   ("WhatsApp Image 2026-07-31 at 11.13.54 (3).jpeg",
                   "Puerto Banús — yachts, white facades, mountain behind"),
    "contact":    ("WhatsApp Image 2026-07-31 at 11.13.53 (3).jpeg",
                   "Palm-lined avenue at sunset"),
}

# The brand sheet carries a clean circular monogram. Crop is expressed as a
# fraction of the sheet so it survives any re-scan of the same artwork.
LOGO_SRC = "WhatsApp Image 2026-07-19 at 16.45.38.jpeg"
LOGO_BOX = (647 / 1536, 43 / 1024, 894 / 1536, 287 / 1024)


def sha16(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def emit(src_path: str, dst_path: str, check: bool) -> tuple[int, int, int]:
    """Re-encode one image; returns (width, height, bytes)."""
    with Image.open(src_path) as im:
        im = im.convert("RGB")
        im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
        w, h = im.size
        if not check:
            im.save(dst_path, "JPEG", quality=QUALITY, optimize=True,
                    progressive=True)
    return w, h, (os.path.getsize(dst_path) if os.path.exists(dst_path) else 0)


def make_favicon(src_path: str, out_dir: str, check: bool) -> str | None:
    """Cut the circular monogram out of the brand sheet."""
    if not os.path.isfile(src_path):
        return None
    with Image.open(src_path) as im:
        im = im.convert("RGB")
        x0, y0, x1, y1 = LOGO_BOX
        box = (int(x0 * im.width), int(y0 * im.height),
               int(x1 * im.width), int(y1 * im.height))
        mark = im.crop(box)
        side = max(mark.size)
        canvas = Image.new("RGB", (side, side), (247, 247, 245))
        canvas.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
        if not check:
            canvas.resize((512, 512), Image.LANCZOS).save(
                os.path.join(out_dir, "logo.png"), "PNG", optimize=True)
            canvas.resize((64, 64), Image.LANCZOS).save(
                os.path.join(out_dir, "favicon.png"), "PNG", optimize=True)

            # White-on-transparent nav mark. The source's wordmark is a white
            # SVG on a dark bar at 632x230, so the replacement is padded to the
            # same box: it drops into the same slot without touching any CSS.
            mark_l = mark.convert("L")
            alpha = mark_l.point(lambda v: max(0, min(255, int((255 - v - 25) * 1.7))))
            white = Image.new("RGBA", mark.size, (255, 255, 255, 0))
            white.putalpha(alpha)
            nav = Image.new("RGBA", (632, 230), (0, 0, 0, 0))
            scaled = white.resize((230, 230), Image.LANCZOS)
            nav.paste(scaled, ((632 - 230) // 2, 0), scaled)
            nav.save(os.path.join(out_dir, "logo-nav.png"), "PNG", optimize=True)
    return "logo.png"


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "site"
    check = "--check" in sys.argv
    src_dir = os.path.abspath(SRC_DIR)
    out_dir = os.path.join(root, "wp-content", "uploads", "stock")

    if not os.path.isdir(src_dir):
        print("source directory not found: %s" % src_dir)
        return 1
    if not check:
        os.makedirs(out_dir, exist_ok=True)

    credits, total, missing = {}, 0, []
    for slot in sorted(SLOTS):
        fname, caption = SLOTS[slot]
        src_path = os.path.join(src_dir, fname)
        if not os.path.isfile(src_path):
            missing.append(fname)
            print("  ! missing source: %s" % fname)
            continue
        dst = os.path.join(out_dir, slot + ".jpg")
        w, h, size = emit(src_path, dst, check)
        total += size
        credits[slot] = {
            "file": slot + ".jpg",
            "width": w,
            "height": h,
            "bytes": size,
            "sha256_16": sha16(dst) if os.path.exists(dst) else None,
            "shows": caption,
            "source_file": fname,
            "provider": "Client-supplied",
            "licence": "Client-owned — supplied by the academy for this build",
            "attribution_required": False,
        }
        print("  %-11s %5dx%-5d %6.0f KB  %s" % (slot, w, h, size / 1024, caption))

    logo = make_favicon(os.path.join(src_dir, LOGO_SRC), out_dir, check)
    if logo:
        print("  %-11s monogram cropped from the brand sheet -> logo.png + favicon.png" % "logo")

    if not check:
        with open(os.path.join(out_dir, "credits.json"), "w", encoding="utf-8") as fh:
            json.dump({
                "provenance": "All imagery on this site is supplied by the client "
                              "(Premium Padel Academy) and is client-owned.",
                "attribution_required": False,
                "replaces": "The Wikimedia Commons stock set used in the first media "
                            "pass, which carried CC BY and CC BY-SA obligations.",
                "images": credits,
            }, fh, indent=2, ensure_ascii=False)

        with open(os.path.join(out_dir, "MEDIA-CREDITS.md"), "w", encoding="utf-8") as fh:
            fh.write(
                "# Media credits\n\n"
                "Every image on this site was **supplied by the client** and is "
                "client-owned. There is no attribution obligation and no share-alike "
                "term, so no credits line is required on the page.\n\n"
                "This replaces the Wikimedia Commons stock set used in the first "
                "media pass — that set carried CC BY attribution on four images and "
                "CC BY-SA share-alike on three, and none of it is still on disk.\n\n"
                "EXIF is stripped at ingest: the originals came off phones and could "
                "carry location metadata.\n\n"
                "| Slot | Shows | Pixels |\n| --- | --- | --- |\n")
            for slot in sorted(credits):
                c = credits[slot]
                fh.write("| `%s.jpg` | %s | %d×%d |\n"
                         % (slot, c["shows"], c["width"], c["height"]))
            fh.write(
                "\n## Third-party marks visible in frame\n\n"
                "Some frames are event and club photography and carry other parties' "
                "branding in shot (court-side sponsor boards, club and retailer "
                "signage). That is normal for photographs taken at those venues and is "
                "not a claim of endorsement, but it is worth a look before these go on "
                "a commercial domain.\n")

    print("\n%s %d image(s), %.1f MB total%s"
          % ("would write" if check else "wrote", len(credits), total / 1e6,
             "" if not missing else "  — %d source file(s) missing" % len(missing)))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
