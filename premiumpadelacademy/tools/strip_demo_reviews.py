#!/usr/bin/env python3
"""Remove fabricated demo reviews before the site goes public.

The reviews currently on the page are invented filler, written so the design
could be evaluated. Publishing them to real visitors would be a misleading
commercial practice, so every fabricated block is tagged data-demo="true" and
this script reverts them to clearly-marked empty slots.

    python3 tools/strip_demo_reviews.py [--check] [site-v2]

    --check   report only, exit 1 if demo content is present (use in a
              pre-deploy gate so this can never ship by accident)
"""
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

STAR_EMPTY = ('<svg viewBox="0 0 24 24" aria-hidden="true" class="is-empty">'
              '<path d="M12 2.6l2.9 5.9 6.5.95-4.7 4.58 1.11 6.47L12 17.44 '
              '6.19 20.5l1.11-6.47L2.6 9.45l6.5-.95z"/></svg>')

PLACEHOLDER_CARD = """        <figure class="review is-placeholder">
          <span class="review-pending">Pendiente</span>
          <span class="stars" role="img" aria-label="Sin valoración">{stars}</span>
          <blockquote>Espacio para una reseña real. Sustituir por las palabras del propio jugador o club.</blockquote>
          <figcaption class="review-author">
            <span class="review-avatar" aria-hidden="true">·</span>
            <span>
              <span class="review-who">Nombre</span>
              <span class="review-where">Club · nivel</span>
            </span>
          </figcaption>
        </figure>
"""

PLACEHOLDER_SUMMARY = """        <div class="rating-summary">
          <span class="rating-score">—</span>
          <span class="rating-meta">
            <span class="stars stars-lg" role="img" aria-label="Sin valoración">{stars}</span>
            <p>Valoración media pendiente · <strong>0</strong> reseñas publicadas</p>
          </span>
        </div>
"""


def strip(html: str) -> tuple[str, int]:
    n = html.count('data-demo="true"')
    if not n:
        return html, 0

    empty5 = STAR_EMPTY * 5

    # summary panel
    html = re.sub(r'        <div class="rating-summary" data-demo="true">.*?\n        </div>\n',
                  PLACEHOLDER_SUMMARY.format(stars=empty5), html, flags=re.S)

    # each fabricated card -> one empty slot
    cards = re.findall(r'        <figure class="review" data-demo="true">.*?\n        </figure>\n',
                       html, flags=re.S)
    for c in cards:
        html = html.replace(c, PLACEHOLDER_CARD.format(stars=empty5), 1)

    html = html.replace(
        "Contenido de ejemplo — pendiente de sustituir por reseñas reales.",
        "Las reseñas se publican con el nombre y el club de cada jugador, tal y como nos las envían.")

    html = re.sub(r'      <!-- ={12,}\n           DEMO CONTENT.*?={12,} -->\n', "", html, flags=re.S)
    return html, n


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    root = PROJECT / (args[0] if args else "site-v2")

    total = 0
    for page in sorted(root.glob("*.html")):
        src = page.read_text(encoding="utf-8")
        out, n = strip(src)
        total += n
        if not n:
            continue
        if check:
            print(f"  {page.relative_to(PROJECT)}: {n} fabricated block(s)")
        else:
            page.write_text(out, encoding="utf-8")
            print(f"  {page.relative_to(PROJECT)}: {n} fabricated block(s) removed")

    if check:
        if total:
            print(f"\nFAIL: {total} fabricated review block(s) present — not fit to publish.")
            return 1
        print("OK: no fabricated review content.")
        return 0

    print(f"\n{total} fabricated block(s) reverted to empty slots." if total
          else "Nothing to strip — no demo content found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
