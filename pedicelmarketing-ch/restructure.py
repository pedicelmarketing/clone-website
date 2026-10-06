"""One-off structural edits on the English template pages (Task 3). Run once, output committed.

python3 restructure.py normalize   # bs4/lxml round-trip, one top-level block per line (render-neutral)
python3 restructure.py apply       # routes, nav/footer, removals, page-specific edits

Kept in the repo as the record of what was changed against the raw mirror import; it is not
part of the build. Copy is not rewritten here beyond placeholder headings (Task 4 owns copy).
"""
from __future__ import annotations

import copy
import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

HERE = Path(__file__).parent
PAGES = HERE / "pages"
MIRROR = Path(os.environ.get("MIRROR", "/home/openclaw/Coding/ Cloning Sites/clone-website/pedicelmarketing/mirror"))
WEBFLOW_CSS = MIRROR / "_external/cdn.prod.website-files.com/64a2995238dba40820b37689/css/new-pedicel-website.webflow.shared.061801715.css"
LANG_CSS = HERE / "assets" / "lang-switch.css"

ROUTE_MAP = {
    "/service-lead-generation": "/outbound",
    "/service-brand-presence": "/ai-content-video",
    "/service-web-development": "/web-tracking",
    "/service-social-media": "/paid-ads",
    "/about-our-marketing-agency": "/about",
    "/contact-us": "/contact",
    "/our-marketing-portfolio": "/portfolio",
}
FORBIDDEN_NUMBERS = ("10.8%", "10,8%", "250%", "300+")
NAME_FIXES = {"Vanguard Medical Solutions": "ISN Medical", "Benahavis Bistro": "La Taberna Fantástica"}
EMAIL, PHONE = "info@pedicelmarketing.com", "+34 677 196 547"

# Sections Webflow's own CSS hides (display:none) that carry template text: a Lorem-ipsum FAQ,
# the handle-testimonial marquee, the old duplicate service tabs, unused project lists, CMS
# "No items found." placeholders and conditionally-invisible stat blocks. Hidden or not, their
# text would go through translation and the publish gate, so they come out.
HIDDEN_JUNK = (".section.hide", ".section.testimonial", ".section.section-old-services",
               ".section.hide-for-now", ".w-condition-invisible", ".w-dyn-empty")


def pages() -> list[tuple[str, Path]]:
    out = []
    for f in sorted(PAGES.rglob("index.html")):
        rel = f.parent.relative_to(PAGES).as_posix()
        out.append(("/" if rel == "." else f"/{rel}/", f))
    return out


def load(f: Path) -> BeautifulSoup:
    return BeautifulSoup(f.read_text(encoding="utf-8"), "lxml")


def save(f: Path, soup: BeautifulSoup) -> None:
    f.write_text(str(soup), encoding="utf-8")


# ---------------------------------------------------------------- normalize

def _break_lines(parent: Tag) -> None:
    for child in list(parent.children):
        if isinstance(child, Tag):
            prev = child.previous_sibling
            if not (isinstance(prev, NavigableString) and prev.endswith("\n")):
                child.insert_before("\n")


def normalize() -> None:
    for _, f in pages():
        soup = load(f)
        _break_lines(soup.head)
        _break_lines(soup.body)
        for top in soup.body.find_all(True, recursive=False):
            if top.name not in ("script", "style", "noscript"):
                _break_lines(top)
        save(f, soup)
        print(f"normalized {f.relative_to(HERE)}")


# ---------------------------------------------------------------- helpers

def frag(soup: BeautifulSoup, html: str) -> Tag:
    """Parse an HTML snippet into a tag owned by soup."""
    return BeautifulSoup(html, "html.parser").find(True)


def set_meta_title(soup: BeautifulSoup, title: str, description: str) -> None:
    soup.title.string = title
    for m in soup.find_all("meta"):
        key = m.get("name") or m.get("property")
        if key in ("og:title", "twitter:title"):
            m["content"] = title
        elif key in ("description", "og:description", "twitter:description"):
            m["content"] = description


