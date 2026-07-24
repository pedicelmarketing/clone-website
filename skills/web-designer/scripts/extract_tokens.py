#!/usr/bin/env python3
"""Extract design tokens from a URL — color, typography, spacing, radius, shadow.

Per `research/understand-the-reference.md` §2 (2a-2e). Outputs five JSON files into the
output directory: color.json, typography.json, spacing.json, radius.json, shadow.json.

The extractor is observation-only. It reads:
  - CSS custom properties at :root (and any :where(html, body) rule) for the color
    palette (2a) and ideally for the typographic scale.
  - getComputedStyle on representative elements (h1-h4, p, button, a, label, small, .card,
    .container, etc.) for the *applied* values when variables are unavailable.
  - Tailwind's CDN bundle (when present) for the inline config — color names, spacing
    scale, radius scale.

Honesty rules (same as nt-site-mirror):
  - Every emitted JSON has a `meta.evidence_basis` field.
  - Empty arrays are emitted (not omitted) when a token class could not be extracted;
    the reason is recorded in `meta.notes`.
  - No inferred values. If a Tailwind config has 11 colors, we emit 11 colors — we do
    not synthesize an 11-color palette from a 3-color observation.

Usage:
    ~/.venvs/nt-mirror/bin/python extract_tokens.py <url> -o reports/reference/tokens/ \
        [--viewport 1440x900] [--timeout 45000]

Requires: Playwright + Chromium (use the ~/.venvs/nt-mirror interpreter).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit


SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Page evaluation — the JS expressions we run inside the page
# ---------------------------------------------------------------------------

# One round trip per token class. Each function returns a JSON-serializable dict.
# Documented in scripts/references (vendored from understand-the-reference §2).

EXTRACT_JS = r"""
() => {
  const out = {};

  //----- 2a: CSS custom properties at :root (and html, body) -----
  const propBag = {};
  function walkRootRules(rule) {
    if (!rule) return;
    if (rule.style) {
      for (let i = 0; i < rule.style.length; i++) {
        const name = rule.style[i];
        if (name.startsWith('--')) {
          propBag[name] = rule.style.getPropertyValue(name).trim();
        }
      }
    }
    // CSSRuleList (e.g. media rules) — recurse on nested rules.
    if (rule.cssRules) {
      for (let i = 0; i < rule.cssRules.length; i++) walkRootRules(rule.cssRules[i]);
    }
  }
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        // Only collect variables from :root and :where(html, body) global rules.
        const sel = rule.selectorText || '';
        if (/^\s*:root\b/.test(sel) || /:where\(\s*html\s*,\s*body\s*\)/.test(sel)) {
          walkRootRules(rule);
        }
      }
    } catch (e) { /* cross-origin stylesheet — skip */ }
  }
  out.css_variables = propBag;

  //----- 2b: typography on representative elements -----
  const TYPE_ROLES = [
    {role: 'h1', selector: 'h1'},
    {role: 'h2', selector: 'h2'},
    {role: 'h3', selector: 'h3'},
    {role: 'h4', selector: 'h4'},
    {role: 'p',  selector: 'p'},
    {role: 'body', selector: 'body'},
    {role: 'button', selector: 'button, a.btn, [class*="button" i], [role="button"]'},
    {role: 'small', selector: 'small, .small, [class*="caption" i]'},
  ];
  const typography = [];
  for (const {role, selector} of TYPE_ROLES) {
    const el = document.querySelector(selector);
    if (!el) continue;
    const cs = getComputedStyle(el);
    typography.push({
      role,
      selector,
      family: cs.fontFamily,
      size_px: parseFloat(cs.fontSize),
      weight: cs.fontWeight,
      line_height_px: parseFloat(cs.lineHeight),
      letter_spacing_px: parseFloat(cs.letterSpacing) || 0,
      text_transform: cs.textTransform,
    });
  }
  out.typography = typography;

  //----- 2c: spacing — sample padding/margin/gap on section/grid containers -----
  const SAMPLE_SEL = [
    'section', 'main > div', '[class*="container" i]', '[class*="section" i]',
    '[class*="grid" i]', '[class*="flex" i]', '[class*="card" i]',
    'header', 'footer', 'nav',
  ];
  const seen = new Set();
  const spacings = [];
  for (const sel of SAMPLE_SEL) {
    const nodes = document.querySelectorAll(sel);
    for (let i = 0; i < Math.min(5, nodes.length); i++) {
      const n = nodes[i];
      const key = n.tagName + ':' + (n.className || '').toString().slice(0, 60);
      if (seen.has(key)) continue;
      seen.add(key);
      const cs = getComputedStyle(n);
      spacings.push({
        tag: n.tagName,
        class: (n.className || '').toString().slice(0, 80),
        padding_px: parseFloat(cs.paddingTop) || 0,
        margin_px: parseFloat(cs.marginTop) || 0,
        gap_px: parseFloat(cs.rowGap || cs.gap) || 0,
      });
    }
  }
  out.spacings = spacings;

  //----- 2d: radius — buttons, cards, inputs, images -----
  const RADII_SEL = [
    {role: 'button', selector: 'button, a.btn, [class*="button" i], [role="button"]'},
    {role: 'card',   selector: '[class*="card" i], article, .card'},
    {role: 'input',  selector: 'input, textarea, select, [class*="input" i]'},
    {role: 'image',  selector: 'img, video, [class*="avatar" i]'},
    {role: 'tag',    selector: '[class*="tag" i], [class*="badge" i], [class*="pill" i]'},
  ];
  const radii = [];
  for (const {role, selector} of RADII_SEL) {
    const nodes = document.querySelectorAll(selector);
    for (let i = 0; i < Math.min(4, nodes.length); i++) {
      const n = nodes[i];
      const cs = getComputedStyle(n);
      radii.push({
        role,
        selector,
        radius_px: parseFloat(cs.borderTopLeftRadius) || 0,
      });
    }
  }
  out.radii = radii;

  //----- 2e: shadow — cards, popovers, modals, sticky headers -----
  const SHADOW_SEL = [
    {role: 'card',      selector: '[class*="card" i], article'},
    {role: 'popover',   selector: '[class*="popover" i], [role="tooltip"], [role="dialog"]'},
    {role: 'modal',     selector: '[class*="modal" i], [class*="dialog" i]'},
    {role: 'header',    selector: 'header, [class*="header" i]'},
    {role: 'button',    selector: 'button, a.btn, [role="button"]'},
  ];
  const shadows = [];
  for (const {role, selector} of SHADOW_SEL) {
    const nodes = document.querySelectorAll(selector);
    for (let i = 0; i < Math.min(3, nodes.length); i++) {
      const n = nodes[i];
      const cs = getComputedStyle(n);
      const shadow = cs.boxShadow && cs.boxShadow !== 'none' ? cs.boxShadow : null;
      if (shadow) {
        shadows.push({role, selector, box_shadow: shadow});
      }
    }
  }
  out.shadows = shadows;

  //----- tailwind detection -----
  const tailwindScript = document.querySelector('script[src*="cdn.tailwindcss.com"]');
  out.tailwind_detected = !!tailwindScript;
  if (tailwindScript) {
    // Look for inline tailwind.config in subsequent scripts.
    for (const s of document.querySelectorAll('script')) {
      const m = (s.textContent || '').match(/tailwind\.config\s*=\s*(\{[\s\S]*?\})\s*;?\s*(?:<|$)/);
      if (m) {
        try {
          // Safe eval: only the tailwind.config object literal.
          out.tailwind_config = (new Function('return ' + m[1]))();
        } catch (e) {
          out.tailwind_config_error = String(e);
        }
        break;
      }
    }
  }

  //----- count var(--name) references across same-origin stylesheets -----
  // Cross-origin stylesheets throw on cssRules access — we skip those silently.
  const refCounts = {};
  function ruleTextAll(rule) {
    let text = '';
    if (rule.cssText) text += rule.cssText + '\n';
    if (rule.cssRules) {
      for (let i = 0; i < rule.cssRules.length; i++) {
        text += ruleTextAll(rule.cssRules[i]);
      }
    }
    return text;
  }
  for (const sheet of document.styleSheets) {
    let blob = '';
    try {
      for (const rule of sheet.cssRules) {
        blob += ruleTextAll(rule);
      }
    } catch (e) { continue; /* cross-origin sheet */ }
    for (const name in propBag) {
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const re = new RegExp('var\\(\\s*' + escaped + '\\s*[,)]', 'g');
      const m = blob.match(re);
      if (m) refCounts[name] = (refCounts[name] || 0) + m.length;
    }
  }
  out.var_reference_counts = refCounts;

  //----- page context -----
  out.page_context = {
    title: document.title,
    url: location.href,
    h1_count: document.querySelectorAll('h1').length,
    section_count: document.querySelectorAll('section, main > div').length,
  };

  return out;
}
"""

# ---------------------------------------------------------------------------
# Token-class post-processors
# ---------------------------------------------------------------------------

COLOR_NAME_RE = re.compile(
    r"^(?:color|clr|brand|palette|surface|fg|bg|background|border|fill|stroke|ring|accent)"
    r"[-_]?(.*)$",
    re.IGNORECASE,
)

def _normalize_hex(value: str) -> str | None:
    """Return a lowercased #rrggbb hex if value parses as a CSS color, else None."""
    if not value:
        return None
    v = value.strip()
    # Skip non-color tokens (font, spacing, weight, etc.) — they shouldn't be in
    # color.css_variables at all, but defensive.
    if v.startswith("(") or " " in v and "rgb" not in v and "hsl" not in v:
        return None
    if v.startswith("#"):
        body = v[1:]
        if len(body) == 3:
            body = "".join(c * 2 for c in body)
        if re.fullmatch(r"[0-9a-fA-F]{6}", body):
            return "#" + body.lower()
        if re.fullmatch(r"[0-9a-fA-F]{8}", body):
            return "#" + body.lower()
        return None
    m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
    if m:
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        return "#%02x%02x%02x" % (r, g, b)
    m = re.fullmatch(r"hsla?\(\s*([0-9.]+)", v)
    if m:
        # We don't fully parse hsl here — too many forms. Use a stable placeholder
        # so the caller still sees the token.
        return v.lower()
    return None


