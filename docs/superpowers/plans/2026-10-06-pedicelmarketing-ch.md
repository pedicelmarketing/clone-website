# pedicelmarketing.ch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Swiss DE/FR/EN copy of the Pedicel website, built from the existing Webflow mirror, ready to publish on pedicelmarketing.ch.

**Architecture:** English template pages live in `pedicelmarketing-ch/pages/` (copied from the mirror, then structurally edited by hand). A translation layer (`strings/de.json`, `strings/fr.json`: English text → translated text) and one build script produce `dist/` with German at `/`, French at `/fr/`, English at `/en/`. Assets (`/_external/`) are read from the existing mirror, not copied into git. A check script gates publishing.

**Tech Stack:** Python 3 + BeautifulSoup4/lxml (installed), `unittest` (repo convention), Playwright (installed) for screenshots, nginx + certbot on spire, Comfy Cloud for images.

**Spec:** `docs/superpowers/specs/2026-10-06-pedicelmarketing-ch-design.md`

## Global Constraints
- Work only in worktree `~/Coding/clone-website-wt/feat-pedicelmarketing-ch` (branch `feat/pedicelmarketing-ch`). Do not touch `pedicelmarketing/mirror*` or the live `/var/www/pedicelmarketing`.
- Mirror input path (git-ignored, lives only in the main checkout): `MIRROR=/home/openclaw/Coding/ Cloning Sites/clone-website/pedicelmarketing/mirror` (note the leading space in ` Cloning Sites`; always quote it).
- Languages: `/` = `de` (default, `x-default`), `/fr/` = `fr`, `/en/` = `en`. Canonical host `https://pedicelmarketing.ch`.
- German: Swiss spelling — **never `ß`** (write `ss`), formal "Sie". French: Swiss usage, formal "vous".
- **No prices** anywhere (no `CHF`, `€`, `EUR`, `₦`, "from …/month").
- **No numbers in case studies.** Forbidden strings in `dist/`: `10.8%`, `250%`, `300+`, `Vanguard Medical`, `Benahavis Bistro`.
- **No fake people:** no named staff who don't exist, no invented testimonials or quotes. AI images of people are scene imagery only, never captioned with a name.
- Copy claims stay inside `~/Coding/Pedicel  AI/research/offering.md` "Do not claim" lines.
- Impressum: Pedicel Marketing OÜ · Lõõtsa tn 5, 11415 Tallinn, Estonia · Registry code 16104440 · Board member: Sergio Andres Palacio Martinez · info@pedicelmarketing.com · +34 677 196 547 · no VAT number.
- Blog removed: no `/blog` links in `dist/`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus
1. **A text node that appears in a new page but has no translation** → build must fail loudly (not ship English inside `/fr/`). Pinned by Task 1 `test_missing_translation_fails`.
2. **Internal link from a French page to `/services`** → must become `/fr/services`; links to `/_external/`, `/api/`, `mailto:`, `tel:`, `#`, `http(s)` must stay unchanged. Pinned by Task 1 `test_links_prefixed_only_when_internal`.
3. **Webflow non-breaking/zero-width text (`‍`, `&nbsp;`) and whitespace-only nodes** → must be ignored by extraction, not demanded as translations. Pinned by Task 1 `test_whitespace_and_zwj_ignored`.
4. **Form submitted from the French page** → reaches `/api/forms/ch-contact`, CRM label ends in "(CH)", success message shown in French. Pinned by Task 6 tests + Task 7 live submit.
5. **Phone at 390 px** → language switcher visible in the mobile menu, no horizontal scroll. Pinned by Task 7 screenshot check `scrollWidth <= 390`.

---

## File structure (all under `pedicelmarketing-ch/`)
| File | Responsibility |
|---|---|
| `textlayer.py` | Pure functions: find translatable strings in an HTML doc; apply a translation map; rewrite internal links for a language; set `lang`, canonical, hreflang; fill the language switcher. |
| `extract.py` | CLI: list every string in `pages/` and write missing ones to `strings/todo-<lang>.json`. |
| `build.py` | CLI: `pages/` + `strings/` → `dist/` for de/fr/en; symlink `dist/_external` to the mirror for preview; write `sitemap.xml`, `robots.txt`. |
| `checks.py` | CLI: gate on `dist/` (forbidden strings, ß, prices, broken internal links, hreflang/canonical, blog links). Exit 1 on any failure. |
| `test_textlayer.py`, `test_checks.py` | unittest. |
| `pages/**/index.html` | English template pages (structure + English text). |
| `strings/de.json`, `strings/fr.json` | `{english: translation}`. `en` needs no file. |
| `assets/` | AI images + `form-shim-ch.js` + `lang-switch.css`. |
| `deploy/nginx-pedicelmarketing-ch.conf`, `deploy/publish.sh` | Hosting. |
| `README.md` | How to edit text, build, check, preview, publish. |

Shared file changed: `pedicelmarketing/deploy/form_handler.py` (+2 CH form specs) and its tests.