def css_rules_for_id(css: str, old: str, new: str) -> str:
    """Every Webflow CSS rule (incl. inside @media) that targets #old, re-targeted at #new."""
    out = []
    for m in re.finditer(r"(@media[^{]*)\{((?:[^{}]*\{[^}]*\})*)\s*\}", css):
        inner = [r.group(0) for r in re.finditer(r"[^{}]*\{[^}]*\}", m.group(2)) if f"#{old}" in r.group(0).split("{")[0]]
        if inner:
            out.append(m.group(1).strip() + "{" + "".join(" ".join(i.replace(old, new).split()) for i in inner) + "}")
    top = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^}]*\})*\s*\}", "", css)
    for r in re.finditer(r"[^{}]*\{[^}]*\}", top):
        if f"#{old}" in r.group(0).split("{")[0]:
            out.insert(0, " ".join(r.group(0).replace(old, new).split()))
    return "\n".join(out)


# ---------------------------------------------------------------- global edits

def relink(soup: BeautifulSoup) -> None:
    for el in soup.find_all(href=True):
        h = el["href"]
        path, sep, rest = re.match(r"([^#?]*)([#?]?)(.*)", h).groups()
        base = path.rstrip("/") or path
        if base in ROUTE_MAP:
            el["href"] = ROUTE_MAP[base] + sep + rest


def drop_blog(soup: BeautifulSoup) -> int:
    n = 0
    for a in soup.find_all("a", href=re.compile(r"^/blog")):
        (a.parent if a.parent.name == "li" else a).decompose()
        n += 1
    return n


def lang_switch(soup: BeautifulSoup) -> None:
    for menu in soup.select(".w-nav-menu"):
        menu.append(soup.new_tag("div", attrs={"data-lang-switch": ""}))
    wf = soup.head.find("link", rel="stylesheet")
    link = soup.new_tag("link", rel="stylesheet", href="/assets/lang-switch.css")
    (wf.insert_after if wf else soup.head.append)(link)
    link.insert_before("\n")


def form_shim(soup: BeautifulSoup) -> None:
    for s in soup.find_all("script", src="/form-shim.js"):
        s["src"] = "/assets/form-shim-ch.js"


def footer(soup: BeautifulSoup) -> None:
    for legal in soup.select(".section.legal .w-container"):
        legal["class"] = legal.get("class", []) + ["legal-row"]
        links = frag(soup, '<p class="no-margins legal-links"><a href="/impressum">Impressum</a>'
                           '<a href="/datenschutz">Privacy policy</a></p>')
        legal.append(links)
    # The footer email/phone were dead "#" links on the mirror.
    for a in soup.select(".footer a.footer-link[href='#']"):
        t = a.get_text(strip=True)
        if t == EMAIL:
            a["href"] = f"mailto:{EMAIL}"
        elif t == PHONE:
            a["href"] = "tel:" + PHONE.replace(" ", "")


def drop_hidden(soup: BeautifulSoup) -> int:
    n = 0
    for sel in HIDDEN_JUNK:
        for el in soup.select(sel):
            if not el.decomposed:
                el.decompose()
                n += 1
    return n


def drop_quote(soup: BeautifulSoup) -> int:
    """The Lucas Jessen (Airflows) quote: unconfirmed, so removed (operator default)."""
    n = 0
    for card in soup.select(".testimonial-card-big"):
        box = card.find_parent(class_="w-container")
        alone = box is not None and box.get_text(" ", strip=True) == card.get_text(" ", strip=True)
        (box if alone else card).decompose()
        n += 1
    return n


def drop_pricing(soup: BeautifulSoup) -> int:
    n = 0
    for i, sec in enumerate(soup.select("section.section.pricing")):
        n += 1
        if i:                                   # web-tracking had two package tables: one CTA is enough
            sec.decompose()
            continue
        cta = frag(soup,
                   '<section class="section pricing audit-cta"><div class="main-container-new-services w-container">'
                   '<div class="center-content"><h2 class="no-margins">Start with a free audit</h2>'
                   '<div class="space-24"></div><a class="cta w-button" href="/audit">Get a free audit</a>'
                   '</div></div></section>')
        sec.replace_with(cta)
    return n


def fix_current(soup: BeautifulSoup, route: str) -> None:
    """Webflow bakes w--current into the page it was published as; copies inherit the wrong one."""
    here = route.rstrip("/") or "/"
    for a in soup.find_all("a", href=True):
        target = a["href"].split("#")[0].rstrip("/") or "/"
        current = "w--current" in a.get("class", [])
        if current and target != here and a["href"] not in ("#",):
            a["class"] = [c for c in a["class"] if c != "w--current"]
            if a.get("aria-current"):
                del a["aria-current"]


