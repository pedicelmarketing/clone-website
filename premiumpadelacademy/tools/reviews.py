#!/usr/bin/env python3
"""Render the customer-reviews section on the home page.

The client supplied 20 real reviews on 2026-08-03, replacing the six fabricated
placeholders the design was built with. Source of truth is
site-v2/assets/reviews.json; this renders it between the <!-- reviews:start -->
and <!-- reviews:end --> markers, same generated-block pattern as
tools/partner_logos.py and tools/social_links.py.

Two things are deliberately COMPUTED rather than authored:

  * the aggregate score, from the ratings actually present. A star average is a
    factual claim about real people's opinions; typing one by hand is how it
    ends up disagreeing with the reviews beneath it.
  * the review count, likewise.

Nothing rendered here carries data-demo="true" any more, which is what allows
deploy/build_public.sh to produce an indexable build (see its Gate 1).

    python3 tools/reviews.py --render
    python3 tools/reviews.py --check

Stdlib only, to match the rest of the tooling in this repo.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PAGES = ("index.html",)          # the reviews section lives on the home page only

START = "      <!-- reviews:start -->"
END = "      <!-- reviews:end -->"

# Rows in the marquee. Reviews are dealt across them and alternate rows travel
# in opposite directions, which is what produces the offset, drifting look.
ROWS = 3

# Seconds per card. The whole row's duration scales with how many cards it
# holds, so every row moves at the same apparent speed regardless of length.
SECONDS_PER_CARD = 13

# Country label + flag. Flags are inline SVG on a 24x16 box to match the .flag
# convention already used by the language switch in the header — no emoji,
# which renders inconsistently across platforms and can't be styled.
COUNTRIES = {
    "es": ("España", "Spain",
           '<rect width="24" height="16" fill="#AA151B"/>'
           '<rect y="4" width="24" height="8" fill="#F1BF00"/>'),
    "no": ("Noruega", "Norway",
           '<rect width="24" height="16" fill="#BA0C2F"/>'
           '<path d="M8 0v16M0 6.5h24" stroke="#fff" stroke-width="4"/>'
           '<path d="M8 0v16M0 6.5h24" stroke="#00205B" stroke-width="2"/>'),
    "se": ("Suecia", "Sweden",
           '<rect width="24" height="16" fill="#005293"/>'
           '<path d="M8 0v16M0 6.5h24" stroke="#FECB00" stroke-width="3"/>'),
    "gb": ("Reino Unido", "United Kingdom",
           '<rect width="24" height="16" fill="#012169"/>'
           '<path d="M0 0 24 16M24 0 0 16" stroke="#FFF" stroke-width="3.2"/>'
           '<path d="M0 0 24 16M24 0 0 16" stroke="#C8102E" stroke-width="1.7"/>'
           '<path d="M12 0v16M0 8h24" stroke="#FFF" stroke-width="5.4"/>'
           '<path d="M12 0v16M0 8h24" stroke="#C8102E" stroke-width="3.2"/>'),
    "ie": ("Irlanda", "Ireland",
           '<rect width="8" height="16" fill="#169B62"/>'
           '<rect x="8" width="8" height="16" fill="#fff"/>'
           '<rect x="16" width="8" height="16" fill="#FF883E"/>'),
    "de": ("Alemania", "Germany",
           '<rect width="24" height="16" fill="#000"/>'
           '<rect y="5.33" width="24" height="5.34" fill="#D00"/>'
           '<rect y="10.67" width="24" height="5.33" fill="#FFCE00"/>'),
    "fr": ("Francia", "France",
           '<rect width="8" height="16" fill="#002395"/>'
           '<rect x="8" width="8" height="16" fill="#fff"/>'
           '<rect x="16" width="8" height="16" fill="#ED2939"/>'),
    "ch": ("Suiza", "Switzerland",
           '<rect width="24" height="16" fill="#DA291C"/>'
           '<path d="M12 4v8M8 8h8" stroke="#fff" stroke-width="2.6"/>'),
    "ma": ("Marruecos", "Morocco",
           '<rect width="24" height="16" fill="#C1272D"/>'
           '<path d="M12 4.1 14.4 11.5 8.1 6.9h7.8L9.6 11.5Z" fill="none" '
           'stroke="#006233" stroke-width="0.9" stroke-linejoin="round"/>'),
}

# A rounded five-point star. stroke-linejoin:round in the CSS softens the tips,
# which reads as deliberate rather than clip-art at small sizes.
STAR = ("M12 2.4l2.72 5.79 6.18.92c.5.08.7.72.33 1.09l-4.49 4.5 1.06 6.34"
        "c.09.52-.45.91-.9.66L12 18.78l-5.4 2.92c-.45.25-.99-.14-.9-.66"
        "l1.06-6.34-4.49-4.5c-.37-.37-.17-1.01.33-1.09l6.18-.92z")

# translate="no" on the initial and the name: machine translation treats a lone
# letter as a word, and Chrome was rendering the avatars as "Yo" and "AND" for
# reviewers whose initials are I and Y. Personal names must not be translated
# either — they are proper nouns, not copy.
CARD = """            <figure class="review"{hidden}>
              <span class="stars" role="img" aria-label="{stars_label}">{stars}</span>
              <blockquote>{text}</blockquote>
              <figcaption class="review-author">
                <span class="review-avatar" aria-hidden="true" translate="no">{initial}</span>
                <span>
                  <span class="review-who" translate="no">{name}</span>
                  <span class="review-where"><svg class="flag" viewBox="0 0 24 16" aria-hidden="true" focusable="false">{flag}</svg>{country}</span>
                </span>
              </figcaption>
            </figure>