---

### Task 1: Translation layer (`textlayer.py`) with tests

**Files:**
- Create: `pedicelmarketing-ch/textlayer.py`, `pedicelmarketing-ch/test_textlayer.py`

**Interfaces:**
- Produces:
  - `LANGS = ("de", "fr", "en")`, `DEFAULT = "de"`, `HOST = "https://pedicelmarketing.ch"`
  - `strings_in(html: str) -> list[str]` — ordered, de-duplicated translatable strings (text nodes + `alt`, `placeholder`, `title`, `aria-label`, `value` of submit inputs, `data-wait`, and `content` of meta `description`, `og:title`, `og:description`, `twitter:title`, `twitter:description`; plus `<title>`).
  - `localize(html: str, lang: str, route: str, tmap: dict[str, str]) -> str` — raises `MissingTranslation(list[str])` if any string lacks a translation (when `lang != "en"`).
  - `prefix(lang: str) -> str` — `""` for de, `"/fr"`, `"/en"`.

- [ ] **Step 1: Write the failing tests**

```python
"""python3 -m unittest pedicelmarketing-ch/test_textlayer.py"""
import re, unittest
from textlayer import strings_in, localize, MissingTranslation, prefix

PAGE = """<!DOCTYPE html><html data-wf-domain="www.pedicelmarketing.com"><head><title>Home</title>
<meta name="description" content="We grow you"><meta property="og:title" content="Home">
<link rel="stylesheet" href="/_external/x.css"></head><body>
<nav><a href="/">Home</a><a href="/services">Services</a><div data-lang-switch></div></nav>
<p>Hello <b>world</b></p><p>&nbsp;</p><p>‍</p><p>   </p>
<img src="/_external/a.webp" alt="Team at work">
<form><input type="submit" value="Send" data-wait="Please wait..."><input placeholder="Your email"></form>
<a href="/_external/f.pdf">PDF</a><a href="mailto:info@x.ch">Mail</a><a href="#top">Top</a>
<a href="https://linkedin.com/x">LinkedIn</a><a href="/api/forms/ch-contact">api</a>
<script>var s = "not text";</script></body></html>"""

DE = {"Home": "Startseite", "We grow you": "Wir lassen Sie wachsen", "Services": "Leistungen",
      "Hello": "Hallo", "world": "Welt", "Team at work": "Team bei der Arbeit", "Send": "Senden",
      "Please wait...": "Bitte warten...", "Your email": "Ihre E-Mail", "PDF": "PDF", "Mail": "E-Mail",
      "Top": "Nach oben", "LinkedIn": "LinkedIn", "api": "api"}


class Strings(unittest.TestCase):
    def test_collects_text_attrs_and_meta(self):
        s = strings_in(PAGE)
        for want in ["Home", "We grow you", "Hello", "world", "Team at work", "Send", "Please wait...", "Your email"]:
            self.assertIn(want, s)
        self.assertNotIn("not text", s)
        self.assertEqual(len(s), len(set(s)))

    def test_whitespace_and_zwj_ignored(self):
        s = strings_in(PAGE)
        self.assertFalse(any(not x.strip("‍  \n\t") for x in s))


class Localize(unittest.TestCase):
    def test_translates_and_sets_lang(self):
        out = localize(PAGE, "de", "/", DE)
        self.assertRegex(out, r'<html[^>]*\blang="de"')
        self.assertIn("Hallo", out)
        self.assertIn('content="Wir lassen Sie wachsen"', out)
        self.assertIn('value="Senden"', out)
        self.assertNotIn("Hello", out)

    def test_missing_translation_fails(self):
        with self.assertRaises(MissingTranslation) as ctx:
            localize(PAGE, "fr", "/", {"Home": "Accueil"})
        self.assertIn("Hello", ctx.exception.missing)

    def test_english_needs_no_map(self):
        self.assertIn("Hello", localize(PAGE, "en", "/", {}))

    def test_links_prefixed_only_when_internal(self):
        out = localize(PAGE, "fr", "/", {k: k for k in DE})
        self.assertIn('href="/fr/"', out)
        self.assertIn('href="/fr/services"', out)
        for kept in ['href="/_external/f.pdf"', 'href="mailto:info@x.ch"', 'href="#top"',
                     'href="https://linkedin.com/x"', 'href="/api/forms/ch-contact"', 'href="/_external/x.css"']:
            self.assertIn(kept, out)
        self.assertEqual(prefix("de"), "")

    def test_hreflang_canonical_and_switcher(self):
        out = localize(PAGE, "fr", "/services/", {k: k for k in DE})
        self.assertIn('<link rel="canonical" href="https://pedicelmarketing.ch/fr/services/"', out)
        for lang, url in [("de", "/services/"), ("fr", "/fr/services/"), ("en", "/en/services/"), ("x-default", "/services/")]:
            self.assertIn(f'hreflang="{lang}" href="https://pedicelmarketing.ch{url}"', out)
        self.assertIn('class="lang-switch"', out)
        self.assertIn('aria-current="true"', out)          # FR marked current
        self.assertIn('data-wf-domain="pedicelmarketing.ch"', out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, expect failure** — `cd pedicelmarketing-ch && python3 -m unittest test_textlayer -v` → `ModuleNotFoundError: textlayer`.

- [ ] **Step 3: Implement `textlayer.py`**

```python
"""Translation layer for pedicelmarketing.ch: English template page -> one language.

Strings are keyed by their English text, so the same sentence on two pages is translated
once, and editing an English sentence surfaces as a missing translation instead of
silently shipping stale text.
"""
from __future__ import annotations

