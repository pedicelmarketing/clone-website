#!/usr/bin/env python3
"""Focused behavioral check of the /en/3d WebGL scene.

Reading canvas pixels via drawImage is unreliable for three.js because the
default preserveDrawingBuffer:false clears the drawing buffer after compositing.
This instead screenshots the canvas element (Playwright captures the composited
frame) and measures colour variance from the PNG, and records real failure
reasons rather than treating every requestfailed event as a 404.

Usage: ~/.venvs/nt-mirror/bin/python reports/webgl-check.py [base_url]
"""
import collections
import json
import struct
import sys
import zlib

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"
out = {}


def png_colour_stats(path):
    """Decode a PNG well enough to count distinct pixel colours."""
    data = open(path, "rb").read()
    pos, w, h, bitd, colt, idat = 8, 0, 0, 0, 0, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitd, colt = struct.unpack(">IIBB", body[:10])
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if colt not in (2, 6) or bitd != 8:
        return {"error": f"unsupported png colour type {colt}/{bitd}"}
    ch = 3 if colt == 2 else 4
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    colours = collections.Counter()
    p = 0
    for _ in range(h):
        ft = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if ft == 1:
                line[i] = (line[i] + a) & 255
            elif ft == 2:
                line[i] = (line[i] + b) & 255
            elif ft == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif ft == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        for i in range(0, stride, ch):
            colours[bytes(line[i:i + 3])] += 1
        prev = line
    total = sum(colours.values())
    top = colours.most_common(1)[0]
    return {"distinct_colours": len(colours), "pixels": total,
            "dominant_colour": list(top[0]), "dominant_share": round(top[1] / total, 4)}


with sync_playwright() as p:
    browser = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    failures, responses = [], []
    page.on("requestfailed",
            lambda r: failures.append({"url": r.url, "failure": r.failure}))
    page.on("response", lambda r: responses.append((r.url, r.status)))
    page.goto(f"{BASE}/en/3d", wait_until="domcontentloaded", timeout=120000)

    # Poll until the renderer reports drawn geometry, up to 90s.
    drew, waited = None, 0
    while waited < 90000:
        page.wait_for_timeout(5000)
        waited += 5000
        drew = page.evaluate("""() => {
            const c = document.querySelector('canvas');
            if (!c) return null;
            return {has_canvas: true, width: c.width, height: c.height,
                    engine: c.getAttribute('data-engine'),
                    css_w: c.clientWidth, css_h: c.clientHeight};
        }""")
        # Element screenshots time out on this large software-rendered canvas;
        # a viewport screenshot captures the composited frame just as well.
        shot = "reports/viewports-local/_webgl-probe.png"
        page.screenshot(path=shot, timeout=120000)
        stats = png_colour_stats(shot)
        if stats.get("distinct_colours", 0) > 200:
            break
    out["canvas"] = drew
    out["canvas_screenshot_stats"] = stats
    out["waited_ms"] = waited

    glb = [(u.replace(BASE, ""), s) for u, s in responses if ".glb" in u]
    out["glb_responses"] = sorted(set(glb))
    out["glb_200_count"] = sum(1 for _, s in glb if s == 200)
    out["real_failures"] = [f for f in failures if BASE in f["url"]]
    out["external_failures_sample"] = sorted(
        {f["url"].split("?")[0] for f in failures if BASE not in f["url"]})[:12]
    # was the external draco decoder + hdr actually fetched?
    out["external_ok"] = sorted({u.split("?")[0] for u, s in responses
                                 if BASE not in u and s == 200
                                 and any(k in u for k in ("draco", "githack", "githubusercontent"))})

    page.screenshot(path="reports/viewports-local/_3d-fullpage.png",
                    full_page=False, timeout=120000)
    browser.close()

print(json.dumps(out, indent=1))
json.dump(out, open("reports/webgl-results.json", "w"), indent=1)
