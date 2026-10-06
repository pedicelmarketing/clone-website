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
JUNK = "‍​  \n\t\r"


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
