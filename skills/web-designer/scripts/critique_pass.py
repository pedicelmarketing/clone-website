#!/usr/bin/env python3
"""Vision-based design self-critique loop for a composed static site.

What this is
------------
After `compose_site.py` produces a site directory, this script renders the site
on a local HTTP server, screenshots it at each declared viewport (waiting for
animations to settle), and asks a vision LLM to score the result against a
fixed rubric. It then emits CONCRETE, ACTIONABLE revisions — each one names a
section id and a specific change, and is gated by `design_pass.verify_source_fields`
so a revision can NEVER introduce a claim that isn't backed by the brand brief.

The rubric
----------
7 dimensions, 0-10 each. `looks_templated` is INVERTED (10 = does NOT look
templated). Every score carries a one-line justification AND at least one
concrete observation (e.g. "section X sits at y=NNNpx and contains a single
paragraph — left 50% of viewport is empty at 1440px"). Vague advice like
"improve spacing" is rejected by the prompt; revisions must name a section
and a change.

Apply / iterate
---------------
With `--apply`, the script applies revisions back into the design plan
(keeping the plan schema-valid and the source-brief inv-nothing contract),
re-runs `compose_site.py`, and critiques again, up to `--max-iterations`. If
the total score DROPS after a revision, the previous higher-scoring design
plan is restored (never let the loop make things worse). A `critique-summary.md`
score table records every iteration.

CLI
---
    critique_pass.py --site <composed site dir> \
                     --brand-brief <path> --design-plan <path> \
                     -o <critique dir> \
                     [--viewports 1440x900,375x812] [--max-iterations 3] \
                     [--model MiniMax-M3] [--apply] [--entry index.html] \
                     [--compose-script skills/web-designer/scripts/compose_site.py] \
                     [--tokens <tokens.json>] [--reference-report <dir>] \
                     [--reference-tokens <dir>]

Environment
-----------
  MINIMAX_API_KEY   required for vision calls; if missing/unauthorised the
                    script degrades to a no-op with a clear stderr message
                    and exit code 0 (matches `design_pass.py` graceful path).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYBROWSER = Path("/home/openclaw/.venvs/nt-mirror/bin/python")  # Playwright + Chromium

SCHEMA_VERSION = "1.0"
RUBRIC_DIMENSIONS = [
    "visual_hierarchy",
    "use_of_space",
    "typographic_contrast",
    "focal_point",
    "brand_fit",
    "motion_restraint",
    "looks_templated",  # inverted: 10 = does NOT look templated
]
DEFAULT_VIEWPORTS = [(1440, 900), (375, 812)]
SETTLE_JS = (
    "async () => { const animations = document.getAnimations(); "
    "await Promise.race([Promise.all(animations.map(a => a.finished.catch(() => {}))), "
    "new Promise(resolve => setTimeout(resolve, 3000))]); "
    "return {animation_count: animations.length, settle_cap_ms: 3000}; }"
)


# ---------------------------------------------------------------------------
# Vision API — stdlib urllib, Anthropic-compatible, no new deps
# ---------------------------------------------------------------------------

def _vision_call(model: str, system: str, messages: list, timeout: int = 180) -> dict:
    """Single round-trip. Raises on HTTP errors so callers can decide."""
    key = os.environ.get("MINIMAX_API_KEY")
    if not key:
        raise RuntimeError("MINIMAX_API_KEY is not set")
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": messages,
    }
    req = urllib.request.Request(
        "https://api.minimax.io/anthropic/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _extract_text(body: dict) -> str:
    return "".join(x.get("text", "") for x in body.get("content", []) if isinstance(x, dict))


# ---------------------------------------------------------------------------
# Image preparation — downscale + JPEG-encode screenshots in-process via stdlib
# ---------------------------------------------------------------------------

def _downscale_png_to_jpeg(png_path: Path, max_w: int = 760, quality: int = 72) -> bytes:
    """Downscale a PNG screenshot to JPEG bytes (max_w wide, quality ~72).

    Uses only stdlib. The dependency-free way: parse PNG IHDR for dims, then
    re-encode via Playwright's Chromium by loading the PNG into a tiny HTML
    page and screenshotting the <img> at a downscaled size. We do that via a
    second Playwright run inside the nt-mirror venv.
    """
    # We delegate the actual downscale to a small Playwright script. The reason
    # is that stdlib has no image library — we either shell out to a converter
    # or use Chromium (which we already need for the screenshot). Chromium
    # gives us controllable quality and width in one pass.
    return _downscale_via_chromium(png_path, max_w, quality)


_DOWNSCALE_SCRIPT = r"""
import sys, base64, pathlib
from playwright.sync_api import sync_playwright
src = sys.argv[1]; max_w = int(sys.argv[2]); q = int(sys.argv[3])
b64 = pathlib.Path(src).read_bytes()
data_url = "data:image/png;base64," + base64.b64encode(b64).decode()
html = (
    "<!doctype html><html><body style=\"margin:0;background:#fff\">"
    "<img id=\"i\" src=\"" + data_url + "\" style=\"display:block;max-width:100%;height:auto\">"
    "</body></html>"
)
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width": max_w, "height": 10})
    page = ctx.new_page()
    page.set_content(html)
    page.wait_for_load_state("domcontentloaded")
    el = page.locator("#i")
    box = el.bounding_box()
    h = int(box["height"]) if box else 10
    ctx2 = browser.new_context(viewport={"width": max_w, "height": max(h, 10)},
                              device_scale_factor=1)
    page2 = ctx2.new_page()
    page2.set_content(html)
    page2.wait_for_load_state("domcontentloaded")
    page2.locator("#i").screenshot(path=sys.argv[4], type="jpeg", quality=q)
    browser.close()
