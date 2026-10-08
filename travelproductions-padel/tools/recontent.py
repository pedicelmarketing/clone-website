#!/usr/bin/env python3
"""Re-content the restructured mirror as Premium Padel Academy Marbella.

Runs on top of ``restructure.py``, which moved the routes and made the assets
plain-hostable. This pass replaces **copy and metadata only**, on the five
routes the approved architecture document marks "Nothing blocking":

    /            Home
    /coaching/   How we coach
    /programmes/ Programmes
    /marbella/   Marbella & the club
    /contact/    Contact

``/coaches/`` and the net-new ``/coaches/juanpi-vanella/`` are deliberately
untouched: both are blocked on bios and photographs from the coaches
themselves, and writing around that gap would mean inventing biography.

Three things happen here, all reversible and all reported:

1. **Head metadata** — language, title, description, Open Graph, canonical.
   The source ships Spanish ``es-ES`` metadata naming Travel Productions;
   none of it survives a rebrand.
2. **Body copy** — replaced against an explicit per-page map. Every
   replacement targets a *text node* (``>text<``), never raw substring, so a
   word like "Web" can never be rewritten inside a class name or attribute.
3. **Licensed media, neutralised** — the source's 21 background videos are
   Travel Productions' commercial work for Meliá, Selina, Bahía del Duque and
   several tourism boards. A derived site must not inherit them, so every
   ``background_video_link`` is emptied. Containers, layout and scroll
   behaviour are left intact so replacement footage can drop straight in.

What this pass does **not** do: design, photography, or final art direction.
Nothing here invents a fact. Where the brief has no confirmed answer — a phone
number, the coaches' backgrounds — the text says so rather than guessing.

Usage:
    python3 tools/recontent.py site            # apply
    python3 tools/recontent.py site --check    # report only
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _dom import container_span, widget_spans  # noqa: E402

BRAND = "Premium Padel Academy"

# --------------------------------------------------------------------------
# Head metadata, per route.
# --------------------------------------------------------------------------
HEAD = {
    "index.html": {
        "title": "Premium Padel Academy | High-performance padel coaching in Marbella",
        "description": (
            "A high-performance padel academy based in Marbella. Professional, premium "
            "coaching for demanding players, programmes for clubs worldwide, and camps "
            "on the Costa del Sol."
        ),
        "og_title": "Premium Padel Academy",
    },
    "coaching/index.html": {
        "title": "How we coach | Premium Padel Academy",
        "description": (
            "Local service in Marbella: high-impact private and group sessions, advanced "
            "technical and tactical development, racket-specific physical preparation, "
            "match lessons with real analysis, and thorough progress tracking."
        ),
        "og_title": "How we coach — Premium Padel Academy",
    },
    "programmes/index.html": {
        "title": "Programmes | Premium Padel Academy",
        "description": (
            "Local service, programmes for clubs worldwide, and camps in Marbella. "
            "Intensive programmes of up to seven days for padel clubs, their members "
            "and their technical staff."
        ),
        "og_title": "Programmes — Premium Padel Academy",
    },
    "marbella/index.html": {
        "title": "Camps in Marbella | Premium Padel Academy",
        "description": (
            "Raise your competitive level in the Mediterranean with premium padel "
            "programmes designed to reach maximum performance. What the experience "
            "includes, and answers to the questions we are asked most."
        ),
        "og_title": "Camps in Marbella — Premium Padel Academy",
    },
    "coaches/index.html": {
        "title": "The coaches | Premium Padel Academy",
        "description": (
            "Riki Padrón, Head Coach, and Juampi Vanella, Premium Coach. More than "
            "15 years at the elite level, and what you can expect from working with us."
        ),
        "og_title": "The coaches — Premium Padel Academy",
    },
    "contact/index.html": {
        "title": "Contact | Premium Padel Academy",
        "description": (
            "Get in touch about coaching in Marbella, a programme for your club, or a "
            "camp. Marbella, Spain."
        ),
        "og_title": "Contact — Premium Padel Academy",
    },
}

# --------------------------------------------------------------------------
# Chrome shared by every route: navigation, footer, overlay menu, cookie bar.
# --------------------------------------------------------------------------
GLOBAL_TEXT = {
    "Ir al contenido": "Skip to content",
    "Trabajos": "Programmes",
    "Servicios": "How we coach",
    "ServicIos": "How we coach",
    "Sobre nosotros": "The coaches",
    "SOBRE NOSOTROS": "The coaches",
    "contacto": "Contact",
    "contactO": "Contact",
    "Menú": "Menu",
    "Cerrar": "Close",
    # footer
    "Hagamos algo que importe.": "Let's raise your level.",
    "Localización": "Location",
    "Sedes en Canarias y Barcelona": "Marbella, Spain",
    # the source's own footer tagline
    "Trabajamos globalmente": "International programmes for elite clubs",
    "Nuevo proyecto": "New enquiry",
    "Información y talento": "General enquiries",
    "Comience un proyecto": "Get in touch",
    "Ver casos de éxito": "See the programmes",
    "© Todos los derechos reservados": "© All rights reserved",
    "Condiciones legales": "Legal notice",
    # cookie banner
    "Hola": "Hello",
    "Rechazar": "Decline",
    # third home label row; the other two are covered by the nav entries above
    "Experiencia": "Camps",
    # uppercase nav variants used by the overlay menu
    "TRABAJOS": "PROGRAMMES",
    "SERVICIOS": "HOW WE COACH",
    "Controles": "Controls",
    # label inside the custom cursor follower
    "Ver": "View",
    "CONTACTO": "CONTACT",
    # language switcher
    "Español": "Español",
    "English": "English",
}

# --------------------------------------------------------------------------
# Per-route body copy.
#
# Every string below is an adaptation of the live source site
# (97jnvjsg4j.wixsite.com/riki-coach), translated from Spanish into the
# English this build was designed around. Claims of fact — 15 years, Nueva
# Alcántara Club, M3 Academy, "one of the most prestigious padel clubs in the
# world" — are the source's own and are carried across as the source makes
# them. Nothing here is invented about a named person.
# --------------------------------------------------------------------------
PAGE_TEXT = {
    # ---- Home -------------------------------------------------------------
    # Source: Inicio — the hero eyebrow, the three offer cards, the tile row.
    "index.html": {
        "Productora y agencia digital especializada en turismo":
            "High-performance padel academy based in Marbella",
        # three label rows: what we do / where / who it is for
        # (note the double space between "fotografía" and "marca" in the source)
        "audiovisual fotografía  marca &amp; web": "local service · clubs · camps",
        # These two sit in a narrow label column that wraps past ~19 characters
        # and then collides with its own row label, so they are kept short.
        "trabajamos globalmente": "Marbella, Spain",
        "Expertos Desde 2018": "Players and clubs",
        # grid tiles, repointed at real routes
        "Playas de Jandía": "Local service",
        "Peñíscola": "Programmes for clubs",
        "Comunidad Valenciana": "Worldwide",
        "San Miguel de Abona": "The coaches",
        "Guía de Isora": "Camps in Marbella",
    },
    # ---- How we coach -----------------------------------------------------
    # Source: the "local service" card's five bullets, expanded into the five
    # service blocks the layout already has, plus the three-pillar methodology
    # from the Camps page (technical / tactical / physical).
    "coaching/index.html": {
        "Somos creadores": "How we coach",

        "Audiovisual": "High-impact sessions",
        "Web": "Technical &amp; tactical",
        "Fotografía": "Physical preparation",
        "Marca": "Match play with analysis",
        "Creación de marca": "Match play with analysis",
        "Escenas 3D": "Progress tracking",

        "vídeo producción": "Private one-to-one sessions",
        "Edición de vídeo": "Small-group sessions",
        "Contenido para redes sociales": "Every level, beginner to competition",
        "Búsqueda y gestión de localizaciones": "Built around your objectives",
        "Gestión de figurantes/actores": "Coaching in Spanish or English",
        "VESTUARIO / MAQUILLAJE Y PELUQUERÍA": "Court time arranged for you",
        "Drone fpv": "Regular weekly slots",

        "Diseño web": "Technique on every shot",
        "redacción de contenido": "Reading the point",
        "Programación a medida": "Decision-making under pressure",
        "SEO - optimización para buscadores": "Positioning and court movement",
        "alojamiento y dominios": "Playing as a pair",
        "traducción": "Biomechanical refinement",

        "Fotografía profesional": "Racket-specific conditioning",
        "Fotos para redes sociales": "Movement and footwork",
        "Fotografía de interiores": "Injury prevention",
        "Edición fotográfica": "Warm-up and recovery",

        "Estudio y Estrategia": "Supervised match play",
        "Creación de identidad de marca": "Real analysis afterwards",
        "Rediseño": "Levelled, competitive matches",
        "Diseño de material promocional": "Video review on request",

        "Captura de imágenes": "Objectives set per player",
        "Producción de video": "Continuous evaluation",
        "Entrenamiento del modelo": "Progress reviewed over time",
        "Renderizado": "Adjustments as you improve",
        "Publicación en medios online": "A plan that carries session to session",
    },
    # ---- Programmes -------------------------------------------------------
    # Source: the three offer cards on Inicio, plus the Clubs page — its four
    # club programmes and the five-step "Dinámica de impacto".
    "programmes/index.html": {
        "trabajos": "Programmes",
        "Hemos trabajado con destinos y hoteles muy interesantes en proyectos increíbles":
            "Intensive programmes of up to seven days for padel clubs anywhere in the "
            "world — innovation, knowledge and high performance for their members and "
            "their technical staff. Every visit is designed to measure around the needs "
            "and character of each club.",
        # filter labels
        "Audiovisual": "Local service",
        "Fotografía": "For clubs",
        "Web": "Camps",
        "Marca": "All programmes",
        "3D": "Enquire",
        # the three programme cards
        "Playas de Jandía": "Local service",
        "Peñíscola": "Programmes for clubs",
        "San Miguel de Abona": "Camps in Marbella",
    },
    # ---- Camps in Marbella -----------------------------------------------
    # Source: the Camps page — hero, the four "¿Qué incluye la experiencia?"
    # items, and the FAQ.
    "marbella/index.html": {
        "Entornos 3D": "Camps in Marbella",
        "Campo de Golf - Tenerife": "On-court training",
        "Museo": "Sporting experience",
        "Centro histórico": "Discover Marbella",
        "Escultura": "Tailored programmes",
        "Hermita": "Frequently asked",
    },
    # ---- Contact ----------------------------------------------------------
    "contact/index.html": {
        "PONTE EN": "GET IN",
        "Contacto": "Touch",
        "¿Estás planeando un nuevo proyecto?":
            "Coaching in Marbella, a programme for your club, or a camp?",
        "Hablemos 🖖": "Let's talk 🖖",
        "Email": "Email",
        "Teléfono / WhatsApp": "Phone / WhatsApp",
        "Social": "Social",
    },
}

# --------------------------------------------------------------------------
# Paragraphs that carry inline <span>/<strong> markup are not a single text
# node, so they are replaced whole. Keyed by a distinctive anchor substring;
# the innermost enclosing <p> is rewritten.
# --------------------------------------------------------------------------
BLOCK_HTML = {
    "index.html": {
        "Fuerteventura": "Marbella",
        "Audiovisual, y fotograf":
            "High-impact private and group sessions, in Marbella",
        "Audiovisual, web y fotograf":
            "Programmes for players, coaches and technical staff",
        "Tenerife</span>": "Costa del Sol",
        "Audiovisual, web, escenas 3D":
            "Riki Padrón, Head Coach — with Premium Coach Juampi Vanella",
        "Audiovisual y web</span>":
            "Padel camps and international experiences, based in Marbella",
    },
    "coaching/index.html": {
        "Trabajamos con <span":
            "Programmes are what you book. Coaching is what you actually receive. Our "
            "academy offers professional, premium coaching designed specifically for "
            "demanding players and for clubs that want excellence — personalised "
            "programmes built to bring individual and collective talent up to the "
            "standard of high-level competition.",
        "Creamos vídeos personalizados":
            "High-impact individual and group sessions. One coach and a plan that "
            "carries over from one session to the next, rather than starting again each "
            "time — for players who live in Marbella and train with us every week, and "
            "for players here for a few days.",
        "En turismo, una web no solo informa":
            "Advanced technical and tactical development. We work the technical pillar "
            "to refine every shot and the tactical pillar to master reading the game and "
            "decision-making — because a shot practised without a reason to play it "
            "tends not to survive a match.",
        "A través de la fotografía buscamos":
            "Racket-specific physical preparation. Padel asks particular things of the "
            "body — repeated changes of direction, overhead loading and a great deal of "
            "stopping — so the physical pillar is there to make sure the body answers "
            "the demands of international competition.",
        "Creamos marcas pensadas":
            "Match lessons with real analysis. Match play is where the work either holds "
            "up or it does not. We play, then we go back through it properly: what "
            "worked, what did not, and what to carry into the next session.",
        "Creamos escenas y entornos 3D":
            "Thorough tracking of your evolution. Objectives are set per player and "
            "reviewed as you improve, so progress is something we can both see rather "
            "than something we assert.",
    },
    "marbella/index.html": {
        "Creamos escenas y entornos 3D":
            "Raise your competitive level in the Mediterranean with premium padel "
            "programmes designed to reach maximum performance. A complete, personalised "
            "sporting immersion for global clubs and elite players — travel and "
            "international padel experiences in Spain, based in Marbella.",
        "Esta solución facilita la comprensión":
            "Intensive on-court sessions designed to refine technique and tactics in the "
            "surroundings of Marbella, alongside friendly competition and levelled "
            "matches. Riki Padrón coaches at Nueva Alcántara Club (NAC) — described by "
            "the academy as one of the most prestigious padel clubs in the world — with "
            "a methodology developed alongside M3 Academy. Beyond the court, one of the "
            "most exclusive destinations in Europe: we handle the programme, the "
            "matches, the complementary activities and the local recommendations.",
    },
}

# --------------------------------------------------------------------------
# Whole-widget replacements, addressed by Elementor's own ``data-id``.
#
# The coaches page carries its copy in ``text-editor`` widgets whose content
# sits directly inside ``elementor-widget-container`` with no wrapping ``<p>``,
# and one widget holds two paragraphs at once. Neither the text-node pass nor
# the ``<p>``-anchored block pass can address that, so these are swapped by id.
# --------------------------------------------------------------------------
WIDGET_HTML = {
    "coaches/index.html": {
        # page title
        "0c3935d": "The coaches",
        # intro under the title
        "7a1fa05":
            "<p>Riki Padrón, Head Coach, and Juampi Vanella, Premium Coach. Between us "
            "the academy offers a personalised approach for players of every level — and "
            "one very clear objective: to give every player, and every club, a "
            "<strong>premium</strong> experience.</p>",
        # first coach
        "b7c327d":
            "<p><strong>Riki Padrón — Head Coach.</strong> Currently at "
            "<strong>Nueva Alcántara Club (NAC)</strong>, regarded as one of the most "
            "prestigious padel clubs in the world, with a methodology developed "
            "alongside <strong>M3 Academy</strong>. Continuing education alongside elite "
            "professionals, bringing in the most current methodologies in professional "
            "padel.</p>\n\n"
            "<p><strong>Juampi Vanella — Premium Coach.</strong></p>",
        # "More than 15 years at the elite level" — the source's three paragraphs
        "995f43d":
            "<p>With more than <strong>15 years</strong> of professional experience, we "
            "offer a personalised approach to bring on players of every level.</p>\n\n"
            "<p>Across those years we have had the opportunity to work and learn "
            "alongside professionals of a very high standard, absorbing different "
            "methodologies, different ways of understanding training, and systems of "
            "work that have enriched how we teach and how we manage.</p>\n\n"
            "<p>That experience has let us build <strong>a methodology of our own</strong> "
            "based on observation, continuous learning and practical application, with "
            "one very clear objective: to give every player and every club a "
            "<strong>premium</strong> experience.</p>",
        # second heading
        "10710ad": "what you can expect",
        "c2fe054":
            "<p>An experience <strong>completely adapted to your level and your "
            "objectives</strong>. A professional, close and motivating environment, where "
            "every session has a purpose. A high-performance methodology applied "
            "personally — as much for players who want to compete as for those who "
            "simply want to improve and enjoy the sport.</p>",
        "caa130e":
            "<p>Training that is dynamic, demanding and enjoyable, where learning and "
            "motivation always go hand in hand. A place to switch off from the routine, "
            "share the passion for padel, and keep evolving on court — and "
            "<strong>a real commitment to your progress</strong>, helping you enjoy the "
            "game more while you reach your best version.</p>",
    },
}

# --------------------------------------------------------------------------
# The source footer carries Travel Productions' real email addresses, phone
# number and social accounts. All of it goes.
#
# The riki-coach site publishes its own contact pair, and those are the ones
# used here. Note that the phone number it publishes — +34 600 000 000 — is
# plainly a placeholder on the source too; it is carried across unchanged
# rather than invented, and is greppable before launch.
# --------------------------------------------------------------------------
PLACEHOLDER_EMAIL = "info@rikicoach.com"
PLACEHOLDER_PHONE = "+34 600 000 000"

CONTACT_SUBS = {
    "mailto:jose@travelproductions.film": "mailto:" + PLACEHOLDER_EMAIL,
    "mailto:hola@travelproductions.film": "mailto:" + PLACEHOLDER_EMAIL,
    "jose@travelproductions.film": PLACEHOLDER_EMAIL,
    "hola@travelproductions.film": PLACEHOLDER_EMAIL,
    "+34 613 088 421": PLACEHOLDER_PHONE,
    "+34613088421": PLACEHOLDER_PHONE.replace(" ", ""),
    "https://www.instagram.com/travelproductions.film/": "#",
    "https://vimeo.com/travelproductions": "#",
    "https://www.linkedin.com/company/travel-productions-film/": "#",
}

# The cookie sentence wraps a link, so it is not a single text node.
COOKIE_ANCHOR = "Utilizamos cookies"
COOKIE_HTML = ('We use cookies to improve your experience. See our '
               '<a href="/contact/">Legal notice</a> for details.')

# Containers removed outright, addressed by the text they contain. Each names a
# Travel Productions client or case study; none has an equivalent on a padel
# academy site, and re-labelling them would leave the source's portfolio shape
# pretending to be something else.
REMOVE_CONTAINERS = {
    "index.html": [
        "Hotel Bahía del Duque",
        "Dhigali Maldivas",
        "Meliá Hotels &amp; Resorts",
        # The client logo band: nine Travel Productions clients (Meliá, Selina,
        # Cabildo de Tenerife, Islas Canarias, Peñíscola, Mogán, Guía de Isora,
        # proximity, The Tais). A logo wall is a claim about who you have worked
        # for; the academy has not made that claim.
        "Logo-carrusel",
    ],
    # The coaches page carries the same nine-client logo wall as the home page.
    "coaches/index.html": [
        "Logo-carrusel",
    ],
    "programmes/index.html": [
        "Hotel Bahía del Duque",
        "Guía de Isora",
        "Mogán cálido paraíso",
        "Turismo de ",   # split across markup, so the anchor stops at the break
        "Dhigali Maldivas",
        "Meliá Hotels &amp; Resorts",
        # Bare "Selina" also occurs in a filter attribute, which resolves to the
        # wrong (smaller) container; anchor on the heading link instead.
        ">Selina</a>",
    ],
}

# Widgets removed by (class, text) rather than by container. The 3D viewer's
# control legend is orphaned once the Luma embed goes: each instruction is its
# own icon-box widget, and they describe gestures for a scene that is no longer
# on the page.
REMOVE_WIDGETS = {
    "coaching/index.html": [
        ("elementor-widget-icon-box", "Pulsar y desplazar a la vez"),
        ("elementor-widget-icon-box", "Rueda de desplazamiento"),
        ("elementor-widget-icon-box", "Doble clic izquierdo"),
        ("elementor-widget-icon-box", "One-finger drag"),
        ("elementor-widget-icon-box", "Press and scroll with two fingers"),
        ("elementor-widget-icon-box", "Pinch"),
        ("elementor-widget-icon-box", "Double tap"),
    ],
}

# Home grid tiles point at case-study routes that were never in scope. Repoint
# them at the real pages so nothing on the home page dead-ends.
LINK_RETARGET = {
    "/programmes/playas-de-jandia/": "/coaching/",
    "/programmes/peniscola/": "/programmes/",
    "/programmes/san-miguel-de-abona/": "/coaches/",
    "/programmes/guia-de-isora/": "/marbella/",
    "/programmes/hotel-bahia-del-duque/": "/programmes/",
    "/programmes/dhigali-maldivas/": "/programmes/",
    "/programmes/melia-hotels-international/": "/programmes/",
    "/programmes/mogan-calido-paraiso/": "/programmes/",
    "/programmes/turismo-de-canarias/": "/programmes/",
    "/programmes/selina/": "/programmes/",
    "/es/condiciones-legales/": "/contact/",
    "/about/": "/coaches/",
    "/services/": "/coaching/",
    "/work/": "/programmes/",
    "/campo-de-golf/": "/marbella/",
    "/escenas-3d/": "/marbella/",
    "/pruebas-3d-ermita-san-jose-de-los-llanos/": "/marbella/",
    "/pruebas-3d-esculturas/": "/marbella/",
    "/pruebas-3d-iglesia-los-realejos-v2/": "/marbella/",
    "/pruebas-3d-museo-tenerife/": "/marbella/",
}

# Widgets removed by Elementor id, for elements with no text to anchor on.
# The home page carries a "Terres Festival — official competition" selection
# badge as an absolutely-positioned overlay image. It is an award claim about
# Travel Productions, sitting on the academy's home page.
REMOVE_WIDGET_IDS = {
    "index.html": ["daaa4b5"],
}

PAGES = list(HEAD)


def replace_text_nodes(src: str, mapping: dict[str, str]) -> tuple[str, int, list[str]]:
    """Replace whole text nodes only — never a bare substring.

    A text node here is the run of characters between ``>`` and ``<``. Matching
    on that boundary is what makes it safe to rewrite a word as generic as
    "Web" without touching ``class="...web..."`` or a URL.
    """
    hits = 0
    unused = []
    for old, new in mapping.items():
        pattern = re.compile(r"(>)(\s*)" + re.escape(old) + r"(\s*)(<)")
        src, n = pattern.subn(lambda m: m.group(1) + m.group(2) + new + m.group(3) + m.group(4), src)
        if n:
            hits += n
        else:
            unused.append(old)
    return src, hits, unused


def replace_blocks(src: str, mapping: dict[str, str]) -> tuple[str, int, list[str]]:
    """Rewrite whole <p> elements that contain inline markup.

    Text-node replacement cannot reach copy split across a <span> or <strong>,
    so these are matched by a distinctive anchor and the enclosing paragraph is
    replaced outright.
    """
    hits = 0
    unused = []
    # Search the body only. Yoast mirrors page copy into og:description, and an
    # anchor found there resolves to no enclosing paragraph.
    body_at = src.find("<body")
    for anchor, new in mapping.items():
        found = 0
        cursor = body_at if body_at > 0 else 0
        # The same copy can appear in more than one tile, so replace every
        # occurrence rather than just the first.
        while True:
            idx = src.find(anchor, cursor)
            if idx < 0:
                break
            start = src.rfind("<p", 0, idx)
            end = src.find("</p>", idx)
            if start < 0 or end < 0:
                cursor = idx + len(anchor)
                continue
            open_end = src.find(">", start)
            src = src[:open_end + 1] + new + src[end:]
            found += 1
            cursor = open_end + 1 + len(new)
        if found:
            hits += found
        else:
            unused.append(anchor)
    return src, hits, unused


def replace_widgets(src: str, mapping: dict[str, str]) -> tuple[str, int, list[str]]:
    """Replace a widget's contents, addressed by Elementor's own ``data-id``.

    Two shapes are handled, because the layout uses both:

    * a **heading** widget wraps its copy in ``<hN class="...">``. Only the text
      inside that tag is swapped, so the heading keeps its tag and its classes
      (and therefore its styling). Triggered when the replacement carries no
      markup of its own.
    * a **text-editor** widget holds its copy directly inside
      ``elementor-widget-container`` with no wrapping ``<p>``, and sometimes
      holds two paragraphs at once. The whole container body is swapped.

    Neither case can be addressed by the text-node pass or by the ``<p>``
    -anchored block pass, which is why this exists.
    """
    OPEN = '<div class="elementor-widget-container">'
    hits, missing = 0, []
    for did, html in mapping.items():
        anchor = 'data-id="%s"' % did
        i = src.find(anchor)
        j = src.find(OPEN, i) if i != -1 else -1
        if j == -1:
            missing.append(did)
            continue
        open_end = j + len(OPEN)
        # Walk to the </div> that closes this container, counting nesting.
        depth, k = 1, open_end
        while depth:
            nd, cd = src.find("<div", k), src.find("</div>", k)
            if cd == -1:
                break
            if nd != -1 and nd < cd:
                depth, k = depth + 1, nd + 4
            else:
                depth, k = depth - 1, cd + 6
        if depth:
            missing.append(did)
            continue
        close = k - 6
        inner = src[open_end:close]

        head = re.match(r"(\s*<(h[1-6])\b[^>]*>)(.*?)(</\2>\s*)$", inner, re.S)
        if head and "<" not in html:
            body = head.group(1) + html + head.group(4)
        else:
            body = "\n" + html + "\n"
        src = src[:open_end] + body + src[close:]
        hits += 1
    return src, hits, missing


def remove_widgets_by_id(src: str, ids: list[str]) -> tuple[str, int, list[str]]:
    """Delete a whole widget element, addressed by its Elementor ``data-id``."""
    hits, missing = 0, []
    for did in ids:
        anchor = 'elementor-element-%s ' % did
        i = src.find(anchor)
        if i == -1:
            missing.append(did)
            continue
        start = src.rfind("<div", 0, i)
        depth, k = 1, src.find(">", start) + 1
        while depth:
            nd, cd = src.find("<div", k), src.find("</div>", k)
            if cd == -1:
                break
            if nd != -1 and nd < cd:
                depth, k = depth + 1, nd + 4
            else:
                depth, k = depth - 1, cd + 6
        if depth:
            missing.append(did)
            continue
        src = src[:start] + src[k:]
        hits += 1
    return src, hits, missing


def remove_containers(src: str, anchors: list[str]) -> tuple[str, int, list[str]]:
    """Delete the innermost Elementor container holding each anchor."""
    removed = 0
    missing = []
    body_at = src.find("<body")
    for anchor in anchors:
        span = container_span(src, anchor, body_at if body_at > 0 else 0)
        if span is None:
            missing.append(anchor)
            continue
        start, end, _ = span
        src = src[:start] + src[end:]
        removed += 1
    return src, removed, missing


def remove_vimeo_widgets(src: str) -> tuple[str, int]:
    """Delete every Elementor video widget holding a Vimeo player.

    Twenty-one of the source's players sit on each route. They are Travel
    Productions' own films, classified `Embed` by the baseline and never
    downloadable — a derived site has no claim to them and no reason to load
    them. Removing the widget also removes the 403s they generate off-domain.
    """
    spans = widget_spans(src, "elementor-widget-video", "player.vimeo.com")
    for start, end in spans:          # already sorted last-first
        src = src[:start] + src[end:]
    return src, len(spans)


def strip_analytics(src: str) -> tuple[str, int]:
    """Remove the source's Google Analytics.

    The pages ship Travel Productions' GA4 property (G-T5Q0TX0MC4) and its
    linker domain. Left in place, a deployed derived site would report the new
    client's traffic into someone else's account.
    """
    n = 0
    src, c = re.subn(r'<script[^>]*googletagmanager\.com[^>]*>\s*</script>', "", src, flags=re.I)
    n += c
    src, c = re.subn(r'<script[^>]*>(?:(?!</script>).)*?gtag\((?:(?!</script>).)*?</script>', "", src, flags=re.I | re.S)
    n += c
    src, c = re.subn(r'<!-- Google tag \(gtag\.js\).*?-->', "", src, flags=re.S)
    n += c
    src, c = re.subn(r"\s*<link[^>]*dns-prefetch[^>]*googletagmanager[^>]*/?>", "", src, flags=re.I)
    n += c
    # Search Console token: left in place, Travel Productions could verify
    # ownership of the derived site.
    src, c = re.subn(r'\s*<meta\s+name="google-site-verification"[^>]*/?>', "", src, flags=re.I)
    n += c
    return src, n


def remove_luma_widgets(src: str) -> tuple[str, int]:
    """Delete the Luma Labs 3D viewer widgets.

    The scenes are captures from Travel Productions' own Luma account (the
    embed URL carries their username) of Tenerife locations. There is no padel
    equivalent, and the baseline never exercised the scene internals anyway.
    """
    spans = widget_spans(src, "elementor-widget-html", "cdn-luma.com")
    for start, end in spans:
        src = src[:start] + src[end:]
    return src, len(spans)


def remove_widgets(src: str, pairs) -> tuple[str, int]:
    """Remove widgets addressed by (class fragment, contained text)."""
    total = 0
    for cls, needle in pairs:
        spans = widget_spans(src, cls, needle)
        for start, end in spans:
            src = src[:start] + src[end:]
        total += len(spans)
    return src, total


def fix_cursor_handler(src: str) -> tuple[str, int]:
    """Repair the source's `mouseleaveHandler is not defined` error.

    A stray brace closes the enclosing function early, so the declaration ends
    up nested one scope down while the listener that references it is
    registered at top level — a ReferenceError on every page load.

    The baseline deliberately left this alone: repairing a source bug during a
    mirror would be a change, and fidelity came first. That reasoning stops at
    the mirror. This is the derived deliverable, and it should not ship an
    error on every route. The fix closes the outer function first, then
    declares the handler where the listener can actually see it.
    """
    broken = ('function mouseleaveHandler() {\n'
              '  gsap.to(cursorSmall, { opacity: 0 });\n'
              '}}')
    fixed = ('}\n\n'
             'function mouseleaveHandler() {\n'
             '  gsap.to(cursorSmall, { opacity: 0 });\n'
             '}')
    n = src.count(broken)
    return src.replace(broken, fixed), n


def rewrite_contacts(src: str) -> int:
    """Count Travel Productions contact details still present."""
    return sum(src.count(k) for k in CONTACT_SUBS)


def strip_structured_data(src: str) -> int:
    """Count the Yoast schema.org graphs carrying the source's identity.

    The block names Travel Productions as the Organization and carries its real
    email, telephone and social profiles. It is removed rather than rewritten:
    an accurate graph for the academy needs a confirmed legal name, address and
    phone number, none of which the brief has yet. Inventing them to fill the
    tags would be exactly the kind of guess this project refuses to make.
    """
    return len(re.findall(r'<script type="application/ld\+json"[^>]*>.*?</script>', src, re.S))


def rewrite_head(src: str, meta: dict[str, str]) -> tuple[str, int]:
    n = 0

    def sub(pattern, repl, s):
        nonlocal n
        s, c = re.subn(pattern, repl, s, flags=re.I)
        n += c
        return s

    src = sub(r'<html([^>]*)\blang="[^"]*"', r'<html\1lang="en"', src)
    src = sub(r"<title>.*?</title>", "<title>%s</title>" % html.escape(meta["title"]), src)
    src = sub(r'(<meta\s+name="description"\s+content=")[^"]*(")',
              lambda m: m.group(1) + html.escape(meta["description"]) + m.group(2), src)
    src = sub(r'(<meta\s+property="og:title"\s+content=")[^"]*(")',
              lambda m: m.group(1) + html.escape(meta["og_title"]) + m.group(2), src)
    src = sub(r'(<meta\s+property="og:description"\s+content=")[^"]*(")',
              lambda m: m.group(1) + html.escape(meta["description"]) + m.group(2), src)
    src = sub(r'(<meta\s+property="og:site_name"\s+content=")[^"]*(")',
              lambda m: m.group(1) + BRAND + m.group(2), src)
    src = sub(r'(<meta\s+property="og:locale"\s+content=")[^"]*(")', r"\1en_GB\2", src)
    src = sub(r'(<meta\s+property="og:locale:alternate"\s+content=")[^"]*(")', r"\1es_ES\2", src)
    # The source's og:image is a Travel Productions award badge.
    src = sub(r'\s*<meta\s+property="og:image(?::(?:width|height|type))?"\s+content="[^"]*"\s*/?>', "", src)
    # WordPress feed and oEmbed endpoints that no static deliverable serves.
    src = sub(r'\s*<link\s+rel="alternate"[^>]*type="(?:application|text)/(?:rss\+xml|json\+oembed|xml\+oembed)"[^>]*/?>', "", src)
    # Favicon and touch icon are the Travel Productions wordmark.
    src = sub(r'\s*<link[^>]*rel="(?:icon|apple-touch-icon|shortcut icon)"[^>]*/?>', "", src)
    src = sub(r'\s*<meta\s+name="msapplication-TileImage"[^>]*/?>', "", src)
    # Yoast schema.org graph — see strip_structured_data for why it goes rather
    # than gets rewritten.
    src = sub(r'\s*<script type="application/ld\+json"[^>]*>.*?</script>', "", src)
    src = sub(r"Travel Productions", BRAND, src)
    return src, n


def strip_licensed_video(src: str) -> tuple[str, int]:
    """Empty every Elementor background-video link.

    The footage is Travel Productions' client work and cannot be redistributed.
    Only the link is cleared; the container, its motion effects and its layout
    survive so replacement footage drops in without rebuilding the section.
    """
    pattern = re.compile(r'(&quot;background_video_link&quot;:&quot;)(?:\\/|/)[^&]*?\.mp4(&quot;)')
    src, n = pattern.subn(lambda m: m.group(1) + m.group(2), src)
    return src, n


def retarget_links(src: str) -> tuple[str, int]:
    n = 0
    for old, new in sorted(LINK_RETARGET.items(), key=lambda kv: -len(kv[0])):
        c = src.count('href="%s"' % old)
        if c:
            src = src.replace('href="%s"' % old, 'href="%s"' % new)
            n += c
    return src, n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mirror")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.mirror)

    grand = dict(text=0, head=0, video=0, links=0)
    problems = []

    for page in PAGES:
        path = os.path.join(root, page)
        if not os.path.isfile(path):
            problems.append("MISSING PAGE: %s" % page)
            continue
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            src = original = fh.read()

        jsonld = strip_structured_data(src)
        contacts = rewrite_contacts(src)
        # Removals first, so later passes never rewrite copy inside a container
        # that is about to be deleted.
        src, rn, missing_c = remove_containers(src, REMOVE_CONTAINERS.get(page, []))
        src, vim = remove_vimeo_widgets(src)
        src, ga = strip_analytics(src)
        src, luma = remove_luma_widgets(src)
        src, wdg = remove_widgets(src, REMOVE_WIDGETS.get(page, []))
        src, wid, missing_w = remove_widgets_by_id(src, REMOVE_WIDGET_IDS.get(page, []))
        wdg += wid
        src, curfix = fix_cursor_handler(src)
        luma += wdg
        # Elementor stamps the source domain into a page-transition attribute.
        src = src.replace("travelproductions\\.film", "premiumpadelacademy\\.example")
        # Blocks next: they replace whole paragraphs, so running them after a
        # text-node pass could clobber copy that was just written.
        src, bn, unused_b = replace_blocks(src, BLOCK_HTML.get(page, {}))
        src, wn, unused_w = replace_widgets(src, WIDGET_HTML.get(page, {}))
        bn += wn
        src, cn, _ = replace_blocks(src, {COOKIE_ANCHOR: COOKIE_HTML})
        bn += cn
        for old, new in CONTACT_SUBS.items():
            src = src.replace(old, new)
        src, hn = rewrite_head(src, HEAD[page])
        src, tn, unused_g = replace_text_nodes(src, GLOBAL_TEXT)
        src, pn, unused_p = replace_text_nodes(src, PAGE_TEXT.get(page, {}))
        src, vn = strip_licensed_video(src)
        src, ln = retarget_links(src)

        grand["head"] += hn
        grand["text"] += tn + pn + bn
        grand["video"] += vn
        grand["links"] += ln
        grand["jsonld"] = grand.get("jsonld", 0) + jsonld
        grand["removed"] = grand.get("removed", 0) + rn
        grand["contacts"] = grand.get("contacts", 0) + contacts

        grand["vimeo"] = grand.get("vimeo", 0) + vim
        grand["ga"] = grand.get("ga", 0) + ga
        grand["luma"] = grand.get("luma", 0) + luma
        grand["curfix"] = grand.get("curfix", 0) + curfix
        print("  %-22s head %2d  copy %3d  block %2d  video %2d  links %2d  ld %d  cut %d  contact %d  vimeo %2d  ga %d"
              % (page, hn, tn + pn, bn, vn, ln, jsonld, rn, contacts, vim, ga))
        for miss in missing_c:
            problems.append("%s: no container found for %r" % (page, miss[:70]))
        for miss in missing_w:
            problems.append("%s: no widget found for id %r" % (page, miss[:70]))
        # Only per-page misses matter; global chrome legitimately varies by page.
        for miss in unused_p:
            problems.append("%s: no text node matched %r" % (page, miss[:70]))
        for miss in unused_b:
            problems.append("%s: no block matched anchor %r" % (page, miss[:70]))
        for miss in unused_w:
            problems.append("%s: no widget found for data-id %r" % (page, miss[:70]))

        if not args.check and src != original:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(src)

    print()
    print("%s: %d head edit(s), %d copy replacement(s), %d video link(s) cleared, "
          "%d link(s) retargeted, %d schema.org graph(s) removed, %d container(s) cut, "
          "%d source contact detail(s) replaced"
          % ("would apply" if args.check else "applied",
             grand["head"], grand["text"], grand["video"], grand["links"],
             grand.get("jsonld", 0), grand.get("removed", 0), grand.get("contacts", 0)))
    print("             %d Vimeo player widget(s) removed, %d analytics block(s) removed, "
          "%d Luma 3D viewer(s) removed"
          % (grand.get("vimeo", 0), grand.get("ga", 0), grand.get("luma", 0)))
    print("             %d cursor-handler scope bug(s) repaired" % grand.get("curfix", 0))

    if problems:
        print("\n%d unmatched replacement(s) — the map is out of step with the HTML:" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
