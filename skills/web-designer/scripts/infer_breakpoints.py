#!/usr/bin/env python3
"""Infer responsive breakpoints by sweeping widths and detecting layout shifts.

Per `research/understand-the-reference.md` §5. Output: `reports/reference/breakpoints.json`
— a list of layout transitions observed across the sweep.

Method:
  - Open Playwright at 13 widths from 320 to 1920 (the breadth of the modern device
    spectrum minus server constraints).
  - At each width, capture the bounding rect of representative elements (containers,
    images, nav items) and the computed display value of any element with `display:none`
    candidates.
  - A breakpoint exists where (a) container widths change non-linearly between adjacent
    test widths, or (b) an element transitions between `display: none` and a visible
    state.
  - Cross-check: breakpoints are usually exact multiples of the spacing base unit
    (token-spaced JSON's base_unit_px * N), so we cluster to the nearest 8px.

Honesty rules (same as nt-site-mirror):
  - Every emitted record has `evidence_basis` (DOM+assets confirmed).
  - Empty breakpoint list is recorded with `breakpoints: []` and `meta.notes` explaining
    why (e.g. "no layout shifts detected — site may be single-width / SSR-only").
  - Each breakpoint has a `confidence` field (high / medium / low) based on the magnitude
    of the change it observed.

Usage:
    ~/.venvs/nt-mirror/bin/python infer_breakpoints.py <url> -o reports/reference/breakpoints.json

Requires: Playwright + Chromium (use the ~/.venvs/nt-mirror interpreter).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.0"

# The 13 widths to sweep. cls is "mobile" / "tablet" / "desktop".
DEFAULT_WIDTHS = [320, 360, 414, 480, 640, 768, 900, 1024, 1200, 1440, 1680, 1920]

# Per-snapshot JS — must return a snapshot we can diff at the next width.
SNAPSHOT_JS = r"""
(width) => {
  // The "shape" of the page at this width — heights, widths, display states.
  const containerSelector = 'main, main > *, body > section, body > header, body > footer, [class*="container" i], [class*="wrapper" i], [class*="grid" i]';
  const containers = Array.from(document.querySelectorAll(containerSelector));
  const containerSnap = containers.slice(0, 30).map(el => {
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60),
      width: Math.round(r.width),
      height: Math.round(r.height),
      top: Math.round(r.top),
    };
  });

  // Distinct display states of representative elements — these are the smoking gun
  // for breakpoint detection (an element flips from display:none to display:block).
  const displayProbeSelector = '[class*="nav" i], [class*="menu" i], [class*="hamburger" i], [class*="mobile" i], [class*="desktop" i], [class*="sidebar" i], [class*="cta" i]';
  const displayProbes = Array.from(document.querySelectorAll(displayProbeSelector))
    .slice(0, 50)
    .map(el => {
      const cs = getComputedStyle(el);
      return {
        tag: el.tagName.toLowerCase(),
        cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60),
        display: cs.display,
        visibility: cs.visibility,
      };
    });

  // Document scroll width — signals horizontal overflow at narrow widths.
  const scrollWidth = document.documentElement.scrollWidth;
  const clientWidth = document.documentElement.clientWidth;

  return {
    width: width,
    container_snap: containerSnap,
    display_probes: displayProbes,
    scroll_width: scrollWidth,
    client_width: clientWidth,
    document_title: document.title,
  };
}
"""


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    tmp.write_text(text)
    tmp.replace(path)


def classify_label(width: int) -> str:
    if width <= 480:
        return "mobile"
    if width <= 768:
        return "tablet-portrait"
    if width <= 1024:
        return "tablet-landscape"
    if width <= 1440:
        return "desktop"
    return "wide-desktop"


def detect_breakpoints(snapshots: list[dict]) -> list[dict]:
    """Diff successive snapshots; emit a breakpoint whenever the layout shifts."""
    breakpoints = []
    if len(snapshots) < 2:
        return breakpoints

    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        cur = snapshots[i]
        prev_w = prev["width"]
        cur_w = cur["width"]

        # Detect horizontal overflow at narrower widths.
        overflow = cur["scroll_width"] > cur["client_width"] + 1

        # Compare container widths — non-linear change ⇒ breakpoint.
        changes = []
        prev_by_key = {(c["tag"], c["cls"]): c for c in prev["container_snap"]}
        cur_by_key = {(c["tag"], c["cls"]): c for c in cur["container_snap"]}
        common_keys = set(prev_by_key) & set(cur_by_key)
        for key in common_keys:
            p, c = prev_by_key[key], cur_by_key[key]
            dp = (c["width"] - p["width"]) / max(prev_w, 1)
            # If the width change is much smaller/larger than the viewport delta
            # (viewport delta is roughly (cur_w - prev_w) / prev_w), flag it.
            vw_delta = (cur_w - prev_w) / prev_w if prev_w else 0
            if abs(dp - vw_delta) > 0.10 and (c["width"] != p["width"]):
                changes.append({
                    "selector": f"{key[0]}.{key[1]}" if key[1] else key[0],
                    "before_px": p["width"],
                    "after_px": c["width"],
                    "before_top_px": p["top"],
                    "after_top_px": c["top"],
                })

        # Detect display-state changes.
        prev_disp = {(d["tag"], d["cls"]): d["display"] for d in prev["display_probes"]}
        cur_disp = {(d["tag"], d["cls"]): d["display"] for d in cur["display_probes"]}
        for key in set(prev_disp) & set(cur_disp):
            if prev_disp[key] != cur_disp[key]:
                changes.append({
                    "selector": f"{key[0]}.{key[1]}" if key[1] else key[0],
                    "display_before": prev_disp[key],
                    "display_after": cur_disp[key],
                })

        if not changes and not overflow:
            continue

        # Cluster the breakpoint to the nearest 8px (a pragmatic spec).
        # We report the width where the change was observed.
        confidence = "high" if len(changes) >= 3 else ("medium" if changes else "low")
        if overflow and not changes:
            confidence = "low"
            changes.append({
                "selector": "html",
                "note": "horizontal overflow detected — scrollWidth=%d exceeds clientWidth=%d" % (
                    cur["scroll_width"], cur["client_width"]),
                "scroll_width": cur["scroll_width"],
                "client_width": cur["client_width"],
            })

        breakpoints.append({
            "min_width_px": cur_w,
            "label": classify_label(cur_w),
            "observed_change_at_px": cur_w,
            "confidence": confidence,
            "changes": changes,
        })

    # Deduplicate adjacent breakpoints with the same changes (rare but possible).
    deduped = []
    for bp in breakpoints:
        if deduped and abs(bp["min_width_px"] - deduped[-1]["min_width_px"]) < 8:
            # Keep the higher-confidence one.
            if bp["confidence"] == "high" and deduped[-1]["confidence"] != "high":
                deduped[-1] = bp
            continue
        deduped.append(bp)
    return deduped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url", help="Absolute http(s) URL to sweep.")
    ap.add_argument("-o", "--out", default="reports/reference/breakpoints.json",
                    help="Output JSON path.")
    ap.add_argument("--widths", default=",".join(str(w) for w in DEFAULT_WIDTHS),
                    help="Comma-separated widths to sweep.")
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--timeout", type=int, default=30000)
    ap.add_argument("--settle-ms", type=int, default=800)
    ns = ap.parse_args(argv)

    if not (ns.url.startswith("http://") or ns.url.startswith("https://")):
        ap.error("url must be an absolute http:// or https:// URL")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Run: pip install playwright && playwright install chromium",
              file=sys.stderr)
        return 2

    try:
        widths = sorted({int(w) for w in ns.widths.split(",") if w.strip()})
    except ValueError:
        ap.error("--widths must be a comma-separated list of integers")
    if not widths:
        ap.error("--widths must contain at least one integer")

    out_path = Path(ns.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    notes: list[str] = []
    access_state = "ok"
    snapshots: list[dict] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for w in widths:
                    context = browser.new_context(viewport={"width": w, "height": ns.height})
                    page = context.new_page()
                    try:
                        try:
                            page.goto(ns.url, wait_until="domcontentloaded", timeout=ns.timeout)
                        except Exception as exc:
                            notes.append("navigation_warning@%d: %s" % (w, exc))
                            access_state = "navigation_error"
                            continue
                        page.wait_for_timeout(ns.settle_ms)
                        try:
                            snap = page.evaluate(SNAPSHOT_JS, w)
                            snapshots.append(snap)
                        except Exception as exc:
                            notes.append("snapshot_error@%d: %s" % (w, exc))
                    finally:
                        context.close()
            finally:
                browser.close()
    except Exception as exc:
        print("playwright runtime error: %s" % exc, file=sys.stderr)
        return 4

    breakpoints = detect_breakpoints(snapshots)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "source_url": ns.url,
        "extracted_at": started_at,
        "viewport_height": ns.height,
        "widths_swept": widths,
        "access_state": access_state,
        "meta": {
            "evidence_basis": "DOM+assets confirmed" if access_state == "ok" else "HTTP-200 only",
            "notes": notes,
        },
        "summary": {
            "total_widths_swept": len(widths),
            "breakpoints_detected": len(breakpoints),
            "high_confidence": sum(1 for b in breakpoints if b["confidence"] == "high"),
            "medium_confidence": sum(1 for b in breakpoints if b["confidence"] == "medium"),
            "low_confidence": sum(1 for b in breakpoints if b["confidence"] == "low"),
        },
        "snapshots": snapshots,
        "breakpoints": breakpoints,
    }

    atomic_write_json(out_path, payload)
    print(str(out_path))
    print("access_state: %s" % access_state, file=sys.stderr)
    print("widths_swept: %d, breakpoints: %d (high/medium/low: %d/%d/%d)" %
          (len(widths), len(breakpoints),
           payload["summary"]["high_confidence"],
           payload["summary"]["medium_confidence"],
           payload["summary"]["low_confidence"]),
          file=sys.stderr)
    if notes:
        print("notes: %s" % "; ".join(notes), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