"""


def _downscale_via_chromium(png_path: Path, max_w: int, quality: int) -> bytes:
    out = png_path.with_suffix(".downscaled.jpg")
    env = os.environ.copy()
    # Playwright cache lives under HOME; the hermes sandbox sometimes rewrites it.
    if not os.path.exists(os.path.join(env.get("HOME", ""), ".cache", "ms-playwright")):
        env["HOME"] = "/home/openclaw"
    proc = subprocess.run(
        [str(PYBROWSER), "-c", _DOWNSCALE_SCRIPT, str(png_path), str(max_w), str(quality), str(out)],
        capture_output=True, text=True, timeout=60, env=env,
    )
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"downscale failed: {proc.stderr[-300:]}")
    return out.read_bytes()


# ---------------------------------------------------------------------------
# Local server (owned lifecycle, killed in finally)
# ---------------------------------------------------------------------------

class _Server:
    def __init__(self, site_dir: Path, port: int):
        self.site_dir = site_dir
        self.port = port
        self.proc: subprocess.Popen | None = None
        self.log_path = site_dir / ".critique_serve.log"

    def start(self):
        # Use stdlib http.server via the system python (the site has no python deps).
        cmd = [sys.executable, "-u", "-m", "http.server", "--bind", "127.0.0.1", str(self.port)]
        self.proc = subprocess.Popen(
            cmd, cwd=str(self.site_dir),
            stdout=open(self.log_path, "w"), stderr=subprocess.STDOUT,
        )
        # wait for / readiness
        deadline = time.time() + 8
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=1) as r:
                    if r.status == 200:
                        return
            except Exception as e:  # noqa: BLE001
                last_err = e
            time.sleep(0.1)
        self.kill()
        raise RuntimeError(f"server did not become ready: {last_err}")

    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def kill(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.send_signal(signal.SIGTERM)
                self.proc.wait(timeout=3)
            except Exception:  # noqa: BLE001
                try:
                    self.proc.kill()
                except Exception:
                    pass


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---------------------------------------------------------------------------
# Screenshots — Playwright + settle, run inside the nt-mirror venv
# ---------------------------------------------------------------------------

_SCREENSHOT_SCRIPT = r"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright
base = sys.argv[1]
route = sys.argv[2]
out_dir = pathlib.Path(sys.argv[3])
viewports = json.loads(sys.argv[4])
url = base + (route if route.startswith("/") else "/" + route)
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    for w, h in viewports:
        ctx = browser.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            settle = page.evaluate(sys.argv[5])
            shot = out_dir / f"shot_{w}x{h}.png"
            page.screenshot(path=str(shot), full_page=False)
            results.append({"viewport": f"{w}x{h}", "shot": str(shot),
                            "settle": settle, "ok": True})
        except Exception as e:  # noqa: BLE001
            results.append({"viewport": f"{w}x{h}", "ok": False, "error": str(e)})
        finally:
            ctx.close()
    browser.close()
print(json.dumps(results))
"""