"""

ROW = """        <div class="marquee-row" data-dir="{dir}">
          <div class="marquee-track" style="--dur:{dur}s">
{cards}          </div>
        </div>
"""

BLOCK = """{start}
      <!-- Reseñas reales de clientes. Generated from assets/reviews.json by
           tools/reviews.py — do not hand-edit; re-render instead. The score and
           the count are computed from the ratings, never typed. -->
      <section class="reviews-section" id="resenas">
        <div class="container">
          <div class="reviews-head" data-anim="up">
            <p class="eyebrow">Lo que dicen los jugadores</p>
            <h2>Reseñas de los programas</h2>
            <p>Jugadores y clubes que ya han entrenado con nosotros.</p>
            <div class="rating-summary">
              <span class="rating-score">{score}</span>
              <span class="rating-meta">
                <span class="stars stars-lg" role="img" aria-label="{avg_label}">{avg_stars}</span>
                <p>Media de <strong>{count}</strong> reseñas</p>
              </span>
            </div>
          </div>

        </div>
        <div class="reviews-marquee">
{rows}        </div>
      </section>
{end}"""


def esc(v: str) -> str:
    return (v.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def initial(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name)
    return (name.strip()[:1] or "?").upper() if not ascii_name else name.strip()[:1].upper()


def stars_svg(rating: int, out_of: int = 5) -> str:
    out = ""
    for i in range(1, out_of + 1):
        cls = "" if i <= rating else ' class="is-empty"'
        out += f'<svg viewBox="0 0 24 24" aria-hidden="true"{cls}><path d="{STAR}"/></svg>'
    return out


def load(root: Path) -> dict:
    path = root / "assets" / "reviews.json"
    if not path.exists():
        sys.exit(f"FATAL: {path} missing")
    return json.loads(path.read_text(encoding="utf-8"))


def render(data: dict) -> tuple[str, int, float]:
    reviews = data.get("reviews") or []
    if not reviews:
        sys.exit("FATAL: reviews.json has no reviews")

    def card(r: dict, duplicate: bool) -> str:
        if r["country"] not in COUNTRIES:
            sys.exit(f"FATAL: no flag for country {r['country']!r} — add one to COUNTRIES")
        label_es, _label_en, flag = COUNTRIES[r["country"]]
        return CARD.format(
            # The second copy exists only to make the loop seamless; hide it
            # from assistive tech so every review is announced exactly once.
            hidden=' aria-hidden="true"' if duplicate else "",
            stars=stars_svg(int(r["rating"])),
            stars_label=f"{int(r['rating'])} de 5 estrellas",
            text=esc(r["text_es"]),
            initial=esc(initial(r["name"])),
            name=esc(r["name"]),
            flag=flag,
            country=esc(label_es),
        )

    # Deal round-robin rather than in blocks, so no row ends up all 5-star or
    # all long-quote — the rows stay visually varied.
    lanes = [reviews[i::ROWS] for i in range(ROWS)]
    rows = ""
    for i, lane in enumerate(lanes):
        if not lane:
            continue
        # Each track holds the lane twice; the animation travels exactly -50%,
        # so the second copy lands where the first began and the seam is
        # invisible. Any other duration/offset pairing visibly jumps.
        body = "".join(card(r, False) for r in lane) + "".join(card(r, True) for r in lane)
        rows += ROW.format(dir="right" if i % 2 else "left",
                           dur=len(lane) * SECONDS_PER_CARD, cards=body)

    total = sum(int(r["rating"]) for r in reviews)
    avg = total / len(reviews)
    score = f"{avg:.1f}".replace(".", ",")      # Spanish decimal comma
    block = BLOCK.format(
        start=START, end=END, rows=rows,
        score=score, count=len(reviews),
        avg_stars=stars_svg(round(avg)),
        avg_label=f"{score} de 5 estrellas",
    )
    return block, len(reviews), avg


def apply(root: Path, block: str) -> list[str]:
    touched = []
    existing = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    for name in PAGES:
        page = root / name
        html = page.read_text(encoding="utf-8")
        if existing.search(html):
            out = existing.sub(lambda _: block, html, count=1)
        else:
            # First run: replace the whole hand-written reviews section.
            pat = re.compile(r'\n  <section class="reviews-section".*?</section>\n', re.S)
            if not pat.search(html):
                sys.exit(f"FATAL: no reviews section found in {name}")
            out = pat.sub("\n" + block + "\n", html, count=1)
        if out != html:
            page.write_text(out, encoding="utf-8")
            touched.append(name)
        final = page.read_text(encoding="utf-8")
        if final.count(START) != 1:
            sys.exit(f"FATAL: {name} has {final.count(START)} review blocks")
    return touched


def check(root: Path, data: dict) -> int:
    problems = 0
    reviews = data.get("reviews") or []
    for name in PAGES:
        html = (root / name).read_text(encoding="utf-8")
        # Each review renders twice — once real, once as the aria-hidden
        # duplicate that closes the marquee loop.
        n_cards = html.count('<figure class="review"') - html.count(
            '<figure class="review" aria-hidden="true"')
        n_demo = html.count('data-demo="true"')
        avg = sum(int(r["rating"]) for r in reviews) / len(reviews)
        shown = re.search(r'<span class="rating-score">([\d,\.]+)</span>', html)
        expect = f"{avg:.1f}".replace(".", ",")
        ok_score = bool(shown) and shown.group(1) == expect
        print(f"  {name:14} {n_cards} card(s), score {shown.group(1) if shown else '?'} "
              f"(computed {expect}), {n_demo} fabricated block(s)")
        if n_cards != len(reviews):
            print(f"    ERROR: {len(reviews)} review(s) in JSON but {n_cards} rendered")
            problems += 1
        if not ok_score:
            print("    ERROR: displayed score does not match the ratings")
            problems += 1
        if n_demo:
            print("    ERROR: fabricated review markup still present")
            problems += 1
    print(f"\n{'FAIL' if problems else 'OK'}: {problems} problem(s).")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site-v2")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    root = PROJECT / args.root
    data = load(root)

    if args.check and not args.render:
        return check(root, data)
    if not args.render:
        ap.error("nothing to do — pass --render or --check")

    block, n, avg = render(data)
    touched = apply(root, block)
    print(f"rendered {n} real review(s), computed average {avg:.2f}")
    print(f"pages updated: {', '.join(touched) if touched else 'none (already current)'}")
    return check(root, data) if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
