#!/usr/bin/env python3
"""Make the build safe and complete enough to publish.

`apply_media.py` put stock imagery behind the containers, but three things
still stood between this build and a public URL. Publishing is distribution,
so each one had to be closed rather than noted.

1. **Poster images.** Elementor paints these containers from generated CSS, not
   from the HTML — and those rules still pointed at twelve Travel Productions
   photographs that were sitting on disk and rendering. Repointed at the stock
   set. This is also why the backgrounds are set here rather than by an
   override: it is Elementor's own mechanism, so the motion-effects layers
   (which carry the parallax) pick the image up too.

2. **Safiro.** A licensed retail typeface (Atipo Foundry) that the source
   self-hosts under a licence that does not transfer; the asset table marks it
   `Restricted — must never ship`. The `@font-face` sources are repointed at
   Open Sans, which is already local and OFL. The family *name* is left alone,
   so every rule still resolves and the swap can be reverted in one line if the
   academy licenses Safiro. **This is a disclosed substitution, not a silent
   one** — see the report.

3. **Source media on disk.** 21 videos (79 MB) and the poster photographs were
   still present. Nothing referenced the videos any more, but an unreferenced
   file under a public URL is still a published file.

`/coaches/` used to be replaced with a placeholder here, because it was still
entirely Travel Productions' Spanish content and is linked from every nav. It
now carries the academy's own coach copy, so the placeholder is gone and the
page goes through the same passes as every other route.

Usage:  python3 tools/prepare_deploy.py site [--check]
"""
from __future__ import annotations
import os, re, sys, shutil

STOCK = "/wp-content/uploads/stock/"

PAGES = ("index.html", "coaching/index.html", "programmes/index.html",
         "marbella/index.html", "coaches/index.html", "contact/index.html")

POSTER_SWAP = {
    "2024/04/BDD-Cover.jpg": "match.jpg",
    "2024/04/Guia_de_Isora_cover.jpg": "club.jpg",
    "2024/04/San_Miguel_de_Abona_cover_2.jpg": "group.jpg",
    "2024/04/Servicios-portada.jpg": "lessons.jpg",
    "2024/05/Dhigali-cover-work.jpg": "programmes.jpg",
    "2024/05/Melia-Cover.jpg": "programmes.jpg",
    "2024/05/Selina-Cover.jpg": "match.jpg",
    "2024/05/Sobre-nosotros.jpg": "group.jpg",
    "2024/05/Turismo-Canarias-Cover_.jpg": "marbella.jpg",
    "2024/05/video_cover_mogan_2.webp": "club.jpg",
    "2025/01/Peniscola-Video-cover.jpg": "programmes.jpg",
    "2026/01/Pajara-Cover.jpg": "lessons.jpg",
    "2025/07/Captura-de-pantalla-2025-07-29-a-las-10.02.33-1024x508.png": "marbella.jpg",
    "2025/07/Captura-de-pantalla-2025-07-29-a-las-10.03.37-scaled.png": "marbella.jpg",
}

OPEN_SANS = "/wp-content/uploads/elementor/google-fonts/fonts/opensans-memvyags126mizpba-uvwbx2vvnxbbobj2ovts-muw.woff2"

def rewrite_css(root, check):
    cssdir = os.path.join(root, "wp-content", "uploads", "elementor", "css")
    poster_hits = font_hits = 0
    files = 0
    for name in sorted(os.listdir(cssdir)):
        if not name.endswith(".css"):
            continue
        path = os.path.join(cssdir, name)
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            css = original = fh.read()
        for src_rel, stock in POSTER_SWAP.items():
            for variant in ('"/wp-content/uploads/%s"' % src_rel,
                            "/wp-content/uploads/%s" % src_rel):
                if variant in css:
                    repl = ('"%s%s"' % (STOCK, stock)) if variant.startswith('"') \
                        else ("%s%s" % (STOCK, stock))
                    css = css.replace(variant, repl)
                    poster_hits += 1
        # Safiro -> Open Sans, family name untouched
        css, n = re.subn(r'url\(["\']?/wp-content/uploads/2024/05/safiro-[a-z]+-webfont\.woff2["\']?\)',
                         "url('%s')" % OPEN_SANS, css)
        font_hits += n
        if css != original:
            files += 1
            if not check:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(css)
    return files, poster_hits, font_hits


def rewrite_html_fonts(root, check):
    """The home page declares the Safiro @font-face blocks inline, not in the
    Elementor CSS, so it needs the same substitution."""
    hits = 0
    for page in PAGES:
        path = os.path.join(root, page)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            src = original = fh.read()
        src, n = re.subn(
            r"url\(['\"]?/wp-content/uploads/2024/05/safiro-[a-z]+-webfont\.woff2['\"]?\)",
            "url('%s')" % OPEN_SANS, src)
        hits += n
        if n and not check:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(src)
    return hits