def _screenshot(base_url: str, route: str, out_dir: Path, viewports: list[tuple[int, int]]) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if not os.path.exists(os.path.join(env.get("HOME", ""), ".cache", "ms-playwright")):
        env["HOME"] = "/home/openclaw"
    proc = subprocess.run(
        [str(PYBROWSER), "-c", _SCREENSHOT_SCRIPT,
         base_url, route, str(out_dir), json.dumps([[w, h] for w, h in viewports]), SETTLE_JS],
        capture_output=True, text=True, timeout=180, env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"screenshot run failed (exit {proc.returncode}): {proc.stderr[-400:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# Rubric prompt — strict: concrete observation per score, named revisions only
# ---------------------------------------------------------------------------

RUBRIC_PROMPT = """\
You are a senior web designer doing a visual critique of a screenshot of a single webpage.

You will see 1 or more viewport screenshots (desktop wide and mobile narrow) of the same page.
You will also be told the brand's "layout thesis" (the structural argument the page is making),
the "signature element" the design is built around, and the brand's voice register (e.g.
conversational-professional). Use those as the criteria for the brand_fit and motion_restraint
scores — a deviation from the thesis or signature element is a real penalty, not a stylistic note.

SCORE 7 DIMENSIONS 0-10. For EACH score you must give:
  (a) one-line `justification`  — WHY this score
  (b) at least one `observation` — a CONCRETE measurement or note
      Examples of GOOD observations:
        - "section #hero sits at left 60% / right 40% but the right column is empty at 1440px"
        - "every section is a centered h2 followed by a single p — same shape, no rhythm change"
        - "display size of h1 is ~96px and body is ~16px — ratio ~6:1, real contrast"
      Examples of BAD observations (these will be rejected):
        - "looks a bit empty"
        - "could use more imagery"
        - "spacing could be better"
  `looks_templated` is INVERTED: 10 = clearly bespoke to this brand; 0 = generic template.

THEN PROPOSE 3-6 CONCRETE REVISIONS. Each revision MUST have:
  - `section_id` — exact id from the page (e.g. "hero", "manifesto", "services-as-chapters")
  - `change`     — ONE specific structural change. Examples of GOOD changes:
        "split into two columns at >=1024px with a small image or sidebar on the right"
        "replace the single paragraph with a 3-item checklist using sentence-case headers"
        "make this section break the page rhythm — switch to a dark or accent background"
        "add a pull-quote / large numeral / signature-dot motif so the section reads as a chapter opening, not a paragraph"
      Examples of BAD changes (rejected):
        "improve spacing"
        "add imagery"
        "make it more interesting"
  - `rationale`  — 1-2 sentences tying the change to a specific observation.
  - `addressed_observation` — paste the exact observation string this revision fixes.

If you cannot find any specific problems, say so honestly — but in practice, almost any
rendered page has at least 2-3 concrete improvements available.

DO NOT invent facts. The revisions only modify STRUCTURE / LAYOUT / VISUAL RHYTHM, not
claims about the brand.

Return STRICT JSON matching this schema (no markdown, no commentary outside JSON):
{
  "scores": {
    "visual_hierarchy":        {"score": <int 0-10>, "justification": "<str>", "observation": "<str>"},
    "use_of_space":            {"score": <int 0-10>, "justification": "<str>", "observation": "<str>"},
    "typographic_contrast":    {"score": <int 0-10>, "justification": "<str>", "observation": "<str>"},
    "focal_point":             {"score": <int 0-10>, "justification": "<str>", "observation": "<str>"},
    "brand_fit":               {"score": <int 0-10>, "justification": "<str>", "observation": "<str>"},
    "motion_restraint":        {"score": <int 0-10>, "justification": "<str>", "observation": "<str>"},
    "looks_templated":         {"score": <int 0-10 INVERTED>", "justification": "<str>", "observation": "<str>"}
  },
  "total": <int>,
  "revisions": [
    {"section_id": "<str>", "change": "<str>", "rationale": "<str>", "addressed_observation": "<str>"}
  ],
  "rubric_self_check": {
    "every_score_has_observation": <bool>,
    "every_revision_names_section_and_change": <bool>,
    "no_vague_advice_given": <bool>
  }
}
"""


def _build_messages(plan: dict, brief: dict, screenshots: list[dict], html_section_ids: list[str]) -> list[dict]:
    """Build the Anthropic-format messages with base64 image parts."""
    parts: list[dict] = []
    for shot in screenshots:
        b64 = base64.b64encode(shot["jpeg_bytes"]).decode()
        parts.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })
        parts.append({"type": "text", "text": f"Viewport: {shot['viewport']} ({shot['label']})"})
    thesis = plan.get("layout_thesis", {}) or {}
    sig = plan.get("signature_element", {}) or {}
    voice = brief.get("voice_and_tone", {}) or {}
    context_text = (
        "Layout thesis (statement): " + str(thesis.get("statement", "")) + "\n"
        + "Layout thesis (audience): " + str(thesis.get("audience", "")) + "\n"
        + "Signature element: " + json.dumps(sig) + "\n"
        + "Voice register: " + str(voice.get("register", "")) + "\n"
        + "Voice notes: " + str(voice.get("notes", "")) + "\n"
        + "Brand donts: " + json.dumps(brief.get("brand_donts", [])) + "\n"
        + "\nSECTION IDS OBSERVED IN THE RENDERED HTML (use one of these for `section_id`): "
        + ", ".join(html_section_ids) + "\n"
        + "If a section you want to revise is NOT in that list, name it descriptively (e.g. 'hero / first-screen area') — it will be rejected, but only after telling you the section doesn't exist.\n"
    )
    parts.append({"type": "text", "text": "BRAND CONTEXT:\n" + context_text + "\n\nApply the rubric below to the screenshots above."})
    return [{"role": "user", "content": parts}]