from bs4 import BeautifulSoup, Comment, NavigableString

LANGS = ("de", "fr", "en")
DEFAULT = "de"
HOST = "https://pedicelmarketing.ch"
LABELS = {"de": "DE", "fr": "FR", "en": "EN"}
SKIP_TAGS = {"script", "style", "noscript", "code"}
TEXT_ATTRS = ("alt", "placeholder", "title", "aria-label", "data-wait")
META_KEYS = {"description", "og:title", "og:description", "twitter:title", "twitter:description"}
KEEP_PREFIXES = ("/_external/", "/api/", "/assets/", "//")
JUNK = "‍​  \n\t\r"


class MissingTranslation(Exception):
    def __init__(self, missing: list[str]):
        super().__init__(f"{len(missing)} untranslated: {missing[:5]}")
        self.missing = missing


def _norm(s: str) -> str:
    return " ".join(s.split())


def _real(s: str) -> bool:
    return bool(s and s.strip(JUNK))


def _slots(soup):
    """Yield (getter, setter) pairs for every translatable string, in document order."""
    if soup.title and soup.title.string:
        t = soup.title
        yield (lambda t=t: t.string), (lambda v, t=t: t.string.replace_with(v))
    for m in soup.find_all("meta"):
        key = m.get("name") or m.get("property")
        if key in META_KEYS and m.get("content"):
            yield (lambda m=m: m["content"]), (lambda v, m=m: m.__setitem__("content", v))
    body = soup.body or soup
    for node in body.find_all(string=True):
        if isinstance(node, Comment) or node.parent.name in SKIP_TAGS:
            continue
        yield (lambda n=node: str(n)), (lambda v, n=node: n.replace_with(_keep_space(str(n), v)))
    for el in body.find_all(True):
        for attr in TEXT_ATTRS:
            if el.get(attr):
                yield (lambda el=el, a=attr: el[a]), (lambda v, el=el, a=attr: el.__setitem__(a, v))
        if el.name == "input" and el.get("type") == "submit" and el.get("value"):
            yield (lambda el=el: el["value"]), (lambda v, el=el: el.__setitem__("value", v))


def _keep_space(old: str, new: str) -> str:
    lead = old[: len(old) - len(old.lstrip())]
    trail = old[len(old.rstrip()):]
    return lead + new + trail


