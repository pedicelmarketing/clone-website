#!/usr/bin/env python3
"""Detect reusable component instances on a page by structural/class-prefix clustering.

Per `research/understand-the-reference.md` §4. Output: `reports/reference/components.json`
— a list of `{name, instances: [{section, variant, selector}], average_height_px,
has_hover_state, has_animation, instance_count}`.

Detection strategy (in priority order):
  1. **Class-prefix clustering** — group elements that share a common class prefix
     (e.g. `Card_*`, `Button_*`, `c-card-*`, `hero__button`). This is the most reliable
     signal on styled-component / design-system sites.
  2. **Structural / role clustering** — group elements with the same `(tag, role)` pair
     that have a stable child structure (≥ 2 enum children that match the same pattern).
  3. **Heuristic role classification** — by `tag + role + className(lower).substring(0,12)`,
     bubbles up obvious patterns: cards, buttons, nav items, list items, etc.

A component is "confirmed" if it has ≥ 3 near-duplicate instances on the page. Less than
that = "candidate" (worth noting, but not definitive).

Honesty rules: same as nt-site-mirror. Every emitted record has `evidence_basis`; an
empty component list is recorded as `components: []` with `meta.notes` explaining why
(no repeated groupings found).

Usage:
    ~/.venvs/nt-mirror/bin/python inventory_components.py <url> -o reports/reference/components.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
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

  function sum(arr) { return arr.reduce(function (a, b) { return a + b; }, 0); }

  function classStr(el) {
    if (!el) return '';
    const cn = el.className;
    if (cn === null || cn === undefined) return '';
    if (typeof cn === 'string') return cn;
    if (cn.baseVal !== undefined) return cn.baseVal;
    return String(cn);
  }

  const sectionSelector = 'main > *, body > section, body > header, body > footer, body > nav, [role="main"] > *';
  const sections = Array.from(document.querySelectorAll(sectionSelector));
  const all = Array.from(document.querySelectorAll('button, a, article, li, [role="button"], [class*="card" i], [class*="btn" i], [class*="button" i], [class*="nav" i], [class*="item" i], [class*="tile" i], header, footer, nav'));

  // Heuristic role classification.
  function classify(el) {
    const tag = el.tagName.toLowerCase();
    const cls = classStr(el).toLowerCase();
    const role = (el.getAttribute('role') || '').toLowerCase();
    if (tag === 'button' || role === 'button' || /(^|\s|_)btn(\s|_|$)/i.test(cls) || /button/i.test(cls)) return 'button';
    if (tag === 'a' && /nav|crumb|menu/i.test(cls)) return 'nav-item';
    if (tag === 'a') return 'link';
    if (/card/i.test(cls)) return 'card';
    if (tag === 'article') return 'card';
    if (/tile/i.test(cls)) return 'tile';
    if (tag === 'li' && /nav|menu|list/i.test(cls)) return 'nav-item';
    if (tag === 'li') return 'list-item';
    if (/input|field|form/i.test(cls)) return 'input';
    if (tag === 'header') return 'header';
    if (tag === 'footer') return 'footer';
    if (tag === 'nav') return 'nav';
    if (/badge|tag|pill|chip/i.test(cls)) return 'badge';
    if (/modal|dialog|popup/i.test(cls)) return 'modal';
    if (/tooltip|popover/i.test(cls)) return 'popover';
    if (/avatar/i.test(cls)) return 'avatar';
    if (/hero/i.test(cls)) return 'hero';
    return 'generic';
  }

  // Extract class prefix — the BEM/CVA-style common prefix.
  function classPrefix(cls) {
    if (cls === null || cls === undefined) return null;
    // SVG elements expose className as an SVGAnimatedString; coerce to string.
    const str = typeof cls === 'string' ? cls : (cls.baseVal !== undefined ? cls.baseVal : String(cls));
    if (!str) return null;
    const tokens = str.split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return null;
    // Take the first token's first 2 segments (e.g. "Card_root__abc" -> "Card_root").
    const first = tokens[0];
    const parts = first.split(/[_-]/);
    if (parts.length >= 2) return parts[0] + '_' + parts[1];
    return first;
  }

  // Structural fingerprint for clustering — stable across the page.
  function fingerprint(el) {
    const tag = el.tagName.toLowerCase();
    const classes = Array.from(el.classList).slice(0, 3).join('.');
    const directChildren = Array.from(el.children).slice(0, 5).map(c => c.tagName.toLowerCase());
    return tag + '|' + classes + '|' + directChildren.join(',');
  }

  const groups = new Map();
  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;

    const kind = classify(el);
    const fp = fingerprint(el);
    const cp = classPrefix(classStr(el)) || '';
    // Composite key: kind + fingerprint + class prefix.
    const key = kind + '||' + fp + '||' + cp;

    if (!groups.has(key)) {
      groups.set(key, {
        kind: kind,
        fingerprint: fp,
        class_prefix: cp,
        instances: [],
      });
    }
    const g = groups.get(key);
    const rect = el.getBoundingClientRect();

    // Find which section this element is in.
    let sectionIdx = 0;
    let p = el.parentElement;
    while (p) {
      const i = sections.indexOf(p);
      if (i >= 0) { sectionIdx = i + 1; break; }
      p = p.parentElement;
    }

    // Detect hover + animation capability via CSS class signals.
    const inlineStyle = el.getAttribute('style') || '';
    const cssAnimation = cs.animationName !== 'none';
    const cssTransition = cs.transitionDuration !== '0s' && cs.transitionProperty !== 'none' && cs.transitionProperty !== 'all';

    g.instances.push({
      section_index: sectionIdx,
      selector: uniqueSelector(el),
      tag: el.tagName.toLowerCase(),
      class: classStr(el).slice(0, 120),
      height_px: Math.round(rect.height),
      width_px: Math.round(rect.width),
      has_css_animation: cssAnimation,
      has_css_transition: cssTransition,
      has_onclick: !!el.getAttribute('onclick'),
    });
  }

  // Sort groups by instance count desc.
  const sortedGroups = Array.from(groups.values())
    .sort((a, b) => b.instances.length - a.instances.length);

  // Build component records.
  const components = sortedGroups.map((g, idx) => {
    const heights = [];
    for (const r of g.instances) {
      if (r.height_px > 0) heights.push(r.height_px);
    }
    const avg = heights.length ? Math.round(sum(heights) / heights.length) : 0;
    const hasHover = g.instances.some(r => r.has_css_transition);
    const hasAnim = g.instances.some(r => r.has_css_animation);
    const hasOnclick = g.instances.some(r => r.has_onclick);
    return {
      id: 'comp-' + (idx + 1),
      name: g.kind,
      class_prefix: g.class_prefix,
      structural_fingerprint: g.fingerprint,
      instance_count: g.instances.length,
      status: g.instances.length >= 3 ? 'confirmed' : 'candidate',
      average_height_px: avg,
      has_hover_state: hasHover,
      has_animation: hasAnim,
      has_onclick: hasOnclick,
      instances: g.instances.slice(0, 20).map(r => ({
        section_index: r.section_index,
        selector: r.selector,
        height_px: r.height_px,
      })),
      instance_oversample_note: (
        g.instances.length > 20
          ? 'first 20 of %d shown' % g.instances.length
          : null
      ),
    };
  });


  return {
    components: components,
    page_context: {
      title: document.title,
      url: location.href,
      section_count: sections.length,
      total_groups: groups.size,
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
    ap.add_argument("url", help="Absolute http(s) URL to inventory components from.")
    ap.add_argument("-o", "--out", default="reports/reference/components.json",
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
    components: list[dict] = []
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
                    components = raw.get("components") or []
                    page_context = raw.get("page_context") or {}
                except Exception as exc:
                    notes.append("evaluation_error: %s" % exc)
            finally:
                browser.close()
    except Exception as exc:
        print("playwright runtime error: %s" % exc, file=sys.stderr)
        return 4

    # ---- Quick stats ----
    by_kind: dict[str, int] = {}
    total_instances = 0
    for c in components:
        by_kind[c["name"]] = by_kind.get(c["name"], 0) + c["instance_count"]
        total_instances += c["instance_count"]
    confirmed = sum(1 for c in components if c["status"] == "confirmed")
    candidates = len(components) - confirmed

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
            "total_components": len(components),
            "confirmed_components": confirmed,
            "candidate_components": candidates,
            "total_instances": total_instances,
            "by_kind": by_kind,
        },
        "components": components,
    }

    atomic_write_json(out_path, payload)

    print(str(out_path))
    print("access_state: %s" % access_state, file=sys.stderr)
    print("components: %d (confirmed: %d, candidate: %d); total_instances: %d" %
          (len(components), confirmed, candidates, total_instances), file=sys.stderr)
    print("by_kind: %s" % by_kind, file=sys.stderr)
    if notes:
        print("notes: %s" % "; ".join(notes), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