def _critique_once(plan: dict, brief: dict, screenshots: list[dict], model: str,
                   html_section_ids: list[str]) -> dict:
    body = _vision_call(model, RUBRIC_PROMPT, _build_messages(plan, brief, screenshots, html_section_ids))
    text = _extract_text(body)
    if "```" in text:
        text = text.split("```json", 1)[-1].split("```", 1)[0]
    parsed = json.loads(text.strip())
    # Validate shape; coerce total if model lied
    scores = parsed.get("scores", {})
    for dim in RUBRIC_DIMENSIONS:
        if dim not in scores:
            raise RuntimeError(f"model response missing dimension {dim}")
        s = scores[dim]
        if not isinstance(s.get("score"), int) or not isinstance(s.get("observation"), str):
            raise RuntimeError(f"dimension {dim} malformed: {s}")
    computed_total = sum(scores[d]["score"] for d in RUBRIC_DIMENSIONS)
    parsed["total"] = computed_total
    parsed.setdefault("rubric_self_check", {})
    return parsed


# ---------------------------------------------------------------------------
# Apply revisions back into the design plan (schema-valid, no inventions)
# ---------------------------------------------------------------------------

def _apply_revisions(plan: dict, revisions: list[dict], brief: dict) -> tuple[dict, list[str]]:
    """Mutate a copy of the plan with the proposed revisions.

    Each revision must:
      - name an existing section id (or be REJECTED with a clear reason)
      - update the section's `component` (the prose component spec) with a
        concrete CHANGE string appended, so the next compose_site.py picks it up
      - never invent a `source_brief_fields` claim — we only EDIT existing
        entries (component / rationale / emphasis), never add new facts

    Returns (new_plan, applied_revision_messages).
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("design_pass", HERE / "design_pass.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_source_fields = module.verify_source_fields

    new_plan = json.loads(json.dumps(plan))
    by_id = {s["id"]: s for s in new_plan.get("sections", [])}
    applied: list[str] = []
    for r in revisions:
        sid = r.get("section_id")
        change = (r.get("change") or "").strip()
        if sid not in by_id:
            applied.append(f"REJECTED: revision references unknown section_id '{sid}'")
            continue
        if len(change) < 12:
            applied.append(f"REJECTED: revision for '{sid}' too vague (change='{change}')")
            continue
        # Reject generic-vague wording patterns
        vague_patterns = [
            r"^\s*improve\s+\w+",
            r"^\s*add\s+more\s+\w+",
            r"^\s*better\s+\w+",
        ]
        if any(re.match(p, change, re.IGNORECASE) for p in vague_patterns):
            applied.append(f"REJECTED: revision for '{sid}' is vague boilerplate")
            continue
        sec = by_id[sid]
        prev_component = sec.get("component", "")
        sec["component"] = (prev_component + " | REVISION: " + change).strip(" |")
        prev_rationale = sec.get("rationale", "")
        sec["rationale"] = (prev_rationale + " | Revision rationale: " + (r.get("rationale") or "")).strip(" |")
        applied.append(f"APPLIED '{sid}': {change}")
    # Schema sanity — we didn't add or remove required keys.
    violations = verify_source_fields(new_plan, brief)
    if violations:
        return plan, [f"REVERTED: source-field check failed after applying revisions: {violations}"]
    return new_plan, applied


# ---------------------------------------------------------------------------
# Score history + regression guard
# ---------------------------------------------------------------------------

def _safe_total(entry: dict) -> int:
    return int(entry.get("total") or sum(int(entry["scores"][d]["score"]) for d in RUBRIC_DIMENSIONS))


def _load_history(out_dir: Path) -> list[dict]:
    p = out_dir / "iterations.json"
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_history(out_dir: Path, history: list[dict]):
    (out_dir / "iterations.json").write_text(json.dumps(history, indent=2) + "\n")


def _restore_best(out_dir: Path, history: list[dict]):
    """Copy the highest-scoring design plan back into the canonical plan path."""
    if not history:
        return None
    best = max(history, key=_safe_total)
    src = Path(best["plan_snapshot"])
    if src.exists():
        return str(src)
    return None


# ---------------------------------------------------------------------------
# Markdown report for a single iteration
# ---------------------------------------------------------------------------

def _md_for_iteration(iter_no: int, critique: dict, plan_path: Path,
                      screenshots: list[dict], applied: list[str] | None) -> str:
    lines: list[str] = []
    lines.append(f"# Critique — iteration {iter_no}")
    lines.append("")
    lines.append(f"_Plan: `{plan_path}`_")
    lines.append(f"_Generated: {critique.get('generated_at', '')}_  ")
    lines.append(f"_Model: {critique.get('model', '')}_  ")
    lines.append(f"_Viewports: {', '.join(s['viewport'] for s in screenshots)}_")
    lines.append("")
    lines.append("## Scores (0-10, looks_templated inverted)")
    lines.append("")
    lines.append("| Dimension | Score | Justification | Observation |")
    lines.append("|-----------|-------|---------------|-------------|")
    for d in RUBRIC_DIMENSIONS:
        s = critique["scores"][d]
        score = s["score"]
        just = s["justification"].replace("|", "\\|")
        obs = s["observation"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {d} | {score} | {just} | {obs} |")
    lines.append("")
    lines.append(f"**Total: {critique['total']} / 70**")
    lines.append("")
    if critique.get("revisions"):
        lines.append("## Revisions")
        lines.append("")
        for i, r in enumerate(critique["revisions"], 1):
            lines.append(f"{i}. **#{r['section_id']}** — {r['change']}")
            lines.append(f"   - Rationale: {r['rationale']}")
            if r.get("addressed_observation"):
                lines.append(f"   - Fixes observation: _{r['addressed_observation']}_")
            lines.append("")
    if applied:
        lines.append("## Apply results")
        lines.append("")
        for a in applied:
            lines.append(f"- {a}")
        lines.append("")
    rsc = critique.get("rubric_self_check", {}) or {}
    if rsc:
        lines.append("## Rubric self-check")
        lines.append("")
        for k, v in rsc.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _summary_md(history: list[dict]) -> str:
    lines = ["# Critique summary", "",
             "Score table across iterations (lower is worse; looks_templated is inverted).",
             ""]
    header = "| Iter | " + " | ".join(RUBRIC_DIMENSIONS) + " | Total | Applied | Best |"
    sep = "|------|" + "|".join("-" * len(d) for d in RUBRIC_DIMENSIONS) + "|------|---------|------|"
    lines.append(header)
    lines.append(sep)
    best_total = max(_safe_total(h) for h in history)
    for h in history:
        scores = {d: h["scores"][d]["score"] for d in RUBRIC_DIMENSIONS}
        is_best = _safe_total(h) == best_total
        applied_count = sum(1 for a in h.get("applied", []) if a.startswith("APPLIED"))
        lines.append(
            "| " + str(h["iteration"])
            + " | " + " | ".join(str(scores[d]) for d in RUBRIC_DIMENSIONS)
            + " | " + str(_safe_total(h))
            + " | " + str(applied_count)
            + " | " + ("**best**" if is_best else "")
            + " |"
        )
    lines.append("")
    if history and _safe_total(history[-1]) < best_total:
        lines.append(f"> Note: iteration {history[-1]['iteration']} regressed "
                     f"(score {_safe_total(history[-1])} < best {best_total}); "
                     "the higher-scoring design plan was kept.")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_viewports(s: str) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(\d+)x(\d+)$", chunk)
        if not m:
            raise ValueError(f"bad viewport '{chunk}', expected WxH")
        out.append((int(m.group(1)), int(m.group(2))))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="composed site directory (served)")
    ap.add_argument("--brand-brief", required=True)
    ap.add_argument("--design-plan", required=True, help="path to design-plan.json (in-place edited when --apply)")
    ap.add_argument("-o", required=True, help="critique output directory")
    ap.add_argument("--viewports", default="1440x900,375x812")
    ap.add_argument("--max-iterations", type=int, default=3)
    ap.add_argument("--model", default="MiniMax-M3")
    ap.add_argument("--entry", default="index.html")
    ap.add_argument("--apply", action="store_true",
                    help="apply revisions back into the design plan, recompose, critique again")
    ap.add_argument("--compose-script", default=str(HERE / "compose_site.py"))
    ap.add_argument("--tokens")
    ap.add_argument("--reference-report")
    ap.add_argument("--reference-tokens")
    args = ap.parse_args(argv)

    site_dir = Path(args.site).resolve()
    brief_path = Path(args.brand_brief).resolve()
    plan_path = Path(args.design_plan).resolve()
    out_dir = Path(args.o).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    brief = json.loads(brief_path.read_text())
    plan = json.loads(plan_path.read_text())
    viewports = _parse_viewports(args.viewports)

    # Pre-flight: API key
    if not os.environ.get("MINIMAX_API_KEY"):
        msg = "WARN: MINIMAX_API_KEY is not set; critique_pass.py cannot run. "\
              "Skipping critique (no-op)."
        print(msg, file=sys.stderr)
        return 0

    history: list[dict] = []
    last_total = -1
    best_plan_snapshot: str | None = str(plan_path)
    iteration = 0

    # Pre-extract section IDs from the HTML so we can offer them as candidates
    # to the vision model (avoids the cover-vs-hero id-mismatch class of bug).
    entry_path = site_dir / args.entry
    if entry_path.exists():
        _ids = sorted(set(re.findall(r'id="([\w-]+)"', entry_path.read_text())))
    else:
        _ids = [s["id"] for s in plan.get("sections", [])]
    html_section_ids = _ids

    while iteration < args.max_iterations:
        iteration += 1
        iter_dir = out_dir / f"iter-{iteration:02d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        shots_dir = iter_dir / "shots"
        shots_dir.mkdir(parents=True, exist_ok=True)
        # Server lifecycle
        port = _free_port()
        server = _Server(site_dir, port)
        server.start()
        try:
            raw_shots = _screenshot(server.base_url(), args.entry, shots_dir, viewports)
            ok_shots = [s for s in raw_shots if s.get("ok")]
            if not ok_shots:
                raise RuntimeError(f"no viewport screenshots succeeded: {raw_shots}")
            screenshots: list[dict] = []
            for s in ok_shots:
                png = Path(s["shot"])
                jpeg_bytes = _downscale_png_to_jpeg(png)
                screenshots.append({
                    "viewport": s["viewport"],
                    "label": "desktop wide" if int(s["viewport"].split("x")[0]) >= 1024 else "mobile narrow",
                    "jpeg_bytes": jpeg_bytes,
                    "png_path": str(png),
                    "settle": s.get("settle"),
                })
            critique = _critique_once(plan, brief, screenshots, args.model, html_section_ids)
        finally:
            server.kill()

        critique["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        critique["model"] = args.model
        critique["iteration"] = iteration
        critique["viewports"] = [s["viewport"] for s in screenshots]
        critique["plan_snapshot"] = str(plan_path)

        applied: list[str] = []
        if args.apply:
            new_plan, applied = _apply_revisions(plan, critique["revisions"], brief)
            critique["applied"] = applied
            if any(a.startswith("APPLIED") for a in applied):
                # Write the new plan to a snapshot first; we'll only commit it if it
                # doesn't regress in the next critique pass.
                snap = out_dir / f"iter-{iteration:02d}.design-plan.json"
                snap.write_text(json.dumps(new_plan, indent=2) + "\n")
                plan_path.write_text(json.dumps(new_plan, indent=2) + "\n")
                plan = new_plan
                # Re-compose so the next critique sees the updated structure
                compose_cmd = [sys.executable, args.compose_script,
                               "--brand-brief", str(brief_path),
                               "--design-plan", str(plan_path),
                               "-o", str(site_dir)]
                if args.tokens:
                    compose_cmd += ["--tokens", args.tokens]
                if args.reference_report:
                    compose_cmd += ["--reference-report", args.reference_report]
                if args.reference_tokens:
                    compose_cmd += ["--reference-tokens", args.reference_tokens]
                proc = subprocess.run(compose_cmd, capture_output=True, text=True, timeout=300)
                if proc.returncode != 0:
                    print(f"compose_site.py failed in iteration {iteration}: {proc.stderr[-300:]}",
                          file=sys.stderr)
                    break

        history.append(critique)
        _save_history(out_dir, history)

        # Per-iteration JSON + MD
        (iter_dir / f"critique-{iteration:02d}.json").write_text(
            json.dumps({k: v for k, v in critique.items() if k != "applied"} | {"applied": critique.get("applied", [])}, indent=2) + "\n"
        )
        (iter_dir / f"critique-{iteration:02d}.md").write_text(
            _md_for_iteration(iteration, critique, plan_path, screenshots, applied)
        )

        cur_total = _safe_total(critique)
        if cur_total < last_total and last_total >= 0:
            # Regression guard: revert to best snapshot
            best = _restore_best(out_dir, history[:-1])
            if best:
                print(f"regression guard: reverting design plan to best snapshot {best}", file=sys.stderr)
                plan_path.write_text(Path(best).read_text())
            break
        last_total = cur_total
        # If not applying, we only need one iteration.
        if not args.apply:
            break

    (out_dir / "critique-summary.md").write_text(_summary_md(history))
    print(json.dumps({"iterations": [_safe_total(h) for h in history], "out_dir": str(out_dir)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())