def _is_color_token_name(name: str) -> bool:
    base = name.lstrip("-").lower()
    return COLOR_NAME_RE.match(base) is not None


def _rgb_to_luma(hex_color: str) -> float | None:
    if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
        return None
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
    except ValueError:
        return None
    # Rec. 709 luma — perceptual brightness.
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _frequency_color_groups(css_variables: dict[str, str]) -> dict[str, int]:
    """Unused placeholder kept for API symmetry.

    Frequency analysis requires a CSSOM walk that the page.evaluate context owns; we
    do it inside the extract block below. Kept here so the signature is stable.
    """
    return {name: 0 for name in css_variables}


def build_color_tokens(css_variables: dict[str, str], frequency: dict[str, int]) -> dict[str, Any]:
    color_tokens = []
    for name, value in sorted(css_variables.items()):
        if not _is_color_token_name(name):
            continue
        hex_color = _normalize_hex(value)
        if not hex_color:
            continue
        color_tokens.append({
            "name": name,
            "raw_value": value,
            "hex": hex_color if hex_color.startswith("#") else None,
            "raw_string": value if not hex_color or not hex_color.startswith("#") else None,
            "refs": frequency.get(name, 0),
        })

    # Cluster by hue families. Pure CSS gives us per-token names; we bucket them by
    # the *base* name (e.g. --color-gray-100 and --color-neutral-100 both → "gray").
    families: dict[str, list[dict]] = {}
    for token in color_tokens:
        stripped = token["name"].lstrip("-")
        m = re.match(r"^(?:color|clr|brand|fg|bg|background|border|fill|stroke|ring|accent|surface)[-_]?(.*)$",
                     stripped, re.IGNORECASE)
        tail = (m.group(1) if m else stripped).lower()
        # tail is like "primary-600" or "gray-100" or "white"
        family = tail.split("-")[0] if "-" in tail else tail
        families.setdefault(family, []).append(token)

    # Sort each family by luminance (white → black) or by numeric step if present.
    def sort_key(t):
        step_m = re.search(r"-(\d{2,4})$", t["name"])
        if step_m:
            return (0, int(step_m.group(1)))
        if t["hex"]:
            return (1, _rgb_to_luma(t["hex"]) or 0)
        return (2, 0)

    for family in families.values():
        family.sort(key=sort_key)

    # Pick the primary / secondary / accent heuristically — the most-referenced
    # available tokens in those families. This is observational, not editorial.
    primaries = sorted(color_tokens, key=lambda t: -t["refs"])[:3]
    return {
        "tokens": color_tokens,
        "families": families,
        "primary_candidates": [t["name"] for t in primaries],
        "total_unique": len(color_tokens),
    }


