#!/usr/bin/env python3
"""Fill the emptied background-video slots with the sourced stock imagery.

`recontent.py` cleared 21 Elementor background videos because the footage was
Travel Productions' client work. That left the layout structurally right and
visually blank. This puts an image behind each of those containers.

Each slot is converted from a video background to a classic (image) one:

* ``background_background`` flips from ``video`` to ``classic`` so Elementor's
  front-end script stops trying to initialise a player;
* the now-empty ``<video>`` wrapper is removed;
* a rule is appended to a single ``<style id="stock-media">`` block keyed on the
  container's own Elementor id.

The containers' motion-FX settings — the parallax scale and scroll effects that
give the source its feel — are deliberately left untouched, so the imagery moves
the way the footage did.

Anything not named in SLOTS still gets filled, from PAGE_DEFAULT, so a slot can
never be silently missed.

Usage:  python3 tools/apply_media.py site [--check]
"""
from __future__ import annotations
import os, re, sys, json

STOCK_URL = "/wp-content/uploads/stock/"

# Elementor container id -> stock image, chosen from the headings each sits behind.
SLOTS = {
    "index.html": {
        "3994e2f": "hero.jpg",        # hero, desktop
        "7bc9cdb": "hero.jpg",        # hero, mobile cut
        "1e76ca7": "lessons.jpg",     # tile -> How we coach
        "e64cfc9": "programmes.jpg",  # tile -> Programmes
        "98ac771": "coaches.jpg",     # tile -> The coaches
        "296a2e1": "camps.jpg",       # tile -> Camps in Marbella
        "ae289e2": "match.jpg",       # closing CTA band
    },
    "coaching/index.html": {
        "9b52514": "hero.jpg",
        "b6c895d": "hero.jpg",
        "6bbc508": "lessons.jpg",
        "f3b91e3": "lessons.jpg",
        "6f51b1f": "group.jpg",
        "7ddf9eb": "technical.jpg",
        "c31231d": "physical.jpg",
    },
    "programmes/index.html": {
        "967160f": "programmes.jpg",
        "222d8b5": "match.jpg",
        "9936121": "club.jpg",
    },
    "marbella/index.html": {
        "3cbc829": "marbella.jpg",   # the town
        "059a7c7": "camps.jpg",      # courts under La Concha
        "91544c9": "courts.jpg",     # the courts
    },
    "contact/index.html": {
        "48ebb5e": "contact.jpg",
    },
    "coaches/index.html": {
        "1110e40": "coaches.jpg",    # under the page title
        "904767c": "group.jpg",      # "what you can expect"
        "542bbcb": "courts.jpg",     # closing band
    },
}
PAGE_DEFAULT = {
    "index.html": "hero.jpg",
    "coaching/index.html": "lessons.jpg",
    "programmes/index.html": "programmes.jpg",
    "marbella/index.html": "marbella.jpg",
    "contact/index.html": "contact.jpg",
    "coaches/index.html": "coaches.jpg",
}

EMPTY_VIDEO = "&quot;background_video_link&quot;:&quot;&quot;"
CONTAINER = re.compile(
    r'<(?:div|a) class="elementor-element elementor-element-([0-9a-zA-Z]+)[^"]*"[^>]*?'
    r'data-settings="([^"]*)"', re.S)
VIDEO_WRAP = re.compile(
    r'<div class="elementor-background-video-container[^"]*">.*?</div>\s*', re.S)


def find_slots(src: str):
    """Every container whose data-settings still names an empty video."""
    out = []
    for m in CONTAINER.finditer(src):
        if EMPTY_VIDEO in m.group(2):
            out.append(m.group(1))
    seen, ordered = set(), []
    for d in out:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    return ordered


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "site"
    check = "--check" in sys.argv
    stock_dir = os.path.join(root, "wp-content", "uploads", "stock")
    available = {f for f in os.listdir(stock_dir) if f.endswith((".jpg", ".png", ".webp"))}
    total_rules = total_slots = total_wraps = 0

    for page, default in PAGE_DEFAULT.items():
        path = os.path.join(root, page)
        if not os.path.isfile(path):
            print("  missing: %s" % page)
            continue
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            src = original = fh.read()

        ids = find_slots(src)
        mapping = SLOTS.get(page, {})
        rules, used = [], []
        for did in ids:
            img = mapping.get(did, default)
            if img not in available:
                print("  ! %s: image %s missing, using %s" % (page, img, default))
                img = default
            rules.append(
                ".elementor-element.elementor-element-%s{"
                "background-image:url('%s%s') !important;"
                "background-size:cover !important;"
                "background-position:center center !important;"
                "background-repeat:no-repeat !important;}" % (did, STOCK_URL, img))
            used.append((did, img))

        # video background -> image background
        src = src.replace(
            "&quot;background_background&quot;:&quot;video&quot;,"
            + EMPTY_VIDEO,
            "&quot;background_background&quot;:&quot;classic&quot;")
        src = src.replace(EMPTY_VIDEO + ",", "")
        src = src.replace(EMPTY_VIDEO, "")

        src, nwrap = VIDEO_WRAP.subn("", src)

        if rules:
            block = ('\n<style id="stock-media">\n' + "\n".join(rules) + "\n</style>\n")
            src = src.replace("</head>", block + "</head>", 1)

        total_rules += len(rules)
        total_slots += len(ids)
        total_wraps += nwrap
        print("  %-22s %2d slot(s) filled, %2d video wrapper(s) removed" % (page, len(ids), nwrap))
        for did, img in used:
            print("        %-9s -> %s" % (did, img))

        if not check and src != original:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(src)

    print("\n%s: %d slot(s) across %d page(s), %d empty video wrapper(s) removed"
          % ("would fill" if check else "filled", total_slots, len(PAGE_DEFAULT), total_wraps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
