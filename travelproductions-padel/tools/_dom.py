"""Locate the smallest Elementor container enclosing a piece of text.

Elementor nests containers deeply and mixes <div> and <a> as container tags, so
brace-counting on a single tag name is not safe. This walks the document with a
real parser, tracking byte offsets, and returns the innermost element that both
encloses the anchor and looks like an Elementor container.
"""
from __future__ import annotations
from html.parser import HTMLParser

VOID = {"area","base","br","col","embed","hr","img","input","link","meta",
        "param","source","track","wbr"}


class _Locator(HTMLParser):
    def __init__(self, src: str):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.stack: list[tuple[str, int, str]] = []
        self.spans: list[tuple[int, int, str, str]] = []   # start, end, tag, attrs
        self._lines = [0]
        for ln in src.split("\n")[:-1]:
            self._lines.append(self._lines[-1] + len(ln) + 1)

    def _off(self) -> int:
        ln, col = self.getpos()
        return self._lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        raw = self.get_starttag_text() or ""
        if raw.endswith("/>"):
            return
        self.stack.append((tag, self._off(), raw))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                t, start, raw = self.stack[i]
                end = self._off() + len(tag) + 3
                self.spans.append((start, end, t, raw))
                del self.stack[i:]
                return


def widget_spans(src: str, class_needle: str, content_needle: str):
    """All element spans whose start tag carries `class_needle` and whose inner
    text contains `content_needle`. Outermost-only, sorted last-first so a
    caller can delete them without invalidating earlier offsets."""
    p = _Locator(src)
    p.feed(src)
    hits = [(s, e) for s, e, tag, raw in p.spans
            if class_needle in raw and content_needle in src[s:e]]
    hits.sort(key=lambda se: (se[0], -(se[1] - se[0])))
    kept = []
    for s, e in hits:
        if kept and s < kept[-1][1]:      # nested inside one already taken
            continue
        kept.append((s, e))
    return sorted(kept, reverse=True)


def container_span(src: str, anchor: str, start_from: int = 0):
    """Return (start, end, data_id) of the innermost Elementor container
    enclosing `anchor`, or None."""
    idx = src.find(anchor, start_from)
    if idx < 0:
        return None
    p = _Locator(src)
    p.feed(src)
    best = None
    for s, e, tag, raw in p.spans:
        if s <= idx < e and "elementor-element" in raw and "e-con" in raw:
            if best is None or (e - s) < (best[1] - best[0]):
                best = (s, e, raw)
    if best is None:
        return None
    s, e, raw = best
    did = ""
    m = raw.find('data-id="')
    if m >= 0:
        did = raw[m + 9: raw.find('"', m + 9)]
    return s, e, did