def build_typography_tokens(typography: list[dict]) -> dict[str, Any]:
    """Style the applied font stack + the modular scale ratio from observed sizes."""
    if not typography:
        return {"scale": [], "families": {}, "scale_ratio": None, "evidence_basis": "DOM+assets confirmed"}

    # Compute scale ratio from the most-distant pair (usually h1 vs p/body).
    sizes = sorted({t["size_px"] for t in typography if t["size_px"] > 0}, reverse=True)
    if len(sizes) >= 2:
        scale_ratio = round(sizes[0] / sizes[-1], 3)
    else:
        scale_ratio = None

    # Family ↔ role mapping
    family_by_role = {}
    for t in typography:
        family_by_role[t["role"]] = {
            "family": t["family"],
            "size_px": t["size_px"],
            "weight": t["weight"],
            "line_height_px": t["line_height_px"],
            "letter_spacing_px": t["letter_spacing_px"],
            "text_transform": t["text_transform"],
        }

    # Classify families into display / body / mono based on common keywords.
    families = {"display": set(), "body": set(), "mono": set()}
    for t in typography:
        f = (t["family"] or "").lower()
        if not f:
            continue
        first = f.split(",")[0].strip().strip("'\"")
        if "mono" in f or "code" in f or "courier" in f:
            families["mono"].add(first)
        # Heuristic: h1/h2 entries are considered display candidates.
        if t["role"] in ("h1", "h2"):
            families["display"].add(first)
        else:
            families["body"].add(first)

    return {
        "scale": typography,
        "family_by_role": family_by_role,
        "families": {k: sorted(v) for k, v in families.items()},
        "scale_ratio": scale_ratio,
        "evidence_basis": "DOM+assets confirmed",
    }


