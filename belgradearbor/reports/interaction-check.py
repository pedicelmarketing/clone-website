#!/usr/bin/env python3
"""Behavioral validation of the local mirror.

Answers the questions HTTP 200s cannot: does client-side navigation still work
when the RSC prefetch 404s, does the WebGL scene actually render frames, do the
runtime-injected videos actually play, and does the mobile menu open.

Usage: ~/.venvs/nt-mirror/bin/python reports/interaction-check.py [base_url]
"""
import json
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"
TELEMETRY = ("googletagmanager", "google-analytics", "doubleclick", "facebook",
             "hubspot", "hs-scripts", "hs-banner", "hs-analytics", "gstatic",
             "google.com", "google.fr", "amazonaws")
results = {}


def note(key, value):
    results[key] = value
    print(f"{key}: {json.dumps(value)[:300]}", flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch()

    # --- 1. Client-side navigation despite failed RSC prefetch ---------------
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(f"{BASE}/en", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)

    # The nav lives inside a menu overlay (links carry opacity-0 until opened),
    # on desktop as well as mobile, so open it before clicking.
    menu_opened = False
    for sel in ["button:has-text('Menu')", "header button", "[aria-label*='menu' i]"]:
        b = page.locator(sel).first
        if b.count() > 0:
            try:
                b.click(timeout=5000, force=True)
                page.wait_for_timeout(2000)
                menu_opened = True
                break
            except Exception:
                continue
    note("desktop_menu_opened", menu_opened)

    link = page.locator('a[href="/en/residences"]').first
    nav_ok, nav_url, nav_mode = False, None, None
    nav_title = nav_h_count = None
    if link.count() > 0:
        before = page.evaluate("() => performance.getEntriesByType('navigation').length")
        try:
            link.click(timeout=10000, force=True)
        except Exception as exc:
            results["nav_click_error"] = str(exc)[:150]
        page.wait_for_timeout(5000)
        nav_url = page.url
        nav_ok = nav_url.rstrip("/").endswith("/en/residences")
        after = page.evaluate("() => performance.getEntriesByType('navigation').length")
        # a fresh navigation entry means the router fell back to a full page load
        nav_mode = "full_page_reload" if after > before else "client_side_soft_nav"
        # confirm the destination actually rendered content, not an error page
        if nav_ok:
            nav_title = page.title()
            nav_h_count = page.locator("h1, h2").count()
    note("nav_click_reached_target", nav_ok)
    note("nav_url", nav_url)
    note("nav_mode", nav_mode)
    note("nav_dest_title", nav_title)
    note("nav_dest_heading_count", nav_h_count)
    note("home_console_errors_non_telemetry",
         [e for e in errors if not any(t in e for t in TELEMETRY) and "_rsc=" not in e][:10])
    note("home_rsc_prefetch_errors", sum(1 for e in errors if "_rsc=" in e))

    # --- 2. Videos actually playing on /en -----------------------------------
    page.goto(f"{BASE}/en", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(12):
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(500)
    vid = page.evaluate("""() => [...document.querySelectorAll('video')].map(v => ({
        src: (v.currentSrc || v.src || '').split('/').pop(),
        readyState: v.readyState, currentTime: +v.currentTime.toFixed(2),
        paused: v.paused, w: v.videoWidth, h: v.videoHeight}))""")
    note("videos_total", len(vid))
    note("videos_with_source", sum(1 for v in vid if v["src"]))
    note("videos_advancing", sum(1 for v in vid if v["currentTime"] > 0))
    note("videos_decoded_dimensions", sum(1 for v in vid if v["w"] > 0))
    note("videos_detail", vid)

    # --- 3. WebGL scene on /en/3d -------------------------------------------
    page3 = browser.new_page(viewport={"width": 1440, "height": 900})
    gl_errors = []
    page3.on("console", lambda m: gl_errors.append(m.text) if m.type == "error" else None)
    failed = []
    page3.on("requestfailed", lambda r: failed.append(r.url))
    page3.goto(f"{BASE}/en/3d", wait_until="domcontentloaded", timeout=90000)
    page3.wait_for_timeout(25000)  # generous: 63 MB of Draco GLB to fetch + decode
    gl = page3.evaluate("""() => {
        const c = document.querySelector('canvas');
        if (!c) return {canvas: false};
        const ctx = c.getContext('webgl2') || c.getContext('webgl');
        return {canvas: true, w: c.width, h: c.height,
                context: !!ctx,
                renderer: ctx ? (() => { const d = ctx.getExtension('WEBGL_debug_renderer_info');
                    return d ? ctx.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'masked'; })() : null,
                drawingBufferWidth: ctx ? ctx.drawingBufferWidth : 0};
    }""")
    note("webgl", gl)
    # non-blank check: sample the canvas for colour variance
    px = page3.evaluate("""() => {
        const c = document.querySelector('canvas');
        if (!c) return null;
        const o = document.createElement('canvas'); o.width = 60; o.height = 40;
        const x = o.getContext('2d');
        try { x.drawImage(c, 0, 0, 60, 40); } catch (e) { return {error: String(e)}; }
        const d = x.getImageData(0, 0, 60, 40).data;
        const s = new Set();
        for (let i = 0; i < d.length; i += 4) s.add(`${d[i]},${d[i+1]},${d[i+2]}`);
        return {distinct_colours: s.size};
    }""")
    note("webgl_canvas_pixels", px)
    note("3d_local_404s", sorted({u.replace(BASE, "") for u in failed
                                 if u.startswith(BASE) and "_rsc=" not in u}))
    note("3d_external_failed", sorted({u for u in failed if not u.startswith(BASE)})[:10])
    note("3d_console_errors_non_telemetry",
         [e for e in gl_errors if not any(t in e for t in TELEMETRY)][:10])

    # --- 4. Mobile menu ------------------------------------------------------
    pm = browser.new_page(viewport={"width": 390, "height": 844})
    pm.goto(f"{BASE}/en", wait_until="domcontentloaded", timeout=60000)
    pm.wait_for_timeout(3000)
    before_links = pm.locator("nav a:visible").count()
    opened = False
    for sel in ["button:has-text('Menu')", "header button", "[aria-label*='menu' i]"]:
        b = pm.locator(sel).first
        if b.count() > 0:
            try:
                # force: the header has overlapping decorative layers that
                # intercept pointer events under Playwright's actionability check
                b.click(timeout=5000, force=True)
                pm.wait_for_timeout(1500)
                opened = True
                break
            except Exception as exc:
                results.setdefault("mobile_menu_click_errors", []).append(
                    f"{sel}: {str(exc)[:120]}")
                continue
    note("mobile_menu_button_clicked", opened)
    note("mobile_nav_links_before", before_links)
    note("mobile_nav_links_after", pm.locator("nav a:visible").count())

    browser.close()

json.dump(results, open("reports/interaction-results.json", "w"), indent=1)
print("\nwrote reports/interaction-results.json")
