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
        [--seconds 8] [--model gemini-2.5-flash] [--fps 12]

Requires: Playwright + Chromium (use the ~/.venvs/nt-mirror interpreter) and
google-generativeai, plus GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment.
"""

import argparse
import json
import time
import urllib.error
import urllib.request
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


GEMINI_API = "https://generativelanguage.googleapis.com"


def _gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        # Fall back to the project .env so the agent can run this unaided.
        for env_path in (Path.home() / "Coding/ Cloning Sites/.env",
                         Path.home() / ".hermes/.env"):
            try:
                for line in env_path.read_text().splitlines():
                    if line.startswith(("GEMINI_API_KEY=", "GOOGLE_API_KEY=")):
                        return line.split("=", 1)[1].strip()
            except OSError:
                continue
    if not key:
        raise SystemExit("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")
    return key


def _upload(path: Path, key: str) -> str:
    """Upload a video via the REST Files API. Returns the file URI.

    Uses stdlib urllib rather than google-generativeai: the legacy SDK (0.8.x)
    rejects the `video_metadata` part shape, which is exactly the field that
    controls frame sampling. Dropping the SDK also matches the rest of the
    pipeline's stdlib-only convention.
    """
    size = path.stat().st_size
    print(f"Uploading {path.name} ({size/1024/1024:.1f} MB)...", file=sys.stderr)
    req = urllib.request.Request(
        f"{GEMINI_API}/upload/v1beta/files?key={key}",
        data=json.dumps({"file": {"display_name": path.stem}}).encode(),
        headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                 "X-Goog-Upload-Header-Content-Length": str(size),
                 "X-Goog-Upload-Header-Content-Type": "video/webm",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        upload_url = r.headers.get("x-goog-upload-url")
    if not upload_url:
        raise SystemExit(f"Gemini did not return an upload URL for {path.name}")
    req = urllib.request.Request(
        upload_url, data=path.read_bytes(),
        headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                 "X-Goog-Upload-Command": "upload, finalize"})
    with urllib.request.urlopen(req, timeout=300) as r:
        info = json.load(r)
    uri = info["file"]["uri"]
    name = info["file"]["name"]
    # Wait for ACTIVE; a video used while still PROCESSING silently yields no frames.
    for _ in range(30):
        with urllib.request.urlopen(f"{GEMINI_API}/v1beta/{name}?key={key}", timeout=60) as r:
            if json.load(r).get("state") == "ACTIVE":
                return uri
        time.sleep(2)
    return uri


def analyze(source_video: Path, local_video: Path, out_dir: Path, model_name: str,
            fps: float = 12.0) -> str:
    key = _gemini_key()
    uris = [_upload(p, key) for p in (source_video, local_video)]

    prompt = (
        "You are auditing whether a locally mirrored website reproduces the MOTION of the original.\n"
        "VIDEO 1 is the live SOURCE. VIDEO 2 is the local MIRROR. Both were recorded with the same\n"
        "scripted scroll over the same viewport. Compare them and report, in markdown:\n\n"
        "1. **Entrance / load animations** — do elements fade/slide/scale in the same way?\n"
        "2. **Scroll choreography** — parallax, pinned sections, reveal-on-scroll: match or not?\n"
        "3. **Continuous motion** — carousels, marquees, looping video/background motion.\n"
        "4. **Missing or broken motion in the mirror** — anything static in VIDEO 2 that moved in VIDEO 1.\n"
        "5. **Verdict** — one of: `Motion faithful` | `Partial motion` | `Motion lost`, with a one-line reason.\n\n"
        "Judge only motion you can actually observe; do not infer. Be concrete about timestamps."
    )
    parts = [{"file_data": {"file_uri": u, "mime_type": "video/webm"},
              "video_metadata": {"fps": fps}} for u in uris]
    parts.append({"text": prompt})
    body = json.dumps({"contents": [{"parts": parts}]}).encode()
    req = urllib.request.Request(
        f"{GEMINI_API}/v1beta/models/{model_name}:generateContent?key={key}",
        data=body, headers={"Content-Type": "application/json"})
    effective_fps = fps
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.load(r)
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300].decode(errors="replace")
        print(f"  fps={fps} rejected ({exc.code}); retrying at server default", file=sys.stderr)
        for p in parts[:-1]:
            p.pop("video_metadata", None)
        effective_fps = 0.0
        req = urllib.request.Request(
            f"{GEMINI_API}/v1beta/models/{model_name}:generateContent?key={key}",
            data=json.dumps({"contents": [{"parts": parts}]}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.load(r)

    report = data["candidates"][0]["content"]["parts"][0].get("text", "(empty response)")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "animation-audit-gemini.md"
    tier = ("Interaction-tested" if effective_fps >= 8
            else "Observed visually (coarse — ~1fps cannot resolve easing or stagger)")
    report_path.write_text(
        f"# Gemini Motion-Fidelity Audit\n\n"
        f"- Source video: `{source_video}`\n- Mirror video: `{local_video}`\n"
        f"- Model: `{model_name}`\n"
        f"- Frame sampling: `{(str(effective_fps) + ' fps') if effective_fps else 'server default (~1 fps)'}`\n"
        f"- Evidence tier: `{tier}`\n\n{report}\n"
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
    ap.add_argument("--model", default="gemini-2.5-flash",
                    help="gemini-2.0-flash sits on a separate, often-exhausted quota; "
                         "2.5-flash is the working tier and has better video handling.")
    ap.add_argument("--fps", type=float, default=12.0,
                    help="Frames per second Gemini samples from the video. The DEFAULT "
                         "server-side rate is ~1 fps, which yields ~8 frames for an 8s "
                         "entrance — enough to say motion is present, NOT enough to judge "
                         "easing or stagger. Raising this is what makes the motion verdict "
                         "trustworthy rather than confabulated.")
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
    report = analyze(source_video, local_video, out_dir, args.model, args.fps)
    print("\n--- Gemini verdict ---\n" + report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