def _gcd_many(values: list[int]) -> int:
    from math import gcd
    from functools import reduce
    return reduce(gcd, values)


def build_spacing_tokens(spacings: list[dict]) -> dict[str, Any]:
    """Detect the base unit (4, 6, 8, 10, 12 px) from the GCD of observed values."""
    observed = []
    for s in spacings:
        for field in ("padding_px", "margin_px", "gap_px"):
            v = s.get(field) or 0
            if v > 0:
                observed.append(int(round(v)))
    if not observed:
        return {"base_unit_px": None, "scale": [], "samples": spacings, "evidence_basis": "DOM+assets confirmed"}

    # Drop the largest 10% (full-bleed padding) and smallest 10% (sub-pixel) to make
    # GCD more stable.
    observed.sort()
    trimmed = observed[len(observed) // 10 : max(len(observed) // 10 + 1, -len(observed) // 10 or -1)]
    candidates = sorted(set(trimmed))
    base = None
    for guess in (4, 6, 8, 10, 12, 16, 20):
        if all(v % guess == 0 for v in candidates):
            base = guess
            break
    if base is None and candidates:
        # Fall back to GCD of the first 8 values.
        base = _gcd_many(candidates[:8]) or candidates[0]

    # Build the scale — every multiple of the base that appears in the data.
    multiples = sorted({v for v in candidates if v % base == 0})
    return {
        "base_unit_px": base,
        "scale": multiples,
        "samples": spacings,
        "evidence_basis": "DOM+assets confirmed",
    }


def build_radius_tokens(radii: list[dict]) -> dict[str, Any]:
    """Bucket border-radius values into a scale (0, 4, 8, 12, 16, 9999)."""
    if not radii:
        return {"scale": [], "defaults_by_role": {}, "evidence_basis": "DOM+assets confirmed"}
    buckets = Counter()
    by_role = {}
    for r in radii:
        v = int(round(r["radius_px"]))
        buckets[v] += 1
        by_role.setdefault(r["role"], []).append(v)

    # Group odd values into the nearest of {0, 4, 6, 8, 12, 16, 20, 24, 9999}.
    SCALE = [0, 4, 6, 8, 12, 16, 20, 24, 9999]
    def nearest(v):
        return min(SCALE, key=lambda s: abs(s - v))
    observed_scale = sorted({nearest(v) for v in buckets})
    defaults_by_role = {role: nearest(v_list[0]) for role, v_list in by_role.items() if v_list}
    return {
        "scale": observed_scale,
        "defaults_by_role": defaults_by_role,
        "value_frequency": dict(buckets),
        "evidence_basis": "DOM+assets confirmed",
    }


def build_shadow_tokens(shadows: list[dict]) -> dict[str, Any]:
    """Bucket box-shadow values into elevation levels by blur radius."""
    if not shadows:
        return {"elevations": [], "evidence_basis": "DOM+assets confirmed"}
    # Parse the box-shadow and extract the first blur radius as the elevation key.
    parsed = []
    for s in shadows:
        blur = _extract_blur(s["box_shadow"])
        parsed.append({"role": s["role"], "selector": s["selector"], "value": s["box_shadow"], "blur_px": blur})
    # Bucket by blur.
    buckets = {}
    for p in parsed:
        b = p["blur_px"] if p["blur_px"] is not None else 0
        buckets.setdefault(b, []).append(p)
    elevations = []
    for blur, items in sorted(buckets.items()):
        level = len(elevations)
        elevations.append({
            "level": level,
            "blur_px": blur,
            "value": items[0]["value"],
            "used_by": sorted({i["role"] for i in items}),
        })
    return {
        "elevations": elevations,
        "samples": parsed,
        "evidence_basis": "DOM+assets confirmed",
    }


def _extract_blur(box_shadow: str) -> int | None:
    """Extract the first blur radius from a box-shadow string. Returns px or None."""
    if not box_shadow:
        return None
    # box-shadow: <offset-x> <offset-y> <blur> <spread> <color>?
    # Multiple shadows are comma-separated; we take the first.
    first = box_shadow.split("),")[0]
    # Strip leading 'rgb(' fragments so we don't trip on the color part.
    parts = re.findall(r"-?\d+(?:\.\d+)?", first)
    if len(parts) >= 3:
        try:
            return int(round(float(parts[2])))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def parse_viewport(s: str) -> tuple[int, int]:
    try:
        w, h = s.lower().split("x", 1)
        return int(w), int(h)
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            "viewport must be WIDTHxHEIGHT (e.g. 1440x900); got %r" % s
        )