def strings_in(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    seen: dict[str, None] = {}
    for get, _ in _slots(soup):
        s = _norm(get())
        if _real(s):
            seen.setdefault(s, None)
    return list(seen)


def prefix(lang: str) -> str:
    return "" if lang == DEFAULT else f"/{lang}"


def _url(lang: str, route: str) -> str:
    return f"{HOST}{prefix(lang)}{route}"


def _relink(soup, lang: str) -> None:
    p = prefix(lang)
    if not p:
        return
    for el in soup.find_all(href=True):
        h = el["href"]
        if h.startswith("/") and not h.startswith(KEEP_PREFIXES):
            el["href"] = p + h if h != "/" else p + "/"


def _head_links(soup, lang: str, route: str) -> None:
    head = soup.head
    for old in head.find_all("link", rel=["canonical", "alternate"]):
        old.decompose()
    canon = soup.new_tag("link", rel="canonical", href=_url(lang, route))
    head.append(canon)
    for code in LANGS + ("x-default",):
        target = DEFAULT if code == "x-default" else code
        head.append(soup.new_tag("link", rel="alternate", hreflang=code, href=_url(target, route)))


def _switcher(soup, lang: str, route: str) -> None:
    for slot in soup.select("[data-lang-switch]"):
        slot.clear()
        slot["class"] = "lang-switch"
        for code in LANGS:
            a = soup.new_tag("a", href=f"{prefix(code)}{route}", hreflang=code, lang=code)
            a.string = LABELS[code]
            if code == lang:
                a["aria-current"] = "true"
            slot.append(a)


def localize(html: str, lang: str, route: str, tmap: dict[str, str]) -> str:
    soup = BeautifulSoup(html, "lxml")
    if lang != "en":
        missing: dict[str, None] = {}
        for get, put in list(_slots(soup)):
            s = _norm(get())
            if not _real(s):
                continue
            if s in tmap and tmap[s]:
                put(tmap[s])
            else:
                missing.setdefault(s, None)
        if missing:
            raise MissingTranslation(list(missing))
    soup.html["lang"] = lang
    soup.html["data-wf-domain"] = "pedicelmarketing.ch"
    _relink(soup, lang)
    _head_links(soup, lang, route)
    _switcher(soup, lang, route)
    return str(soup)
```

Note: `_switcher` runs after `_relink`, so switcher links are not double-prefixed.

- [ ] **Step 4: Run** `python3 -m unittest test_textlayer -v` → all PASS. Fix and re-run until green.
- [ ] **Step 5: Commit** `git add pedicelmarketing-ch/textlayer.py pedicelmarketing-ch/test_textlayer.py && git commit -m "pedicelmarketing.ch: translation layer keyed by English text"`

---

### Task 2: Build, extract and check CLIs

**Files:**
- Create: `pedicelmarketing-ch/build.py`, `pedicelmarketing-ch/extract.py`, `pedicelmarketing-ch/checks.py`, `pedicelmarketing-ch/test_checks.py`, `pedicelmarketing-ch/.gitignore` (`dist/`, `shots/`, `strings/todo-*.json`)

**Interfaces:**
- Consumes: `strings_in`, `localize`, `MissingTranslation`, `LANGS`, `prefix`, `HOST` from Task 1.
- Produces:
  - `build.py [--lang de|fr|en|all]` → `dist/`; exit 1 listing untranslated strings per page.
  - `extract.py` → `strings/todo-de.json`, `strings/todo-fr.json` (missing English keys with `""` values).
  - `checks.py [dist]` → prints one line per failure, exit 1 if any. Function `problems(dist: Path) -> list[str]` for tests.

- [ ] **Step 1: Failing tests for `checks.problems`**

```python
"""python3 -m unittest pedicelmarketing-ch/test_checks.py"""
import tempfile, unittest
from pathlib import Path
from checks import problems

OK = ('<html lang="de"><head><link rel="canonical" href="https://pedicelmarketing.ch/">'
      '<link rel="alternate" hreflang="de" href="https://pedicelmarketing.ch/"></head>'
      '<body><a href="/services">x</a></body></html>')


def site(pages: dict[str, str]) -> Path:
    root = Path(tempfile.mkdtemp())
    for route, html in pages.items():
        f = root / route.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html)
    return root


class Checks(unittest.TestCase):
    def test_clean_site_passes(self):
        self.assertEqual(problems(site({"/": OK, "/services": OK})), [])

    def test_each_rule_fires(self):
        bad = {
            "eszett": OK.replace("x<", "Strasse Straße<"),
            "price": OK.replace("x<", "ab CHF 2'900<"),
            "fake number": OK.replace("x<", "10.8% engagement<"),
            "leftover name": OK.replace("x<", "Vanguard Medical Solutions<"),
            "blog link": OK.replace('href="/services"', 'href="/blog"'),
            "broken link": OK.replace('href="/services"', 'href="/nope"'),
            "no canonical": OK.replace('rel="canonical"', 'rel="x"'),
        }
        for name, html in bad.items():
            with self.subTest(name):
                self.assertTrue(problems(site({"/": html, "/services": OK})), name)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** → fails (`No module named checks`).

- [ ] **Step 3: Implement `checks.py`**

```python
"""Publish gate for pedicelmarketing.ch: python3 checks.py [dist]  (exit 1 on any problem)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

FORBIDDEN = ["ß", "10.8%", "10,8%", "250%", "300+", "Vanguard Medical", "Benahavis Bistro",
             "Marianna Levchenko", "Leo Grant", "Lorem ipsum"]
PRICE = re.compile(r"(CHF|EUR|€|₦)\s?\d|\d\s?(CHF|EUR|€)", re.I)


def _exists(dist: Path, href: str) -> bool:
    path = href.split("#")[0].split("?")[0].strip("/")
    return (dist / path / "index.html").exists() or (dist / path).is_file() or path.startswith("_external")


def problems(dist: Path) -> list[str]:
    out: list[str] = []
    for f in sorted(dist.rglob("index.html")):
        rel = f.relative_to(dist)
        html = f.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ")
        for bad in FORBIDDEN:          # visible text only: Webflow CSS can contain "250%"
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
```

- [ ] **Step 4: Implement `build.py`**