# ---------------------------------------------------------------- page-specific edits

TAB_EXTRA = [  # (source tab name, new tab name, label, href)
    ("Tab 3", "Tab 5", "SEO + AI Visibility", "/seo-ai-visibility"),
    ("Tab 2", "Tab 6", "The Hub", "/hub"),
]


def six_tabs(soup: BeautifulSoup, css: str, page: str) -> list[str]:
    """Webflow w-tabs: 4 service tabs -> 6 (adds SEO + AI visibility and the Hub)."""
    rules = []
    tabs = [t for t in soup.select(".w-tabs") if len(t.select(".w-tab-pane")) == 4]
    assert len(tabs) == 1, f"{page}: expected one 4-tab component, found {len(tabs)}"
    tabs = tabs[0]
    menu, content = tabs.select_one(".w-tab-menu"), tabs.select_one(".w-tab-content")
    for src, new, label, href in TAB_EXTRA:
        link = copy.copy(menu.find("a", attrs={"data-w-tab": src}))
        link["data-w-tab"] = new
        link["class"] = [c for c in link["class"] if c != "w--current"]
        link.find("div").string = label
        menu.append(link)
        pane = copy.copy(content.find("div", attrs={"data-w-tab": src}, recursive=False))
        pane["data-w-tab"] = new
        pane["class"] = [c for c in pane["class"] if c not in ("w--tab-active",) and not c.startswith("tab-pane-tab-")]
        suffix = new.replace("Tab ", "-t")
        for el in pane.find_all(id=True):
            old = el["id"]
            el["id"] = old + suffix
            rules.append(css_rules_for_id(css, old, el["id"]))
        pane.find("h2").string = label
        row = pane.select_one(".tab-row p")
        if row:
            row.string = f"Learn more about {label}!"
        for a in pane.find_all("a", href=True):
            a["href"] = href
        content.append(pane)
    return rules


def placeholder_service(soup: BeautifulSoup, eyebrow: str, h1: str, title: str) -> None:
    set_meta_title(soup, f"{title} | Pedicel Marketing", f"{title} by Pedicel Marketing.")
    hero = soup.select_one(".title-wrap-home-a")
    hero.select_one(".text-span-5").string = eyebrow
    hero.find("h1").string = h1
    soup.select_one("section.section.big .left-project-info .text-span-6").string = title


TEAM = ["Strategy & ads", "Content & motion video", "Web, search & data"]


def about_team(soup: BeautifulSoup) -> None:
    sec = soup.select_one(".section.hero-team")
    slider = sec.select_one(".master-team-slider")
    imgs = [s.select_one(".team-image-wrap img") for s in slider.select(".w-slide")][:3]
    grid = frag(soup, '<div class="ch-team-grid"></div>')
    for img, title in zip(imgs, TEAM):
        card = frag(soup, '<div class="team-tile"><div class="team-image-wrap"></div>'
                          '<div class="team-tile-detail"><div class="text-heading-3"></div></div></div>')
        card.select_one(".team-image-wrap").append(copy.copy(img))
        card.select_one(".text-heading-3").string = title
        grid.append(card)
    slider.replace_with(grid)
    sec["class"] = sec["class"] + ["ch-team"]          # Webflow hid this section; the CH page shows it


def projects(soup: BeautifulSoup, page: str) -> None:
    for sec in soup.select(".section.icons-project-page"):
        if sec.select_one(".rich-text-center-aligned"):  # "Numbers speak louder" stat block
            sec.decompose()
    # Anything else that still carries a forbidden number goes with its nearest block.
    for bad in FORBIDDEN_NUMBERS:
        for node in soup.body.find_all(string=lambda s, b=bad: b in s):
            if node.parent.name not in ("script", "style"):
                print(f"  {page}: extra block with {bad!r} removed")
                (node.find_parent(["section", "div"]) or node.parent).decompose()
    for node in soup.body.find_all(string=lambda s: any(k in s for k in NAME_FIXES)):
        text = str(node)
        for old, new in NAME_FIXES.items():
            text = text.replace(old, new)
        node.replace_with(text)
    for el in soup.find_all(True):
        for attr, val in list(el.attrs.items()):
            if isinstance(val, str) and any(k in val for k in NAME_FIXES):
                for old, new in NAME_FIXES.items():
                    val = val.replace(old, new)
                el[attr] = val