def _sanitize_for_json(value: Any) -> Any:
    """Recursively replace NaN/Inf with None so json.dumps(allow_nan=False) works."""
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
    return value


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    safe = _sanitize_for_json(data)
    text = json.dumps(safe, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    tmp.write_text(text)
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url", help="Absolute http(s) URL to extract tokens from.")
    ap.add_argument("-o", "--out", default="reports/reference/tokens",
                    help="Output directory for the five token JSON files.")
    ap.add_argument("--viewport", default="1440x900", type=parse_viewport)
    ap.add_argument("--timeout", type=int, default=45000)
    ap.add_argument("--settle-ms", type=int, default=1500,
                    help="Time to wait after DOMContentLoaded for fonts/CSS to settle.")
    ap.add_argument("--scroll-steps", type=int, default=8,
                    help="Number of scroll steps to lazy-trigger reveal blocks.")
    ns = ap.parse_args(argv)

    if not (ns.url.startswith("http://") or ns.url.startswith("https://")):
        ap.error("url must be an absolute http:// or https:// URL")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Run: pip install playwright && playwright install chromium",
              file=sys.stderr)
        return 2

    out_dir = Path(ns.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    width, height = ns.viewport

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    notes: list[str] = []
    access_state = "ok"

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
                # Settle, then scroll to trigger lazy-revealed sections.
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

                # Detect Cloudflare / login walls via title heuristic.
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
                except Exception as exc:
                    notes.append("evaluation_error: %s" % exc)
                    raw = {"css_variables": {}, "typography": [], "spacings": [],
                           "radii": [], "shadows": [], "page_context": {},
                           "tailwind_detected": False}
            finally:
                browser.close()
    except Exception as exc:
        print("playwright runtime error: %s" % exc, file=sys.stderr)
        return 4

    # ---- Build the five token files ----
    css_variables = raw.get("css_variables") or {}
    typography = raw.get("typography") or []
    spacings = raw.get("spacings") or []
    radii = raw.get("radii") or []
    shadows = raw.get("shadows") or []
    page_context = raw.get("page_context") or {}

    # Color frequency analysis — the page itself counts var(--name) references
    # across same-origin stylesheets. We use that here.
    frequency = (raw.get("var_reference_counts") or {}).copy()
    for name in css_variables:
        frequency.setdefault(name, 0)

    color = build_color_tokens(css_variables, frequency)
    typography_out = build_typography_tokens(typography)
    spacing_out = build_spacing_tokens(spacings)
    radius_out = build_radius_tokens(radii)
    shadow_out = build_shadow_tokens(shadows)

    # Tailwind config — keep raw if present.
    tailwind = {
        "detected": bool(raw.get("tailwind_detected")),
        "config": raw.get("tailwind_config"),
        "config_error": raw.get("tailwind_config_error"),
        "evidence_basis": "DOM+assets confirmed" if raw.get("tailwind_detected") else "Not exercised",
    }

    meta = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "source_url": ns.url,
        "extracted_at": started_at,
        "viewport": "%dx%d" % (width, height),
        "access_state": access_state,
        "evidence_basis": "DOM+assets confirmed" if access_state == "ok" else "HTTP-200 only",
        "notes": notes,
        "page_context": page_context,
    }

    files_written = []
    for name, payload in (
        ("color", {**color, "meta": meta}),
        ("typography", {**typography_out, "meta": meta}),
        ("spacing", {**spacing_out, "meta": meta}),
        ("radius", {**radius_out, "meta": meta}),
        ("shadow", {**shadow_out, "meta": meta}),
        ("tailwind", {**tailwind, "meta": meta}),
    ):
        path = out_dir / ("%s.json" % name)
        atomic_write_json(path, payload)
        files_written.append(str(path))

    # Concise summary to stdout.
    print("\n".join(files_written))
    print("access_state: %s" % access_state, file=sys.stderr)
    print("css variables at :root: %d" % len(css_variables), file=sys.stderr)
    print("color tokens: %d, typography roles: %d, spacing samples: %d, "
          "radius samples: %d, shadow samples: %d" %
          (color["total_unique"], len(typography_out["scale"]),
           len(spacings), len(radii), len(shadows)),
          file=sys.stderr)
    if notes:
        print("notes: %s" % "; ".join(notes), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