```python
"""pages/ (English templates) + strings/<lang>.json -> dist/ (de at /, fr at /fr/, en at /en/).

python3 build.py            # all languages; exit 1 listing untranslated strings
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from textlayer import HOST, LANGS, MissingTranslation, localize, prefix

HERE = Path(__file__).parent
PAGES, STRINGS, DIST, ASSETS = HERE / "pages", HERE / "strings", HERE / "dist", HERE / "assets"
MIRROR = Path(os.environ.get("MIRROR", "/home/openclaw/Coding/ Cloning Sites/clone-website/pedicelmarketing/mirror"))


def routes() -> list[tuple[str, Path]]:
    out = []
    for f in sorted(PAGES.rglob("index.html")):
        rel = f.parent.relative_to(PAGES).as_posix()
        out.append(("/" if rel == "." else f"/{rel}/", f))
    return out


def tmap(lang: str) -> dict[str, str]:
    f = STRINGS / f"{lang}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def main() -> int:
    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()
    failed = 0
    for lang in LANGS:
        m = tmap(lang)
        for route, src in routes():
            try:
                html = localize(src.read_text(encoding="utf-8"), lang, route, m)
            except MissingTranslation as e:
                failed += len(e.missing)
                print(f"[{lang}] {route}: {len(e.missing)} untranslated, e.g. {e.missing[0]!r}")
                continue
            dest = DIST / prefix(lang).lstrip("/") / route.strip("/") / "index.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(html, encoding="utf-8")
    if (DIST / "404" / "index.html").exists():
        shutil.copy(DIST / "404" / "index.html", DIST / "404.html")
    shutil.copytree(ASSETS, DIST / "assets", dirs_exist_ok=True)
    (DIST / "_external").symlink_to(MIRROR / "_external")
    urls = [f"{HOST}{prefix(l)}{r}" for l in LANGS for r, _ in routes() if r != "/404/"]
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {HOST}/sitemap.xml\n")
    print(f"build: {len(routes())} pages x {len(LANGS)} languages" + (f", {failed} untranslated" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

The 404 page is kept as `pages/404/index.html` (so it is translated like the others); `build.py` copies the German one to `dist/404.html` for nginx's `error_page`.

- [ ] **Step 5: Implement `extract.py`**

```python
"""List English strings in pages/ that strings/<lang>.json does not translate yet.

python3 extract.py   -> strings/todo-de.json, strings/todo-fr.json   ({english: ""}, page order)
"""
import json
from build import PAGES, STRINGS, routes, tmap
from textlayer import strings_in