LEGAL = {
    "/impressum/": ("Impressum", "Impressum | Pedicel Marketing", "Legal notice of Pedicel Marketing OÜ.",
                    "<h2>Company</h2>"
                    "<p>Pedicel Marketing OÜ</p>"
                    "<p>Lõõtsa tn 5, 11415 Tallinn, Estonia</p>"
                    "<p>Registry code: 16104440 (Estonian e-Business Register)</p>"
                    "<p>Board member: Sergio Andres Palacio Martinez</p>"
                    "<h2>Contact</h2>"
                    f'<p>Email: <a href="mailto:{EMAIL}">{EMAIL}</a></p>'
                    f'<p>Phone: <a href="tel:{PHONE.replace(" ", "")}">{PHONE}</a></p>'),
    "/datenschutz/": ("Privacy policy", "Privacy policy | Pedicel Marketing", "How Pedicel Marketing handles personal data.",
                      "<p>Last updated 6 October 2026</p>"
                      "<h2>Controller</h2>"
                      "<p>Pedicel Marketing OÜ, Lõõtsa tn 5, 11415 Tallinn, Estonia.</p>"
                      "<p>The full privacy notice follows.</p>"),
}


def legal_page(soup: BeautifulSoup, route: str) -> None:
    h1, title, desc, body = LEGAL[route]
    set_meta_title(soup, title, desc)
    nav = soup.body.select_one(".navbar")
    foot = soup.body.select_one(".footer")
    for top in soup.body.find_all(True, recursive=False):
        if top is not nav and top is not foot and top.name not in ("script", "style", "noscript"):
            top.decompose()
    for s in soup.find_all("script", src="/form-shim.js"):   # no form left on this page
        s.decompose()
    sec = frag(soup, '<div class="section legal-section"><div class="main-container-new-services w-container">'
                     f'<h1 class="no-margins">{h1}</h1><div class="rich-text-block w-richtext">{body}</div>'
                     '</div></div>')
    foot.insert_before(sec)
    sec.insert_after("\n")


# ---------------------------------------------------------------- apply

def apply() -> None:
    css = WEBFLOW_CSS.read_text(encoding="utf-8")
    tab_rules: list[str] = []
    for route, f in pages():
        soup = load(f)
        if soup.select_one("[data-lang-switch]"):
            print(f"skip {route}: already restructured")
            continue
        log = []
        if route == "/":
            soup.select_one(".section.yellow").decompose()   # Google-reviews badge + Lucas Jessen quote
            log.append("reviews badge + quote section")
        if route in LEGAL:
            legal_page(soup, route)
            log.append("legal page")
        log.append(f"hidden {drop_hidden(soup)}")
        log.append(f"quotes {drop_quote(soup)}")
        log.append(f"pricing {drop_pricing(soup)}")
        relink(soup)
        log.append(f"blog {drop_blog(soup)}")
        lang_switch(soup)
        form_shim(soup)
        footer(soup)
        fix_current(soup, route)
        if route in ("/", "/services/"):
            tab_rules += six_tabs(soup, css, route)
            log.append("6 tabs")
        if route == "/seo-ai-visibility/":
            placeholder_service(soup, "SEO + AI VISIBILITY", "SEO + AI Visibility", "SEO + AI Visibility")
        if route == "/hub/":
            placeholder_service(soup, "THE HUB", "The Hub", "The Hub")
        if route == "/about/":
            about_team(soup)
            log.append("team -> 3 discipline cards")
        if route.startswith("/projects/"):
            projects(soup, route)
            log.append("stats removed, names fixed")
        save(f, soup)
        print(f"{route}: " + ", ".join(log))
    if tab_rules:
        marker = "/* generated by restructure.py: grid placement for the two added service tabs */"
        text = LANG_CSS.read_text(encoding="utf-8")
        if marker not in text:
            LANG_CSS.write_text(text.rstrip("\n") + "\n\n" + marker + "\n" + "\n".join(r for r in tab_rules if r) + "\n",
                                encoding="utf-8")


if __name__ == "__main__":
    {"normalize": normalize, "apply": apply}[sys.argv[1] if len(sys.argv) > 1 else "apply"]()
