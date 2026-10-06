"""Publish gate for pedicelmarketing.ch: python3 checks.py [dist]  (exit 1 on any problem)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

FORBIDDEN = ["ß", "10.8%", "10,8%", "250%", "300+", "Vanguard Medical", "Benahavis Bistro",
             "Marianna Levchenko", "Leo Grant", "Lorem ipsum"]
PRICE = re.compile(
    r"\b(?:CHF|EUR)\b\s?\d|\d\s?\b(?:CHF|EUR)\b"   # CHF 900, 900 EUR (word-bounded: not "2 Europäer")
    r"|[€₦]\s?\d|\d\s?[€₦]"
    r"|\bFr\.\s?\d"                                   # Swiss: Fr. 900
    r"|\d['’.,]?\d*\.[–-]",                           # Swiss: 2'900.–
    re.I)
ATTRS = ("alt", "title", "placeholder", "aria-label", "value", "data-wait")
SKIP_DIRS = {"_external"}      # symlink to the 122 MB Webflow mirror: not ours to check, slow to walk


def _exists(dist: Path, href: str) -> bool:
    path = href.split("#")[0].split("?")[0].strip("/")
    return (dist / path / "index.html").exists() or (dist / path).is_file() or path.startswith("_external")


def _pages(dist: Path):
    """Every index.html under dist, never descending into _external."""
    for root, dirs, files in os.walk(dist):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        if "index.html" in files:
            yield Path(root) / "index.html"


def problems(dist: Path) -> list[str]:
    out: list[str] = []
    for f in _pages(dist):
        rel = f.relative_to(dist)
        html = f.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["script", "style"]):   # visible: Webflow CSS/JS contain "250%" etc.
            tag.decompose()
        text = soup.get_text(" ")
        attrs = [str(el[a]) for el in soup.find_all(True) for a in ATTRS if el.get(a)]
        attrs += [str(m["content"]) for m in soup.find_all("meta") if m.get("content")]
        text = " ".join([text, *attrs])      # visible text + attribute values (alt, meta description, ...)
        for bad in FORBIDDEN:
            if bad in text:
                out.append(f"{rel}: forbidden '{bad}'")
        if PRICE.search(text):
            out.append(f"{rel}: price '{PRICE.search(text).group(0)}'")
        if not soup.find("link", rel="canonical"):
            out.append(f"{rel}: no canonical")
        if not soup.find("link", rel="alternate", hreflang=True):
            out.append(f"{rel}: no hreflang")
        for a in soup.find_all(href=True):
            h = a["href"]
            if not h.startswith("/") or h.startswith(("//", "/api/")):
                continue
            if re.match(r"^/(fr/|en/)?blog", h):
                out.append(f"{rel}: blog link {h}")
            elif not _exists(dist, h):
                out.append(f"{rel}: broken link {h}")
    return out


if __name__ == "__main__":
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "dist")
    found = problems(dist)
    print("\n".join(found) or "checks: all clear")
    sys.exit(1 if found else 0)