for lang in ("de", "fr"):
    have, todo = tmap(lang), {}
    for _, f in routes():
        for s in strings_in(f.read_text(encoding="utf-8")):
            if not have.get(s):
                todo.setdefault(s, "")
    STRINGS.mkdir(exist_ok=True)
    (STRINGS / f"todo-{lang}.json").write_text(json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{lang}: {len(todo)} strings to translate")
```

- [ ] **Step 6: Run** `python3 -m unittest test_textlayer test_checks -v` → PASS.
- [ ] **Step 7: Commit** `git commit -m "pedicelmarketing.ch: build, extract and publish-gate scripts"`

---

### Task 3: English template pages (structure)

**Files:**
- Create: `pedicelmarketing-ch/pages/**/index.html` (14 routes + `404/`), `pedicelmarketing-ch/assets/lang-switch.css`, `pedicelmarketing-ch/import_pages.sh`

**Interfaces:**
- Consumes: `build.py` (Task 2) for preview (`--lang en` run works because en needs no map).
- Produces: routes `/`, `/services/`, `/outbound/`, `/ai-content-video/`, `/web-tracking/`, `/paid-ads/`, `/seo-ai-visibility/`, `/hub/`, `/audit/`, `/about/`, `/contact/`, `/portfolio/`, `/projects/{coeo,isnmedical,latabernafantastica,sana}/`, `/impressum/`, `/datenschutz/`, `/404/`. Every nav has `<div data-lang-switch></div>`.

- [ ] **Step 1: Import script** (`import_pages.sh`) — copies mirror pages to their new routes:

```bash
#!/usr/bin/env bash
set -euo pipefail
M="${MIRROR:-/home/openclaw/Coding/ Cloning Sites/clone-website/pedicelmarketing/mirror}"
P="$(cd "$(dirname "$0")" && pwd)/pages"
cp_page() { mkdir -p "$P/$2"; cp "$M/$1/index.html" "$P/$2/index.html"; }
cp_page _ .
cp_page services services
cp_page service-lead-generation outbound
cp_page service-brand-presence ai-content-video
cp_page service-web-development web-tracking
cp_page service-social-media paid-ads
cp_page service-lead-generation seo-ai-visibility
cp_page service-brand-presence hub
cp_page audit audit
cp_page about-our-marketing-agency about
cp_page contact-us contact
cp_page our-marketing-portfolio portfolio
for p in coeo isnmedical latabernafantastica sana; do cp_page "projects/$p" "projects/$p"; done
cp_page contact-us impressum
cp_page contact-us datenschutz
mkdir -p "$P/404"; cp "$M/404.html" "$P/404/index.html"
echo "imported $(find "$P" -name index.html | wc -l) pages"
```

Run once, commit the raw import as its own commit ("raw import from mirror") so later diffs show only our edits.

- [ ] **Step 2: Global structural edits on every page** (a one-off Python script `restructure.py` using BeautifulSoup, run once, committed with its output):
  - Rewrite nav/footer hrefs: `/service-lead-generation`→`/outbound`, `/service-brand-presence`→`/ai-content-video`, `/service-web-development`→`/web-tracking`, `/service-social-media`→`/paid-ads`, `/about-our-marketing-agency`→`/about`, `/contact-us`→`/contact`, `/our-marketing-portfolio`→`/portfolio`.
  - Remove every `<a href="/blog...">` and its list item.
  - Insert `<div data-lang-switch></div>` as the last child of the nav menu element (`.w-nav-menu`) on every page, and add `<link rel="stylesheet" href="/assets/lang-switch.css">` to `<head>`.
  - Swap `<script src="/form-shim.js">` for `<script src="/assets/form-shim-ch.js">` (file arrives in Task 6).
  - Add footer links Impressum + Datenschutz next to the copyright line.
  - Keep the footer "Offices" block (real offices).
- [ ] **Step 3: Page-specific structural edits (by hand):**
  - **Home:** service tabs become 6 (duplicate one tab pane twice for SEO+GEO and Hub; the tab component is Webflow `w-tabs` — duplicate both `w-tab-link` and `w-tab-pane`, keeping `data-w-tab` names unique). **Remove the handle-testimonial marquee** (Zen Chan … Nick South — template placeholders) and the "Excellent / Google Reviews" badge. Keep the Lucas Jessen (Airflows) quote **only if the operator confirms it is real** (open question; default: remove).
  - **About:** remove the team carousel names/roles (Marianna Levchenko, Leo Grant — template placeholders); replace the 6 team cards with 3 unnamed scene cards (images arrive in Task 5) titled by discipline. Keep mission/vision/values/community sections.
  - **Projects (4):** delete every element containing `10.8%`, `250%`, `300+`; replace "Vanguard Medical Solutions" → "ISN Medical", "Benahavis Bistro" → "La Taberna Fantástica".
  - **Impressum / Datenschutz:** strip the contact form section from the copied contact page, keep header/footer, put a single rich-text block.
  - **Pricing:** remove any price element (old service pages list "from €…" packages) — the price tables come out entirely; their CTA becomes "Get a free audit".
- [ ] **Step 4: `assets/lang-switch.css`**

```css
.lang-switch{display:flex;gap:.5rem;align-items:center;margin-left:1rem;font-size:.875rem;letter-spacing:.04em}
.lang-switch a{color:inherit;text-decoration:none;opacity:.55;padding:.25rem}
.lang-switch a[aria-current="true"]{opacity:1;font-weight:600;border-bottom:2px solid currentColor}
@media (max-width:991px){.lang-switch{margin:1rem 0 0;justify-content:center}}
```

- [ ] **Step 5: Verify:** `MIRROR=... python3 build.py` (de/fr fail as expected — no strings yet), then serve and open `/en/` locally: `python3 -m http.server 8090 -d dist` → every nav link opens a page; no `/blog`. Run `python3 checks.py` and confirm the only failures are pages missing for de/fr.
- [ ] **Step 6: Commit** `"pedicelmarketing.ch: English template pages — new routes, no blog, no placeholder people or numbers"`

---

### Task 4: English copy (rewrite) → then German and French strings

**Files:**
- Modify: `pedicelmarketing-ch/pages/**/index.html` (English text only)
- Create: `pedicelmarketing-ch/strings/de.json`, `pedicelmarketing-ch/strings/fr.json`, `pedicelmarketing-ch/COPY.md` (the English copy deck, page by page, for review)

**Interfaces:** Consumes `extract.py` / `build.py` / `checks.py` (Task 2).

- [ ] **Step 1: Write the English copy deck `COPY.md`** from `~/Coding/Pedicel  AI/research/offering.md` (pillars, edges, do-not-claim) and `research/competitors/ch/summary.md` (5 gaps). Per page: H1, subhead, section copy, CTA. Rules:
  - Positioning line: AI-first growth agency for Swiss SMEs; one team in DE/FR/EN; content, ads, search and outreach run from one client Hub that learns from every approval.
  - Keep sentences inside one text node where possible (avoid `<b>`/`<a>` mid-sentence): the string layer translates node by node, and split sentences translate badly.
  - Every CTA → "Get a free AI audit" (`/audit`) or "Book a call" (`/contact`). No prices.
  - Hub page: Requests, Approvals, Calendar, Analytics + AI copilot, Brand score, Inspiration feed; manager approval before client sees anything; learning loop. No performance-prediction claims.
  - SEO + AI visibility page: technical SEO, Google Business Profile, monthly tracking of answers in ChatGPT, Gemini, Perplexity, Google AI. No "#1 on Maps", no FAQ rich results.
  - Outbound: LinkedIn from the client's team profiles, manager approves every send, WhatsApp to opted-in customers only, calls. **No cold email** (undecided).
  - Case studies: goals + work done + about the partner; ISN adds "live client Hub at hub.pedicelmarketing.com" and "12-month audit of 730 posts" (no lift claims).
  - Impressum/Datenschutz text: exact entity block from Global Constraints; Datenschutz covers controller, data (form fields, server logs, analytics), purposes, processors (Supabase — EU region per project settings; Brevo/Resend email; PostHog EU), cross-border transfer note (Estonia/EU — adequate under nDSG), retention, rights (nDSG + GDPR), contact. Header line: "Last updated 6 October 2026".
- [ ] **Step 2: Put the English copy into `pages/`** (edit text nodes and meta descriptions/titles in place). Build `--lang en` and read `/en/` in the browser.
- [ ] **Step 3: Operator review gate.** Send `COPY.md` (SendUserFile) and wait for the OK before translating — translation cost multiplies every later change by 3.
- [ ] **Step 4:** `python3 extract.py` → `strings/todo-de.json`, `todo-fr.json`. Translate every value (Swiss German, `ss`, "Sie"; Swiss French, "vous"). Keep brand/product names untranslated (Pedicel, Hub, LinkedIn, WhatsApp, Google, ChatGPT). Save as `strings/de.json` / `fr.json` (merge, never drop keys).
- [ ] **Step 5:** `python3 build.py && python3 checks.py` → `build: 19 pages x 3 languages`, `checks: all clear`. Native-quality pass: dispatch one reviewer subagent per language to read every `dist/` page's visible text and list unidiomatic or German-German (not Swiss) phrasing; apply fixes to the JSON.
- [ ] **Step 6: Commit** `"pedicelmarketing.ch: Swiss copy in EN, DE, FR"`

---

### Task 5: AI scene images

**Files:**
- Create: `pedicelmarketing-ch/assets/img/*.webp` (6–8 images), `pedicelmarketing-ch/assets/img/PROMPTS.md`
- Modify: pages whose people images are replaced (home hero/process, about, audit, contact)

- [ ] **Step 1:** List every `<img>` on the template pages that shows people (from the mirror: `first section-19..23`, `Team 3–6`, `pexels-cottonbro-studio-*`, `dwq.webp`, `image 26/27/30/31`). Record each slot's pixel size in `PROMPTS.md`.
- [ ] **Step 2:** Generate on Comfy Cloud (load `running-comfy-cloud-workflows` skill; `estimate_credits` first; total budget ≈ CHF 3). Prompt style: photoreal, natural light, Swiss office/studio settings (Zurich/Lausanne-style interiors, lake or Alpine view through a window at most), mixed ages and genders, mostly Central-European looks, people working (laptops, whiteboard, video shoot, client meeting). No logos, no text, no flags.
- [ ] **Step 3:** Convert to webp at slot size (`cwebp -q 82`), save under `assets/img/`, point the `<img src>` (and `srcset` — remove the Webflow `srcset`/`sizes` on replaced images) to `/assets/img/<name>.webp`. Write a real `alt` in English (it then gets translated by the string layer — re-run `extract.py`, add DE/FR).
- [ ] **Step 4:** Look at every image yourself (Read the file) — reject extra fingers, warped faces, fake text.
- [ ] **Step 5:** build + checks green. Commit `"pedicelmarketing.ch: Swiss scene imagery"`.

---

### Task 6: Forms tagged (CH)

**Files:**
- Modify: `pedicelmarketing/deploy/form_handler.py` (FORMS dict, lines 83–105)
- Modify: `pedicelmarketing/deploy/test_form_pitch.py`
- Create: `pedicelmarketing-ch/assets/form-shim-ch.js`

**Interfaces:**
- Produces: endpoints `/api/forms/ch-audit` (label `"Website Audit request (CH)"`, pitch True) and `/api/forms/ch-contact` (label `"Contact form (CH)"`); same field maps as the .com specs.

- [ ] **Step 1: Failing test** (append to `test_form_pitch.py`):

```python
class SwissForms(unittest.TestCase):
    def test_ch_specs_mirror_com_with_ch_label(self):
        for com, ch in [("/api/forms/audit", "/api/forms/ch-audit"), ("/api/forms/contact", "/api/forms/ch-contact")]:
            self.assertEqual(FORMS[ch]["crm"], FORMS[com]["crm"])
            self.assertEqual(FORMS[ch]["fields"], FORMS[com]["fields"])
            self.assertTrue(FORMS[ch]["label"].endswith("(CH)"))
        self.assertTrue(FORMS["/api/forms/ch-audit"]["pitch"])
        self.assertNotIn("(CH)", FORMS["/api/forms/audit"]["label"])
```

- [ ] **Step 2:** `cd pedicelmarketing/deploy && python3 -m unittest test_form_pitch -v` → KeyError fail.
- [ ] **Step 3:** After the `FORMS = {...}` literal add:

```python
# pedicelmarketing.ch posts to its own paths so its leads are tagged in the Hub CRM.
FORMS["/api/forms/ch-audit"] = {**FORMS["/api/forms/audit"], "label": "Website Audit request (CH)"}
FORMS["/api/forms/ch-contact"] = {**FORMS["/api/forms/contact"], "label": "Contact form (CH)"}
```

- [ ] **Step 4:** Tests pass (`test_form_pitch`, `test_form_spam`).
- [ ] **Step 5:** `assets/form-shim-ch.js` = copy of `pedicelmarketing/deploy/form-shim.js` with only the `ENDPOINTS` map changed to `/api/forms/ch-audit` and `/api/forms/ch-contact`. The success/fail messages are the Webflow `.w-form-done` / `.w-form-fail` text, already translated by the string layer.
- [ ] **Step 6:** Commit `"forms: pedicelmarketing.ch endpoints tagged (CH) in the Hub CRM"`. Deploying the handler change = restart `pedicel-forms` service after merge (note in README).

---

### Task 7: Local QA (screens, links, forms)

**Files:**
- Create: `pedicelmarketing-ch/qa_shots.py`

- [ ] **Step 1:** `qa_shots.py` — Playwright: for every URL in `dist/sitemap.xml` (rewritten to `http://127.0.0.1:8090`), take full-page screenshots at 1440 and 390 width into `shots/<lang>/<route>-<w>.png`, and assert `document.documentElement.scrollWidth <= innerWidth` at 390; print failures, exit 1 if any.

```python
import re, sys, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).parent
urls = [u.replace("https://pedicelmarketing.ch", "http://127.0.0.1:8090")
        for u in re.findall(r"<loc>(.*?)</loc>", (HERE / "dist/sitemap.xml").read_text())]
bad = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(1440, 900), (390, 844)]:
        pg = b.new_page(viewport={"width": w, "height": h})
        for u in urls:
            pg.goto(u, wait_until="networkidle")
            name = u.split("8090", 1)[1].strip("/").replace("/", "_") or "home"
            out = HERE / "shots" / f"{name}-{w}.png"; out.parent.mkdir(exist_ok=True)
            pg.screenshot(path=str(out), full_page=True)
            if w == 390 and pg.evaluate("document.documentElement.scrollWidth > innerWidth"):
                bad.append(f"horizontal scroll at 390: {u}")
    b.close()
print("\n".join(bad) or f"qa: {len(urls)} pages x 2 widths ok"); sys.exit(1 if bad else 0)
```

- [ ] **Step 2:** `python3 -m http.server 8090 -d dist &` then `python3 qa_shots.py`. Look at every screenshot (contact sheet: `montage` if available, else Read in batches). Fix overflow (long German words in buttons/headings: add `hyphens:auto; overflow-wrap:anywhere` to the affected class in `lang-switch.css`).
- [ ] **Step 3:** Live form submits need nginx + the handler, so they happen in Task 8 Step 4.
- [ ] **Step 4:** Commit QA script + any CSS fixes. Send the operator 3 screenshots per language (home, a service page, Hub) via SendUserFile.

---

### Task 8: Hosting on spire (blocked until the domain exists)

**Files:**
- Create: `pedicelmarketing-ch/deploy/nginx-pedicelmarketing-ch.conf`, `pedicelmarketing-ch/deploy/publish.sh`, `pedicelmarketing-ch/README.md`

- [ ] **Step 1: nginx server block** — model on `pedicelmarketing/deploy/nginx-pedicelmarketing.conf.deployed`: `server_name pedicelmarketing.ch www.pedicelmarketing.ch; root /var/www/pedicelmarketing-ch;` include `nginx-pedicel-security.snippet`; `location /api/forms/ { proxy_pass http://127.0.0.1:8081; }` copied verbatim from the .com block; `location /_external/ { alias /var/www/pedicelmarketing/_external/; }` (reuse .com assets, no second copy); `error_page 404 /404.html;`; `try_files $uri $uri/ =404;`; www → apex 301.
- [ ] **Step 2: `publish.sh`** — `python3 build.py && python3 checks.py` must pass, then `sudo rsync -a --delete --exclude _external dist/ /var/www/pedicelmarketing-ch/`, chown www-data, `sudo nginx -t && sudo systemctl reload nginx`.
- [ ] **Step 3: Domain + DNS + TLS** (operator action or Hostinger connector, **ask before buying**): register `pedicelmarketing.ch`; A records `@` and `www` → `62.210.212.199`; wait for `dig +short pedicelmarketing.ch` to return it; `sudo certbot --nginx -d pedicelmarketing.ch -d www.pedicelmarketing.ch`.
- [ ] **Step 4: Live checks:** `curl -sI https://pedicelmarketing.ch/ /fr/ /en/hub/` → 200; submit the contact form once per language with `Name = "TEST CH <lang>"`; confirm 3 leads labelled "Contact form (CH)" in the Hub CRM, then delete them; one audit-form submit with website `example.ch` → lead "(CH)" + pitch queued (delete after).
- [ ] **Step 5:** Restart `pedicel-forms` (handler change from Task 6) before Step 4. Update `spire-config` repo (`./sync.sh --commit`) with the new nginx file.
- [ ] **Step 6:** README: edit text → `strings/*.json` or `pages/`; `python3 extract.py`; `python3 build.py`; `python3 checks.py`; preview; `bash deploy/publish.sh`.
- [ ] **Step 7:** Commit, push branch, open PR against `main` of `pedicelmarketing/clone-website`.
