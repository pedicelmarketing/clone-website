#!/usr/bin/env python3
"""Capture every text node on a page, tagged with its section + role.

Per `research/understand-the-reference.md` §3. Output: `reports/reference/copy.json` —
a list of `{section, role, text, source_url, target_element}` records.

The "section" is the index of the top-level section element (`main > *`, `body > section`,
`body > header`, `body > footer`) that the text node lives in. The "role" is the tag or
ARIA role of the element. The "source_url" is the URL the text was captured from. The
"target_element" is a CSS selector we can use to re-find the same element after the
redesign iterates the DOM.

Honesty rules (same as nt-site-mirror):
  - Every record has a `meta.evidence_basis` field (DOM+assets confirmed).
  - Empty/whitespace-only text is dropped.
  - Truncated text is marked as `truncated: true` (the page held more text than the
    element's visible region; we capture what we see).
  - `innerText` is preferred over `textContent` so we only get the *visible* copy —
    no hidden microcopy, no script bodies, no display:none blocks.

Usage:
    ~/.venvs/nt-mirror/bin/python inventory_copy.py <url> -o reports/reference/copy.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.0"

# -- in-page extraction --------------------------------------------------

EXTRACT_JS = r"""
() => {
  function uniqueSelector(el) {
    if (!el) return "";
    if (el.id) return '#' + CSS.escape(el.id);
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && parts.length < 6) {
      let part = cur.tagName.toLowerCase();
      if (cur.classList && cur.classList.length > 0) {
        part += '.' + Array.from(cur.classList).slice(0, 3)
          .map(c => CSS.escape(c)).join('.');
      }
      const parent = cur.parentElement;
      if (parent) {
        const sibs = Array.from(parent.children).filter(c => c.tagName === cur.tagName);
        if (sibs.length > 1) {
          part += ':nth-of-type(' + (sibs.indexOf(cur) + 1) + ')';
        }
      }
      parts.unshift(part);
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  }

  const sectionSelector = 'main > *, body > section, body > header, body > footer, body > nav, [role="main"] > *';
  const sections = Array.from(document.querySelectorAll(sectionSelector));
  const out = [];

  // For each section, surface all text-bearing descendants.
  for (let s = 0; s < sections.length; s++) {
    const sec = sections[s];
    // Skip display:none elements (we want visible copy only).
    const cs = getComputedStyle(sec);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;

    const candidates = sec.querySelectorAll(
      'h1, h2, h3, h4, h5, h6, p, button, a[href], label, small, span, li, dt, dd, blockquote, td, th, caption, figcaption, legend, summary'
    );

    for (const c of candidates) {
      // Drop descendants of already-recorded parents (e.g. a <span> inside a <p>
      // counts as the <p>, not separately).
      let parent = c.parentElement;
      let skip = false;
      while (parent && parent !== sec) {
        if (parent.matches('h1, h2, h3, h4, h5, h6, p, button, a[href], label, small, li, dt, dd, blockquote, td, th, caption, figcaption, legend, summary')) {
          skip = true;
          break;
        }
        parent = parent.parentElement;
      }
      if (skip) continue;

      const ccs = getComputedStyle(c);
      if (ccs.display === 'none' || ccs.visibility === 'hidden') continue;

      const text = (c.innerText || c.textContent || '').trim();
      if (!text) continue;

      // Determine role — tag name, with ARIA override.
      const role = c.getAttribute('role') || c.tagName.toLowerCase();

      // Detect truncation: scrollWidth > clientWidth (overflow ellipsis).
      const truncated = c.scrollWidth > c.clientWidth + 1;

      out.push({
        section_index: s + 1,
        section_tag: sec.tagName.toLowerCase(),
        section_id: sec.id || null,
        section_role: sec.getAttribute('aria-labelledby') || null,
        role: role,
        text: text,
        target_element: uniqueSelector(c),
        truncated: truncated,
        text_length: text.length,
      });
    }

    // Also capture the section's own head text, in case it has no inner element
    // that matches our selector list (e.g. a wrapper with no <h2>).
    if (sec.children.length === 0 || !sec.querySelector('h1, h2, h3, h4, h5, h6, p, button, a[href], label')) {
      const secText = (sec.innerText || '').trim();
      if (secText) {
        out.push({
          section_index: s + 1,
          section_tag: sec.tagName.toLowerCase(),
          section_id: sec.id || null,
          section_role: sec.getAttribute('aria-labelledby') || null,
          role: 'section',
          text: secText,
          target_element: uniqueSelector(sec),
          truncated: sec.scrollWidth > sec.clientWidth + 1,
          text_length: secText.length,
        });
      }
    }
  }

  // Also capture alt="" and aria-label="" for image/icon-only elements.
  const altLabels = [];
  for (const el of document.querySelectorAll('img, [role="img"], svg, [aria-label]')) {
    const alt = el.getAttribute('alt');
    const aria = el.getAttribute('aria-label');
    if (alt === '' || aria) {
      // Find the section this element lives in.
      let parent = el.parentElement, sIdx = 0;
      while (parent && !sections.includes(parent)) {
        parent = parent.parentElement;
      }
      if (parent) sIdx = sections.indexOf(parent) + 1;
      altLabels.push({
        section_index: sIdx,
        role: el.getAttribute('role') || el.tagName.toLowerCase(),
        text: (alt !== null ? alt : '') || aria || '',
        alt: alt,
        aria_label: aria,
        target_element: uniqueSelector(el),
        truncated: false,
        text_length: ((alt !== null ? alt : '') || aria || '').length,
      });
    }
  }

  return {
    copy: out,
    alt_labels: altLabels,
    page_context: {
      title: document.title,
      url: location.href,
      section_count: sections.length,
      h1_count: document.querySelectorAll('h1').length,
    },
  };
}
"""


def _sanitize_for_json(value):
    """Recursively replace NaN/Inf with None so json.dumps(allow_nan=False) works."""
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
    return value


def atomic_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    safe = _sanitize_for_json(data)
    text = json.dumps(safe, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    tmp.write_text(text)
    tmp.replace(path)


def parse_viewport(s: str) -> tuple[int, int]:
    try:
        w, h = s.lower().split("x", 1)
        return int(w), int(h)
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            "viewport must be WIDTHxHEIGHT (e.g. 1440x900); got %r" % s
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url", help="Absolute http(s) URL to inventory copy from.")
    ap.add_argument("-o", "--out", default="reports/reference/copy.json",
                    help="Output JSON path.")
    ap.add_argument("--viewport", default="1440x900", type=parse_viewport)
    ap.add_argument("--timeout", type=int, default=45000)
    ap.add_argument("--settle-ms", type=int, default=1500)
    ap.add_argument("--scroll-steps", type=int, default=8)
    ns = ap.parse_args(argv)

    if not (ns.url.startswith("http://") or ns.url.startswith("https://")):
        ap.error("url must be an absolute http:// or https:// URL")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Run: pip install playwright && playwright install chromium",
              file=sys.stderr)
        return 2

    out_path = Path(ns.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = ns.viewport

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    notes: list[str] = []
    access_state = "ok"
    copy: list[dict] = []
    alt_labels: list[dict] = []
    page_context: dict = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                try:
                    page.goto(ns.url, wait_until="domcontentloaded", timeout=ns.timeout)
                except Exception as exc:
                    notes.append("navigation_warning: %s" % exc)
                    access_state = "navigation_error"
                page.wait_for_timeout(ns.settle_ms)
                try:
                    total = page.evaluate("document.body.scrollHeight") or (height * 4)
                    for i in range(1, ns.scroll_steps + 1):
                        page.evaluate("(y) => window.scrollTo({top: y, behavior: 'instant'})",
                                      int(total * i / ns.scroll_steps))
                        page.wait_for_timeout(150)
                    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                    page.wait_for_timeout(300)
                except Exception as exc:
                    notes.append("scroll_warning: %s" % exc)

                try:
                    title = (page.title() or "").strip().lower()
                    if any(m in title for m in ("just a moment", "checking your browser",
                                                "verify you are human", "security check",
                                                "attention required", "captcha")):
                        access_state = "blocked_by_challenge"
                except Exception:
                    pass

                try:
                    raw = page.evaluate(EXTRACT_JS)
                    copy = raw.get("copy") or []
                    alt_labels = raw.get("alt_labels") or []
                    page_context = raw.get("page_context") or {}
                except Exception as exc:
                    notes.append("evaluation_error: %s" % exc)
            finally:
                browser.close()
    except Exception as exc:
        print("playwright runtime error: %s" % exc, file=sys.stderr)
        return 4

    # ---- Quick stats ----
    by_role: dict[str, int] = {}
    for r in copy:
        by_role[r["role"]] = by_role.get(r["role"], 0) + 1
    sections_seen = sorted({r["section_index"] for r in copy})

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "source_url": ns.url,
        "extracted_at": started_at,
        "viewport": "%dx%d" % (width, height),
        "access_state": access_state,
        "meta": {
            "evidence_basis": "DOM+assets confirmed" if access_state == "ok" else "HTTP-200 only",
            "notes": notes,
            "page_context": page_context,
        },
        "summary": {
            "total_text_blocks": len(copy),
            "total_alt_labels": len(alt_labels),
            "sections_seen": sections_seen,
            "by_role": by_role,
            "truncated_blocks": sum(1 for r in copy if r.get("truncated")),
        },
        "copy": copy,
        "alt_labels": alt_labels,
    }

    atomic_write_json(out_path, payload)

    # stdout: the path
    print(str(out_path))
    print("access_state: %s" % access_state, file=sys.stderr)
    print("text_blocks: %d, alt_labels: %d, sections_seen: %s" %
          (len(copy), len(alt_labels), sections_seen), file=sys.stderr)
    print("by_role: %s" % by_role, file=sys.stderr)
    if notes:
        print("notes: %s" % "; ".join(notes), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