def add_noindex(root, check):
    """Keep the preview out of search results.

    This is an unapproved client site on a public URL. The link is unlisted,
    but nothing stopped a crawler that found it from indexing an unfinished
    build. Belt and braces: a robots.txt and a per-page meta tag, because a
    robots.txt alone does not stop a page already linked from elsewhere being
    listed.

    Remove both at launch.
    """
    tag = '<meta name="robots" content="noindex, nofollow" />'
    n = 0
    for page in PAGES:
        path = os.path.join(root, page)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            src = fh.read()
        if 'name="robots"' in src:
            continue
        src = src.replace("</head>", "\t" + tag + "\n</head>", 1)
        n += 1
        if not check:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(src)
    if not check:
        with open(os.path.join(root, "robots.txt"), "w", encoding="utf-8") as fh:
            fh.write("User-agent: *\nDisallow: /\n")
    return n


def purge(root, check):
    """Delete source media that must not be published."""
    removed, freed = [], 0
    up = os.path.join(root, "wp-content", "uploads")
    for dirpath, _dirs, names in os.walk(up):
        if os.path.join("uploads", "stock") in dirpath:
            continue
        for n in names:
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, up).replace(os.sep, "/")
            kill = False
            if n.lower().endswith((".mp4", ".webm", ".mov")):
                kill = True                              # source footage
            elif rel in POSTER_SWAP or rel.rsplit(".webp", 1)[0] in POSTER_SWAP:
                kill = True                              # swapped-out posters
            elif "safiro" in n.lower():
                kill = True                              # licensed typeface
            elif ("logo-travel" in n.lower()
                  or "logo-carrusel" in n.lower()
                  or "logo-travel-productions" in n.lower()):
                kill = True                              # source brand + client logos
            elif any(t in n.lower() for t in (
                    "playas-de-jandi_logo", "nicaragua_logo", "logo_ayto_peniscola",
                    "officialcompetition", "logo-login")):
                # Other companies' and public bodies' marks, plus a festival
                # selection badge that is an award claim about the source.
                kill = True
            if kill:
                freed += os.path.getsize(p)
                removed.append(rel)
                if not check:
                    os.remove(p)
    return removed, freed


def swap_nav_logo(root, check):
    """Replace the source's wordmark with the academy's own mark.

    The site logo in the navigation was still `Logo-Travel-web_blanco.svg` —
    Travel Productions' wordmark — on every route, and the content pass had
    rewritten its `alt` text to the academy's name, which made it worse rather
    than better: another company's logo captioned as this client's.

    `ingest_media` renders the academy's monogram white-on-transparent at the
    wordmark's own 632x230 box, so this is a src swap with no CSS consequence.
    """
    hits = 0
    for page in PAGES:
        path = os.path.join(root, page)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            src = original = fh.read()
        src = src.replace("/wp-content/uploads/2024/04/Logo-Travel-web_blanco.svg",
                          STOCK + "logo-nav.png")
        n = original.count("/wp-content/uploads/2024/04/Logo-Travel-web_blanco.svg")
        hits += n
        if n and not check:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(src)
    return hits


def add_favicon(root, check):
    """Point every page at the academy's own monogram.

    The source's favicon was Travel Productions' wordmark and was removed with
    the rest of its identity, which left the build with no icon at all. The
    brand sheet the academy supplied carries a circular monogram; `ingest_media`
    crops it, and this wires it up.
    """
    links = ('\t<link rel="icon" type="image/png" href="%sfavicon.png" />\n'
             '\t<link rel="apple-touch-icon" href="%slogo.png" />\n' % (STOCK, STOCK))
    n = 0
    for page in PAGES:
        path = os.path.join(root, page)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            src = fh.read()
        if 'rel="icon"' in src:
            continue
        src = src.replace("</head>", links + "</head>", 1)
        n += 1
        if not check:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(src)
    return n


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "site"
    check = "--check" in sys.argv

    files, posters, fonts = rewrite_css(root, check)
    print("CSS: %d file(s) touched — %d poster reference(s) repointed, %d Safiro source(s) swapped"
          % (files, posters, fonts))

    hfonts = rewrite_html_fonts(root, check)
    print("HTML: %d inline Safiro @font-face source(s) swapped" % hfonts)

    ni = add_noindex(root, check)
    print("Preview hygiene: %d page(s) marked noindex, robots.txt written" % ni)

    removed, freed = purge(root, check)
    kinds = {}
    for r in removed:
        ext = r.rsplit(".", 1)[-1].lower()
        kinds[ext] = kinds.get(ext, 0) + 1
    print("Purge: %d file(s), %.1f MB  %s"
          % (len(removed), freed / 1e6, kinds))

    navlogo = swap_nav_logo(root, check)
    print("Brand: %d source-wordmark reference(s) replaced with the academy mark" % navlogo)

    icons = add_favicon(root, check)
    print("Favicon: %d page(s) pointed at the academy monogram" % icons)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
