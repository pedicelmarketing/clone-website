#!/usr/bin/env python3
"""Motion-fidelity audit: record source vs. local mirror, compare with Gemini video vision.

Screenshots cannot see motion. This helper records a short screen video of the live source and
the local mirror (same scripted scroll/hover), uploads BOTH to Google Gemini's multimodal video
model, and asks it to judge whether the mirror reproduces the source's transitions, scroll
choreography, entrance animations, and hover states — filling the animation-audit step that the
nt-site-mirror skill otherwise leaves to human observation.

Use only when the mirror actually renders and the source has meaningful motion. Gemini reasons
about temporal motion natively (unlike frame-only image vision), so it is the right backend here.

Usage:
    python3 motion_audit.py --source-url https://example.com \
        --local-url http://127.0.0.1:8000 --out reports/motion [--viewport 1440x900] \
        [--seconds 8] [--model gemini-2.0-flash]

Requires: Playwright + Chromium (use the ~/.venvs/nt-mirror interpreter) and
google-generativeai, plus GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment.
"""

import argparse
import os
import sys
import time
from pathlib import Path


def record(url: str, out_dir: Path, label: str, width: int, height: int, seconds: float) -> Path:
    """Record a scripted scroll pass over `url` to a webm and return its path."""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(out_dir),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as exc:  # noqa: BLE001 - record what we can, report the rest
            print(f"  [{label}] navigation warning: {exc}", file=sys.stderr)
        page.wait_for_timeout(1500)  # let entrance animations play
        # Scripted scroll so both captures exercise the same choreography.
        steps = 10
        try:
            total = page.evaluate("document.body.scrollHeight") or (height * 3)
        except Exception:  # noqa: BLE001
            total = height * 3
        per_step_ms = max(200, int((seconds * 1000) / steps))
        for i in range(1, steps + 1):
            page.evaluate("(y) => window.scrollTo({top: y, behavior: 'smooth'})", int(total * i / steps))
            page.wait_for_timeout(per_step_ms)
        page.wait_for_timeout(500)
        video = page.video
        context.close()  # finalizes the video file
        browser.close()
        src = Path(video.path())
        dest = out_dir / f"{label}.webm"
        src.replace(dest)
        return dest


def analyze(source_video: Path, local_video: Path, out_dir: Path, model_name: str) -> str:
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")
    genai.configure(api_key=api_key)

    uploaded = []
    for path in (source_video, local_video):
        print(f"Uploading {path.name} ({path.stat().st_size/1024/1024:.1f} MB)...", file=sys.stderr)
        f = genai.upload_file(path=str(path))
        while f.state.name == "PROCESSING":
            time.sleep(2)
            f = genai.get_file(f.name)
        if f.state.name == "FAILED":
            raise SystemExit(f"Gemini failed to process {path.name}")
        uploaded.append(f)

    prompt = (
        "You are auditing whether a locally mirrored website reproduces the MOTION of the original.\n"
        "VIDEO 1 is the live SOURCE. VIDEO 2 is the local MIRROR. Both were recorded with the same\n"
        "scripted scroll over the same viewport. Compare them and report, in markdown:\n\n"
        "1. **Entrance / load animations** — do elements fade/slide/scale in the same way? \n"
        "2. **Scroll choreography** — parallax, pinned sections, reveal-on-scroll: match or not?\n"
        "3. **Continuous motion** — carousels, marquees, looping video/background motion.\n"
        "4. **Missing or broken motion in the mirror** — anything static in VIDEO 2 that moved in VIDEO 1.\n"
        "5. **Verdict** — one of: `Motion faithful` | `Partial motion` | `Motion lost`, with a one-line reason.\n\n"
        "Judge only motion you can actually observe; do not infer. Be concrete about timestamps."
    )
    gm = genai.GenerativeModel(model_name)
    resp = gm.generate_content([uploaded[0], uploaded[1], prompt])
    report = resp.text or "(empty response)"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "animation-audit-gemini.md"
    report_path.write_text(
        f"# Gemini Motion-Fidelity Audit\n\n"
        f"- Source video: `{source_video}`\n- Mirror video: `{local_video}`\n- Model: `{model_name}`\n\n"
        f"{report}\n"
    )
    print(str(report_path))
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare source vs mirror motion with Gemini video vision.")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--local-url", required=True)
    ap.add_argument("--out", default="reports/motion")
    ap.add_argument("--viewport", default="1440x900", help="WxH")
    ap.add_argument("--seconds", type=float, default=8.0, help="approx scroll duration per capture")
    ap.add_argument("--model", default="gemini-2.0-flash")
    ap.add_argument("--record-only", action="store_true", help="record videos but skip Gemini analysis")
    args = ap.parse_args()

    width, height = (int(x) for x in args.viewport.lower().split("x", 1))
    out_dir = Path(args.out)
    print("Recording source...", file=sys.stderr)
    source_video = record(args.source_url, out_dir, "source", width, height, args.seconds)
    print("Recording mirror...", file=sys.stderr)
    local_video = record(args.local_url, out_dir, "mirror", width, height, args.seconds)
    print(f"videos: {source_video} | {local_video}", file=sys.stderr)

    if args.record_only:
        print(str(out_dir))
        return 0
    report = analyze(source_video, local_video, out_dir, args.model)
    print("\n--- Gemini verdict ---\n" + report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
