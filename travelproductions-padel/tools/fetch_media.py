#!/usr/bin/env python3
"""Source stock imagery for the empty media slots, with licences on record.

The re-content pass emptied 21 background-video slots: the source footage was
Travel Productions' client work and could not carry over. This fills them so
the layout reads as a site rather than a wireframe.

Source is Wikimedia Commons, which returns the licence, author and file page
for every result. That metadata is written to `MEDIA-CREDITS.md` beside the
files, because a derived site that cannot say where its media came from has
exactly the problem the mirror was careful to avoid.

Licence order, most permissive first: CC0 / public domain (nothing owed), then
CC BY, then CC BY-SA. NonCommercial and NoDerivatives are refused outright —
this is a commercial site and those terms do not fit.

Images are pulled at a 2000px-wide rendering rather than the original, which
is often 5 MB+ and far larger than a background needs.

Usage:  python3 tools/fetch_media.py site/wp-content/uploads/stock
"""
from __future__ import annotations
import json, os, sys, time, hashlib, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "site-cloner/1.0 (site mirror pipeline; pedicelsocial@gmail.com)"}

# Ranked most permissive first; anything not matching a prefix here is skipped.
LICENCE_RANK = ["cc0", "public domain", "pd", "cc by 4.0", "cc by 3.0", "cc by 2.0",
                "cc by-sa 4.0", "cc by-sa 3.0", "cc by-sa 2.0"]
REFUSE = ("nc", "nd", "noncommercial", "noderiv", "fair use")

WANTED = {
    "hero":       ["panoramic padel court", "padel court", "padel"],
    "lessons":    ["padel player", "padel racket", "padel"],
    "group":      ["padel doubles match", "padel match", "padel players"],
    "technical":  ["padel racket ball", "padel racket", "tennis racket"],
    "physical":   ["tennis player running", "athletics training", "sport training"],
    "match":      ["padel tournament", "padel match", "padel court"],
    "club":       ["padel club courts", "padel courts", "padel court"],
    "marbella":   ["Marbella", "Marbella Spain", "Costa del Sol"],
    "programmes": ["padel training", "tennis training camp", "padel court"],
    "contact":    ["padel court net", "tennis net", "padel court"],
}


def rank(lic: str):
    l = (lic or "").strip().lower()
    if any(b in l for b in REFUSE):
        return None
    for i, p in enumerate(LICENCE_RANK):
        if l.startswith(p):
            return i
    return None


def search(term, limit=18):
    qs = urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": term,
        "gsrnamespace": "6", "gsrlimit": str(limit),
        "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": "2000", "format": "json",
    })
    req = urllib.request.Request(API + "?" + qs, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    return list(((d.get("query") or {}).get("pages") or {}).values())


def usable(p):
    ii = (p.get("imageinfo") or [{}])[0]
    w, h = ii.get("width") or 0, ii.get("height") or 0
    if w < 1400 or h < 800 or w < h:            # landscape, big enough
        return None
    em = ii.get("extmetadata") or {}
    lic = (em.get("LicenseShortName") or {}).get("value", "")
    r = rank(lic)
    if r is None:
        return None
    title = (p.get("title") or "").replace("File:", "")
    if os.path.splitext(title)[1].lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        return None
    return r, ii, em, lic


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    if len(data) < 15000:
        raise ValueError("suspiciously small (%d bytes)" % len(data))
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data), hashlib.sha256(data).hexdigest()[:16]


def strip_html(s):
    import re
    return re.sub(r"<[^>]+>", "", s or "").strip()


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "site/wp-content/uploads/stock"
    os.makedirs(outdir, exist_ok=True)
    picked, seen = {}, set()

    for slot, terms in WANTED.items():
        best = None
        for term in terms:
            try:
                pages = search(term)
            except Exception as e:
                print("  ! %-26s %s" % (term, e))
                time.sleep(1.5)
                continue
            cands = []
            for p in pages:
                u = usable(p)
                if not u:
                    continue
                r, ii, em, lic = u
                key = ii.get("descriptionurl") or ii.get("url")
                if key in seen:
                    continue
                cands.append((r, p, ii, em, lic))
            if cands:
                cands.sort(key=lambda c: c[0])
                best = cands[0]
                break
            time.sleep(1.0)
        if not best:
            print("  ! no usable image for %s" % slot)
            continue
        _, p, ii, em, lic = best
        seen.add(ii.get("descriptionurl") or ii.get("url"))
        url = ii.get("thumburl") or ii.get("url")
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        name = slot + ext
        try:
            size, digest = fetch(url, os.path.join(outdir, name))
        except Exception as e:
            print("  ! download %-11s %s" % (slot, e))
            continue
        picked[slot] = {
            "file": name, "bytes": size, "sha256_16": digest,
            "title": (p.get("title") or "").replace("File:", ""),
            "author": strip_html((em.get("Artist") or {}).get("value", "")) or "—",
            "licence": lic,
            "file_page": ii.get("descriptionurl"),
            "fetched_url": url,
            "provider": "Wikimedia Commons",
        }
        print("  %-11s %-11s %6.0f KB  %s" % (slot, lic[:11], size / 1024, name))
        time.sleep(0.6)

    with open(os.path.join(outdir, "credits.json"), "w", encoding="utf-8") as fh:
        json.dump(picked, fh, indent=2, ensure_ascii=False)

    lines = [
        "# Media credits — stock imagery", "",
        "Placeholder-grade imagery filling the slots the source's licensed footage",
        "vacated. Chosen to make the layout readable, **not art-directed**. Replace with",
        "the academy's own photography before launch.", "",
        "Source: Wikimedia Commons. Nothing here is NonCommercial or NoDerivatives.", "",
        "| Slot | File | Licence | Author | File page |", "|---|---|---|---|---|",
    ]
    for slot, m in picked.items():
        lines.append("| `%s` | `%s` | %s | %s | [Commons](%s) |"
                     % (slot, m["file"], m["licence"], m["author"][:40], m["file_page"]))
    by = {k: v for k, v in picked.items() if v["licence"].lower().startswith("cc by")}
    if by:
        lines += ["", "## Attribution required", "",
                  "These carry CC BY or CC BY-SA and must be credited wherever the site is",
                  "published — a credits line in the footer or a colophon page satisfies it:", ""]
        for slot, m in by.items():
            lines.append("- **%s** (`%s`) — %s — %s — %s"
                         % (slot, m["file"], m["author"][:60], m["licence"], m["file_page"]))
        if any(v["licence"].lower().startswith("cc by-sa") for v in by.values()):
            lines += ["", "CC BY-SA additionally obliges derivative *images* to carry the same",
                      "licence. Cropping or recolouring those for the site inherits that",
                      "obligation — a further reason to replace them with owned photography."]
    with open(os.path.join(outdir, "MEDIA-CREDITS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("\n%d/%d slots filled -> %s" % (len(picked), len(WANTED), outdir))
    return 0 if len(picked) >= 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
