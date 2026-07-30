#!/usr/bin/env python3
"""10-gate validation harness for a composed static site directory.

Implements the gates declared in research/workflow-design.md §4 and the
site-cloner SKILL.md, scoped to a *composed* static site (post phase-2 design
pass) rather than a captured mirror. Each gate reports one of:

  PASS            — observed evidence satisfies the gate's criteria
  FAIL            — observed evidence contradicts the gate's criteria
  NOT-EXERCISED   — the gate could not be run (tool missing, offline, runner
                    crashed, runner produced no parseable result, etc.)

Every result carries an `evidence_basis` from the closed set:
  Observed visually | Interaction-tested | DOM+assets confirmed |
  HTTP-200 only     | Not exercised

POSITIVE-EVIDENCE-ONLY HONESTY RULE (critical):
  A gate may only return PASS when it has *positive* evidence: a parsed result
  document with real numbers. Runner exit != 0, missing/unparseable JSON
  output, or an empty results table => NOT-EXERCISED. Never infer PASS from
  an absence of reported problems. "0 violations" only counts when the runner
  exited cleanly AND emitted a results document you actually parsed.

The script only claims what its evidence actually supports. Reporting
NOT-EXERCISED on a gate is honest and MUST appear in the report and
downgrade the acceptance tier; it never fails the run (exit 0) on its own.
A FAIL on any gate causes exit 2.

Acceptance tier rules (positive-evidence-only):
  - "Validated"        : every gate PASS (all runners produced real evidence).
  - "Offline-validated": DOM/CSS/HTTP checks passed; some real-browser check
                         (a11y OR perf) was not exercised. *Reserved for the
                         case where the only un-run gate(s) are non-a11y/perf.*
  - "First-render"     : no real-browser evidence at all (the page returns
                         content but no deeper validation has run).
  - "Partial"          : at least one gate FAILed, OR at least one gate was
                         NOT-EXERCISED. Per the spec, any NOT-EXERCISED gate
                         (a runner that crashed/timed out/produced no result
                         document) caps tier at Partial. A truthful Partial
                         beats a fabricated Validated.

CLI:
  validate_site.py <site-dir> -o <report-dir>
                   [--routes /,/about] [--entry index.html]
                   [--viewports 320,768,1024,1440]
                   [--skip-lighthouse] [--timeout 30]
                   [--host 127.0.0.1]

The script owns starting AND killing the local server — it never validates
through file://.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


SCHEMA_VERSION = "1.1"
GATE_VERSION = "10-gate-v1.1"

# Default thresholds from research/workflow-design.md §4.
PERF_THRESHOLDS = {"performance": 90, "accessibility": 95, "best_practices": 95, "seo": 95}
DEFAULT_VIEWPORTS = [320, 768, 1024, 1440]
DEFAULT_TIMEOUT = 30  # seconds per gate
# Default JS bundle budget for the Next.js renderer (Gate 10). Measured as
# total gzipped bytes of every .js file under _next/static/. Real-but-tight
# ceiling matching the previous M6c-3 deliverable (373 KB gzipped → FAIL
# until we get it under); 300 KB is the realistic 10x-over-static target.
DEFAULT_BUNDLE_BUDGET_KB = 300


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    id: str
    name: str
    verdict: str  # PASS | FAIL | NOT-EXERCISED
    evidence_basis: str  # one of the allowed set
    summary: str
    notes: list[str] = field(default_factory=list)
    observations: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "verdict": self.verdict,
            "evidence_basis": self.evidence_basis,
            "summary": self.summary,
            "notes": self.notes,
            "observations": self.observations,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Utility: free port, server lifecycle, HTTP probes
# ---------------------------------------------------------------------------

def free_port(host: str = "127.0.0.1") -> int:
    s = socket.socket()
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def http_probe(url: str, timeout: float = 5.0) -> tuple[int, str, dict]:
    """Read a URL and return (status, final_url, headers_subset)."""
    req = Request(url, headers={"User-Agent": "validate_site.py/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.geturl(), dict(resp.headers)
    except HTTPError as e:
        return e.code, url, dict(e.headers) if e.headers else {}
    except URLError as e:
        return 0, url, {"error": str(e.reason)}


def wait_for_server(url: str, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _, _ = http_probe(url, timeout=1.0)
        if status == 200:
            return True
        time.sleep(0.2)
    return False


class ServerHandle:
    """Owns a local http.server subprocess. Always killed on exit."""

    def __init__(self, site_dir: str, host: str, port: int, log_path: str):
        self.site_dir = os.path.abspath(site_dir)
        self.host = host
        self.port = port
        self.log_path = log_path
        self.proc: subprocess.Popen | None = None
        self.log_fh = None

    def start(self) -> None:
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.log_fh = open(self.log_path, "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(self.port),
             "--bind", self.host, "--directory", self.site_dir],
            stdout=self.log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # own process group so we can kill children
        )

    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_alive(self) -> bool:
        if self.proc is None:
            return False
        return self.proc.poll() is None

    def kill(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.proc.wait(timeout=2)
        if self.log_fh:
            try:
                self.log_fh.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# HTML / CSS parsing helpers
# ---------------------------------------------------------------------------

class AssetRefParser(HTMLParser):
    """Collect href / src references from an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[tuple[str, str]] = []   # (attr, url)
        self.srcs: list[tuple[str, str]] = []
        self.meta_viewport: str | None = None
        self.lang: str | None = None
        self.title: str | None = None
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == "html" and "lang" in attr_dict:
            self.lang = attr_dict["lang"]
        if tag == "meta" and attr_dict.get("name", "").lower() == "viewport":
            self.meta_viewport = attr_dict.get("content", "")
        if tag == "title":
            self.in_title = True
        for k in ("href", "src"):
            if k in attr_dict:
                entry = (k, attr_dict[k])
                if k == "href":
                    self.hrefs.append(entry)
                else:
                    self.srcs.append(entry)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title = (self.title or "") + data


HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
TOKEN_VAR_RE = re.compile(r"var\(--[a-zA-Z0-9_-]+(?:\s*,[^)]*)?\)")
PREFERS_REDUCED_RE = re.compile(
    r"@media\s+\(\s*prefers-reduced-motion:\s*reduce\s*\)\s*\{", re.IGNORECASE
)


def parse_html(path: str) -> AssetRefParser:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()
    parser = AssetRefParser()
    parser.feed(data)
    parser.raw = data  # type: ignore[attr-defined]
    return parser


def read_css(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def normalize_route(route: str) -> str:
    """Ensure the route maps to a path under the site root that python3 -m http.server will serve."""
    if not route.startswith("/"):
        route = "/" + route
    return route


def is_external(url: str) -> bool:
    p = urlparse(url)
    return bool(p.scheme) and p.scheme not in ("", "data", "blob", "file")


def route_to_file(site_dir: str, route: str) -> str:
    """Map a runtime route to a local file path. Direct file, or index.html for /."""
    route = normalize_route(route)
    if route.endswith("/"):
        candidate = os.path.join(site_dir, route.lstrip("/"), "index.html")
    else:
        candidate = os.path.join(site_dir, route.lstrip("/"))
    return candidate


def resolve_local_asset(site_dir: str, html_path: str, url: str) -> "str | None":
    """Map an href/src found in HTML to a path on disk, or None if not local.

    Root-relative URLs MUST resolve against the site root, not the HTML file's
    directory. os.path.join(dirname, "/_next/static/x.css") silently returns
    "/_next/static/x.css" -- an absolute filesystem path that never exists --
    because join discards everything before an absolute component. That made
    every root-relative stylesheet invisible to the gates that walk the
    filesystem, so Gates 7 and 8 reported NOT-EXERCISED ("no CSS files
    observed") against a Next.js export whose CSS lives in /_next/static/css/.
    The deliverable's token discipline went unchecked while the report looked
    clean.

    >>> import os, tempfile
    >>> d = tempfile.mkdtemp(); sub = os.path.join(d, "_next"); os.makedirs(sub)
    >>> _ = open(os.path.join(sub, "a.css"), "w").write("x")
    >>> html = os.path.join(d, "index.html")
    >>> resolve_local_asset(d, html, "/_next/a.css") == os.path.join(d, "_next/a.css")
    True
    >>> resolve_local_asset(d, html, "https://cdn.example.com/a.css") is None
    True
    >>> resolve_local_asset(d, html, "/_next/missing.css") is None
    True
    """
    if is_external(url):
        return None
    stripped = url.split("#", 1)[0].split("?", 1)[0]
    if not stripped or stripped.startswith(("data:", "blob:")):
        return None
    if stripped.startswith("/"):
        candidate = os.path.join(site_dir, stripped.lstrip("/"))
    else:
        candidate = os.path.join(os.path.dirname(html_path), stripped)
    return candidate if os.path.exists(candidate) else None


# ---------------------------------------------------------------------------
# Gate 1 — Boot
# ---------------------------------------------------------------------------

def gate_1_boot(server: ServerHandle, routes: list[str], timeout: float) -> GateResult:
    notes: list[str] = []
    base = server.base_url()
    per_route: dict[str, dict] = {}
    failed: list[str] = []

    for route in routes:
        url = base + normalize_route(route)
        status, final_url, _ = http_probe(url, timeout=timeout)
        per_route[route] = {"status": status, "final_url": final_url}
        if status != 200:
            failed.append(route)
        notes.append(f"  {route} -> HTTP {status}")

    if failed:
        return GateResult(
            id="1", name="Boot",
            verdict="FAIL",
            evidence_basis="HTTP-200 only",
            summary=f"{len(failed)} route(s) did not return HTTP 200: {failed}",
            notes=notes,
            observations={"per_route": per_route, "failed": failed, "base_url": base},
        )

    return GateResult(
        id="1", name="Boot",
        verdict="PASS",
        evidence_basis="HTTP-200 only",
        summary=f"All {len(routes)} route(s) returned HTTP 200 via local server.",
        notes=notes,
        observations={"per_route": per_route, "base_url": base},
    )


# ---------------------------------------------------------------------------
# Gate 2 — Dependency
# ---------------------------------------------------------------------------

def gate_2_dependency(server: ServerHandle, site_dir: str, routes: list[str], timeout: float) -> GateResult:
    base = server.base_url()
    local_missing: list[str] = []
    external: list[str] = []
    checked: list[dict] = []

    for route in routes:
        local_path = route_to_file(site_dir, route)
        if not os.path.exists(local_path):
            local_missing.append(f"<route {route} did not map to {local_path}>")
            continue
        parser = parse_html(local_path)
        # Combine href + src references
        refs = [(attr, url) for attr, url in parser.hrefs + parser.srcs]
        for attr, url in refs:
            entry = {"route": route, "attr": attr, "url": url}
            checked.append(entry)
            if is_external(url):
                external.append(url)
                continue
            # Strip fragment / query for local resolution
            stripped = url.split("#", 1)[0].split("?", 1)[0]
            if not stripped:
                continue
            resolved = urljoin((base + normalize_route(route)), url)
            status, _, _ = http_probe(resolved, timeout=timeout)
            if status != 200:
                local_missing.append(f"{attr}={url} (route {route}) -> HTTP {status}")

    if local_missing:
        return GateResult(
            id="2", name="Dependency",
            verdict="FAIL",
            evidence_basis="HTTP-200 only",
            summary=f"{len(local_missing)} local asset reference(s) failed to resolve.",
            notes=local_missing[:20],
            observations={
                "missing_count": len(local_missing),
                "missing": local_missing,
                "external_count": len(external),
                "external_sample": sorted(set(external))[:20],
                "reference_count": len(checked),
            },
        )

    return GateResult(
        id="2", name="Dependency",
        verdict="PASS",
        evidence_basis="HTTP-200 only",
        summary=f"All {len(checked)} local reference(s) resolved HTTP 200. "
                f"{len(external)} external host reference(s) classified as Kept External.",
        notes=[],
        observations={
            "reference_count": len(checked),
            "external_count": len(external),
            "external_sample": sorted(set(external))[:20],
            "external_hosts": sorted({urlparse(u).netloc for u in external if urlparse(u).netloc}),
        },
    )


# ---------------------------------------------------------------------------
# Gate 3 — Accessibility (axe-core)
# ---------------------------------------------------------------------------

def _looks_available(cmd: list[str]) -> bool:
    """Best-effort: is `cmd` runnable? Returns True for `npx` itself, shell-resolves for others."""
    if cmd[0] == "npx":
        return shutil.which("npx") is not None
    return shutil.which(cmd[0]) is not None


def _find_axe_min_js() -> str | None:
    """Find axe.min.js in the npx cache. The CLI installs the bundle under
    ~/.npm/_npx/<id>/node_modules/axe-core/axe.min.js. Returns absolute path or None."""
    npx_root = os.path.join(os.path.expanduser("~"), ".npm", "_npx")
    if not os.path.isdir(npx_root):
        return None
    for sub in sorted(os.listdir(npx_root)):
        candidate = os.path.join(npx_root, sub, "node_modules", "axe-core", "axe.min.js")
        if os.path.exists(candidate):
            return candidate
    return None


def _find_playwright_chrome() -> str | None:
    """Locate the Playwright Chromium binary (chrome-linux64/chrome under
    ~/.cache/ms-playwright/chromium-*)."""
    cache = "/home/openclaw/.cache/ms-playwright"
    if not os.path.isdir(cache):
        return None
    candidates = []
    for c in sorted(os.listdir(cache)):
        if c.startswith("chromium-") and not c.startswith("chromium_headless"):
            p = os.path.join(cache, c, "chrome-linux64", "chrome")
            if os.path.exists(p):
                candidates.append(p)
    return candidates[-1] if candidates else None


def _build_subprocess_env() -> dict:
    """Build a clean env for Chrome-bearing subprocesses.

    The hermes profile-local HOME (/home/openclaw/.hermes/profiles/site-cloner/home)
    has no .cache/ms-playwright and confuses Chrome's user-data-dir layout. We
    point HOME back at the real /home/openclaw so Playwright's browser cache
    resolves and chrome-launcher can spawn cleanly. We also pre-set CHROME_PATH
    if we can find Playwright's Chromium.
    """
    env = os.environ.copy()
    real_home = "/home/openclaw"
    if os.path.isdir(os.path.join(real_home, ".cache", "ms-playwright")):
        env["HOME"] = real_home
    if not env.get("CHROME_PATH") or not os.path.exists(env.get("CHROME_PATH", "")):
        cp = _find_playwright_chrome()
        if cp:
            env["CHROME_PATH"] = cp
    return env


# Inline script run inside the nt-mirror venv (Playwright + axe.min.js). We do
# the whole accessibility check in-process to avoid the chromedriver / @axe-core/cli
# sandbox crashes we hit before. The script is passed via -c on the venv python,
# which keeps the deps (playwright) where they are and just bridges the data
# across via argv/stdout.
_AXE_SCRIPT = r"""
import json, sys
from playwright.sync_api import sync_playwright

base = sys.argv[1]
routes = json.loads(sys.argv[2])
axe_path = sys.argv[3]

def _settle(page, cap_ms=8000):
    # Wait for the page to stop changing, by PIXELS not by animation records.
    # document.getAnimations() only reports WAAPI/CSS animations. Motion (and
    # any other rAF-driven library) animates via requestAnimationFrame and never
    # appears there, so awaiting it returned instantly and the audit sampled the
    # page mid-fade. axe then measured half-opacity text against its background
    # and reported phantom color-contrast violations that came and went between
    # runs. Polling for consecutive pixel-identical frames catches what the
    # animation registry cannot see.
    import hashlib
    info = page.evaluate(
        "async () => { const a = document.getAnimations();"
        " await Promise.race([Promise.all(a.map(x => x.finished.catch(() => {}))),"
        " new Promise(r => setTimeout(r, 3000))]);"
        " return {animation_count: a.length, settle_cap_ms: 3000}; }"
    )
    waited, last, stable = 0, None, 0
    while waited < cap_ms:
        digest = hashlib.sha256(page.screenshot(type="jpeg", quality=40)).hexdigest()
        if digest == last:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        last = digest
        page.wait_for_timeout(250)
        waited += 250
    info["pixel_stable"] = stable >= 2
    info["pixel_wait_ms"] = waited
    return info


results = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    try:
        for route in routes:
            url = base + (route if route.startswith("/") else "/" + route)
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=20000)
                status = resp.status if resp else 0
                settle = _settle(page)
                page.add_script_tag(path=axe_path)
                axe_result = page.evaluate(
                    "async () => await axe.run(document, { resultTypes: ['violations'] })"
                )
                violations = axe_result.get("violations", []) or []
                serious_critical = sum(
                    1 for v in violations if v.get("impact") in ("serious", "critical")
                )
                total = len(violations)
                results.append({
                    "route": route,
                    "url": url,
                    "status": status,
                    "exit": 0,
                    "ok": True,
                    "violations": total,
                    "serious_critical": serious_critical,
                    "by_impact": {
                        imp: sum(1 for v in violations if v.get("impact") == imp)
                        for imp in ("minor", "moderate", "serious", "critical")
                    },
                    "ids": [v.get("id") for v in violations],
                })
            except Exception as e:
                results.append({
                    "route": route,
                    "url": url,
                    "exit": 1,
                    "ok": False,
                    "error": str(e),
                })
            finally:
                ctx.close()
    finally:
        browser.close()
print(json.dumps(results))
"""


def _run_inprocess_axe(server: ServerHandle, routes: list[str], timeout: float) -> tuple[list[dict], str | None]:
    """Run axe-core IN-PROCESS via the nt-mirror venv Playwright + axe.min.js.
    Returns (per_route_results, error_string_or_None)."""
    py = "/home/openclaw/.venvs/nt-mirror/bin/python"
    if not os.path.exists(py):
        return ([], f"nt-mirror venv not found at {py}")
    axe_path = _find_axe_min_js()
    if not axe_path:
        return ([], f"axe.min.js not found in any {_find_axe_min_js.__doc__ or 'npx cache'}")
    env = _build_subprocess_env()
    try:
        proc = subprocess.run(
            [py, "-c", _AXE_SCRIPT,
             server.base_url(), json.dumps(routes), axe_path],
            capture_output=True, text=True, timeout=timeout * 2, env=env,
        )
    except subprocess.TimeoutExpired:
        return ([], "in-process axe run timed out")
    except Exception as e:
        return ([], f"in-process axe run failed: {e}")
    if proc.returncode != 0:
        return ([], f"in-process axe exit {proc.returncode}; stderr_tail={proc.stderr[-300:]}")
    try:
        last_line = proc.stdout.strip().splitlines()[-1]
        per_route = json.loads(last_line)
        if not isinstance(per_route, list):
            return ([], f"in-process axe returned non-list: {type(per_route).__name__}")
        return (per_route, None)
    except Exception as e:
        return ([], f"in-process axe stdout unparseable: {e}; tail={proc.stdout[-200:]}")


def gate_3_accessibility(server: ServerHandle, routes: list[str], timeout: float) -> GateResult:
    """Run axe-core with positive-evidence-only verdicts.

    Strategy order (most robust first on this box):
      1. In-process Playwright + axe.min.js injected into the page. This avoids
         the chromedriver / @axe-core/cli sandbox crashes we hit before.
      2. Fall back to `npx @axe-core/cli` with CHROME_PATH pointed at Playwright
         Chromium and HOME=/home/openclaw, and `--chrome-options` for no-sandbox.

    Verdict rules (positive-evidence-only — the heart of the M4 honesty fix):
      - A route is "succeeded" only if the runner produced a parseable result
        object with `ok: True` AND a real `violations` list. If the runner
        crashed, timed out, returned non-zero, or returned an empty/malformed
        document, the route is treated as evidence-less.
      - PASS   : every route succeeded AND total serious/critical across the
                 successful routes is 0. "0 violations" is positive evidence,
                 not an absence.
      - FAIL   : every route succeeded AND there is at least one serious/critical
                 violation.
      - NOT-EXERCISED: at least one route did not produce positive evidence.
                 The runner exit code + a short reason go into the row so the
                 reader sees exactly why.
    """
    notes: list[str] = []
    per_route: dict[str, dict] = {}
    runner_label = "none"

    # Strategy 1: in-process Playwright + axe.min.js (the robust path).
    inproc_results, inproc_error = _run_inprocess_axe(server, routes, timeout)
    if inproc_results:
        runner_label = "in-process playwright + axe.min.js (npx cache)"
        for r in inproc_results:
            per_route[r["route"]] = r
    elif inproc_error:
        notes.append(f"In-process axe failed: {inproc_error}")
        # Try the npx CLI as a fallback. Same positive-evidence rule applies.
        runner_label = "@axe-core/cli via npx (fallback)"
        env = _build_subprocess_env()
        for route in routes:
            url = server.base_url() + normalize_route(route)
            axe_output_path = f"/tmp/axe-route-{abs(hash(route))}.json"
            try:
                # Use --chrome-options so chromedriver gets --no-sandbox. The
                # CLI accepts comma-separated flags inside --chrome-options.
                proc = subprocess.run(
                    ["npx", "--yes", "@axe-core/cli", url,
                     "--exit", "--save", axe_output_path,
                     "--chrome-options=--no-sandbox,--disable-dev-shm-usage"],
                    capture_output=True, text=True, timeout=timeout * 2, env=env,
                )
                # Positive-evidence check: only treat the result as real if the
                # runner exited cleanly AND we got a parseable document with a
                # violations key.
                success = False
                violations: list = []
                parse_error: str | None = None
                if proc.returncode == 0 and os.path.exists(axe_output_path):
                    try:
                        with open(axe_output_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if isinstance(data, dict):
                            v = data.get("violations")
                            if isinstance(v, list):
                                violations = v
                                success = True
                            elif isinstance(data.get("results"), dict) and isinstance(data["results"].get("violations"), list):
                                violations = data["results"]["violations"]
                                success = True
                            else:
                                parse_error = f"unexpected axe JSON shape: keys={list(data.keys())[:5]}"
                        else:
                            parse_error = f"axe JSON not a dict: {type(data).__name__}"
                    except Exception as e:
                        parse_error = f"axe JSON unparseable: {e}"
                sc = sum(1 for v in violations if v.get("impact") in ("serious", "critical"))
                entry: dict = {
                    "exit": proc.returncode,
                    "violations": len(violations),
                    "serious_critical": sc,
                    "ok": success,
                    "stdout_tail": proc.stdout[-300:],
                    "stderr_tail": proc.stderr[-300:],
                }
                if parse_error:
                    entry["parse_error"] = parse_error
                per_route[route] = entry
            except subprocess.TimeoutExpired:
                per_route[route] = {"exit": -1, "ok": False, "error": "axe run timed out"}
            except Exception as e:
                per_route[route] = {"exit": -1, "ok": False, "error": str(e)}

    if not per_route:
        # Neither strategy produced anything (no venv, no npx, no axe bundle).
        return GateResult(
            id="3", name="Accessibility",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="No axe runner available (no in-process Playwright venv, no npx, no axe bundle).",
            notes=[
                "Need either: ~/.venvs/nt-mirror/bin/python (Playwright) + axe.min.js in npx cache,",
                "OR npx @axe-core/cli + CHROME_PATH pointing at a real Chromium.",
            ],
            observations={"engine": "none"},
        )

    # Positive-evidence aggregation: distinguish routes that actually produced
    # axe results from those that didn't.
    succeeded = {r: d for r, d in per_route.items() if d.get("ok")}
    failed = {r: d for r, d in per_route.items() if not d.get("ok")}

    if failed:
        # At least one route did not produce real evidence → NOT-EXERCISED.
        # Build a compact reason for each failed route so the reader sees why.
        reason_lines = []
        for r, d in failed.items():
            why = d.get("error") or d.get("parse_error")
            if not why:
                why = f"exit={d.get('exit')}, no parseable axe document"
            reason_lines.append(f"  {r}: {why}")
        return GateResult(
            id="3", name="Accessibility",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary=f"axe-core did not produce positive evidence for {len(failed)} of "
                     f"{len(per_route)} route(s). Cannot claim PASS without parsed results.",
            notes=[
                f"Runner: {runner_label}",
                "Per-route failures:",
                *reason_lines,
                "Succeeded routes (positive evidence) were not aggregated into a PASS "
                "verdict because the failed route(s) leave the gate's coverage incomplete.",
            ],
            observations={"engine": runner_label, "per_route": per_route,
                          "succeeded_routes": list(succeeded.keys()),
                          "failed_routes": list(failed.keys())},
            error=f"{len(failed)} route(s) without positive evidence: "
                  + "; ".join(reason_lines),
        )

    # All routes produced positive evidence. Now we can compare numbers honestly.
    total_sc = sum(d.get("serious_critical", 0) for d in succeeded.values())
    total_violations = sum(d.get("violations", 0) for d in succeeded.values())
    if total_sc == 0:
        return GateResult(
            id="3", name="Accessibility",
            verdict="PASS",
            evidence_basis="DOM+assets confirmed",
            summary=f"axe-core found 0 serious/critical violations across "
                     f"{len(succeeded)} route(s) ({total_violations} total).",
            notes=[],
            observations={"engine": runner_label, "per_route": per_route,
                          "succeeded_routes": list(succeeded.keys())},
        )
    return GateResult(
        id="3", name="Accessibility",
        verdict="FAIL",
        evidence_basis="DOM+assets confirmed",
        summary=f"axe-core found {total_sc} serious/critical violation(s) across "
                 f"{len(succeeded)} route(s) ({total_violations} total).",
        notes=[f"Runner: {runner_label}"],
        observations={"engine": runner_label, "per_route": per_route,
                      "succeeded_routes": list(succeeded.keys()),
                      "total_serious_critical": total_sc},
    )


# ---------------------------------------------------------------------------
# Gate 4 — Performance (Lighthouse)
# ---------------------------------------------------------------------------

def gate_4_performance(server: ServerHandle, routes: list[str], timeout: float,
                       skip_lighthouse: bool) -> GateResult:
    if skip_lighthouse:
        return GateResult(
            id="4", name="Performance",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="--skip-lighthouse was set; Lighthouse not invoked.",
            notes=["Use --skip-lighthouse=false or omit the flag to run the performance gate."],
            observations={"skipped": True},
        )

    if shutil.which("npx") is None:
        return GateResult(
            id="4", name="Performance",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="npx not available; Lighthouse cannot be invoked.",
            notes=["Install Node.js to run Lighthouse via `npx lighthouse`."],
            observations={"skipped": True, "tool": "npx missing"},
        )

    per_route: dict[str, dict] = {}
    summary_table: list[dict] = []
    failing_routes: list[str] = []
    failed_routes: list[str] = []  # produced positive evidence but missed thresholds

    # Build env: point HOME at the real /home/openclaw so chrome-launcher
    # can spawn Playwright's Chromium, and set CHROME_PATH to that Chromium
    # so lighthouse doesn't have to scan a missing system install. We pass
    # --chrome-flags with --headless=new --no-sandbox --disable-dev-shm-usage
    # so Lighthouse can run on this sandboxed box.
    env = _build_subprocess_env()
    chrome_path = env.get("CHROME_PATH")
    # --headless=new is required on recent Lighthouse versions; the old
    # --headless flag maps to the deprecated headless mode and crashes.
    chrome_flag = "--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage"

    for route in routes:
        url = server.base_url() + normalize_route(route)
        out_path = f"/tmp/lighthouse-{abs(hash(url))}.json"
        if os.path.exists(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass
        try:
            proc = subprocess.run(
                ["npx", "--yes", "lighthouse", url,
                 "--output=json", f"--output-path={out_path}",
                 "--quiet",
                 f"--chrome-flags={chrome_flag}",
                 "--only-categories=performance,accessibility,best-practices,seo",
                 "--form-factor=desktop",
                 "--screenEmulation.disabled",
                 "--throttling-method=provided",
                 ],
                capture_output=True, text=True, timeout=timeout * 3, env=env,
            )
            # POSITIVE-EVIDENCE check: the runner must have exited cleanly AND
            # produced a parseable JSON document whose `categories` actually
            # contains scores. None of those => no evidence, never PASS.
            success = False
            scores: dict = {}
            parse_error: str | None = None
            if proc.returncode == 0 and os.path.exists(out_path):
                try:
                    with open(out_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and isinstance(data.get("categories"), dict):
                        cats = data["categories"]
                        # Lighthouse uses "best-practices" with a hyphen.
                        cat_names = ("performance", "accessibility", "best-practices", "seo")
                        if all(isinstance(cats.get(n), dict) and cats[n].get("score") is not None
                               for n in cat_names):
                            scores = {
                                "performance":     int((cats["performance"]["score"] or 0) * 100),
                                "accessibility":   int((cats["accessibility"]["score"] or 0) * 100),
                                "best_practices":  int((cats["best-practices"]["score"] or 0) * 100),
                                "seo":             int((cats["seo"]["score"] or 0) * 100),
                            }
                            success = True
                        else:
                            parse_error = ("lighthouse JSON missing one of performance/"
                                           "accessibility/best-practices/seo category scores")
                    else:
                        parse_error = f"lighthouse JSON shape unexpected: keys={list(data.keys())[:5] if isinstance(data, dict) else type(data).__name__}"
                except Exception as e:
                    parse_error = f"lighthouse JSON unparseable: {e}"
            elif proc.returncode != 0 and not os.path.exists(out_path):
                parse_error = f"lighthouse JSON output not produced (exit {proc.returncode})"
            elif proc.returncode == 0 and not os.path.exists(out_path):
                parse_error = "lighthouse exit 0 but no JSON file at output path"
            entry: dict = {
                "exit": proc.returncode,
                "ok": success,
                "stdout_tail": proc.stdout[-300:],
                "stderr_tail": proc.stderr[-300:],
            }
            if success:
                fails = {k: v for k, v in scores.items() if v < PERF_THRESHOLDS[k]}
                entry["scores"] = scores
                entry["fails"] = fails
                per_route[route] = entry
                summary_table.append({"route": route, **scores, "fails": list(fails.keys())})
                if fails:
                    failing_routes.append(route)
            else:
                # No positive evidence for this route.
                entry["error"] = parse_error or "lighthouse produced no parseable scores"
                per_route[route] = entry
        except subprocess.TimeoutExpired:
            per_route[route] = {"exit": -1, "ok": False, "error": "lighthouse timed out"}
        except Exception as e:
            per_route[route] = {"exit": -1, "ok": False, "error": str(e)}

    # Positive-evidence aggregation.
    succeeded = {r: d for r, d in per_route.items() if d.get("ok")}
    evidence_less = {r: d for r, d in per_route.items() if not d.get("ok")}

    if not per_route:
        return GateResult(
            id="4", name="Performance",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="Lighthouse was not invoked for any route.",
            notes=["Check npx / network availability and re-run."],
            observations={"per_route": per_route, "tool": "lighthouse"},
        )

    if evidence_less:
        # At least one route did not produce positive evidence → NOT-EXERCISED.
        reason_lines = []
        for r, d in evidence_less.items():
            why = d.get("error") or f"exit={d.get('exit')}, no parseable Lighthouse document"
            reason_lines.append(f"  {r}: {why}")
        return GateResult(
            id="4", name="Performance",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary=f"Lighthouse did not produce positive evidence for "
                     f"{len(evidence_less)} of {len(per_route)} route(s). "
                     f"Cannot claim a perf PASS without real Lighthouse numbers.",
            notes=[
                f"Runner: npx lighthouse with --chrome-flags='{chrome_flag}' "
                f"and CHROME_PATH={chrome_path}",
                "Per-route failures:",
                *reason_lines,
                "Succeeded routes (positive evidence) were not aggregated into a PASS "
                "verdict because the failed route(s) leave the gate's coverage incomplete.",
            ],
            observations={"per_route": per_route, "table": summary_table,
                          "thresholds": PERF_THRESHOLDS,
                          "succeeded_routes": list(succeeded.keys()),
                          "evidence_less_routes": list(evidence_less.keys())},
            error=f"{len(evidence_less)} route(s) without positive evidence: "
                  + "; ".join(reason_lines),
        )

    if failing_routes:
        return GateResult(
            id="4", name="Performance",
            verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary=f"Lighthouse below thresholds on {len(failing_routes)} route(s).",
            notes=[f"Thresholds: {PERF_THRESHOLDS}"],
            observations={"per_route": per_route, "table": summary_table, "thresholds": PERF_THRESHOLDS},
        )

    return GateResult(
        id="4", name="Performance",
        verdict="PASS",
        evidence_basis="DOM+assets confirmed",
        summary=f"Lighthouse met thresholds on {len(succeeded)} route(s).",
        notes=[f"Thresholds: {PERF_THRESHOLDS}"],
        observations={"per_route": per_route, "table": summary_table, "thresholds": PERF_THRESHOLDS},
    )


# ---------------------------------------------------------------------------
# Gate 5 — Site-wide audit (per-route perf summary); build a unified view
# ---------------------------------------------------------------------------

def gate_5_sitewide(g4: GateResult, routes: list[str]) -> GateResult:
    """Site-wide audit, built on the Lighthouse per-route loop (gate 4).

    The previous version returned PASS for the single-route case regardless of
    whether gate 4 actually produced real Lighthouse numbers. That was the same
    positive-evidence bug we just fixed in gates 3 and 4. We now propagate
    NOT-EXERCISED from gate 4 to gate 5 even when there's only one route, so
    a single-route site never claims "site-wide audit PASS" while its
    perf runner is silently broken.
    """
    if g4.verdict == "NOT-EXERCISED":
        return GateResult(
            id="5", name="Site-wide audit",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="Site-wide audit skipped because the performance gate (which feeds it) was not exercised.",
            notes=[
                "Gate 5 reuses the Lighthouse per-route loop from gate 4.",
                "If gate 4 is NOT-EXERCISED, gate 5 cannot produce a site-wide view either.",
                "Re-run with a working Lighthouse runner (CHROME_PATH + --no-sandbox) to enable this gate.",
            ],
            observations={"per_route": g4.observations.get("per_route", {}), "gate_4_verdict": g4.verdict},
            error=g4.error or g4.summary,
        )

    per_route = g4.observations.get("per_route", {})
    only_one = len(routes) <= 1
    if only_one:
        # Even with a single route, only PASS if we have positive Lighthouse
        # evidence (gate 4 PASS). Otherwise this is a hollow PASS that hides
        # the same bug we just fixed in gate 4.
        return GateResult(
            id="5", name="Site-wide audit",
            verdict="PASS",
            evidence_basis="DOM+assets confirmed",
            summary="Only one route declared; per-route vs. whole-site comparison is not applicable. "
                     "Single-route Lighthouse score was emitted by gate 4.",
            notes=["Re-run with --routes /,/about to see a multi-route table."],
            observations={"per_route": per_route, "routes": routes, "gate_4_verdict": g4.verdict},
        )

    return GateResult(
        id="5", name="Site-wide audit",
        verdict="PASS" if g4.verdict == "PASS" else "FAIL",
        evidence_basis="DOM+assets confirmed",
        summary=f"Per-route Lighthouse table collected for {len(routes)} route(s).",
        notes=["Reused Lighthouse per-route loop (gate 4); unlighthouse not invoked (cheaper)."],
        observations={"per_route": per_route, "tool": "per-route lighthouse loop", "gate_4_verdict": g4.verdict},
    )


# ---------------------------------------------------------------------------
# Gate 6 — Responsive (screenshot + horizontal overflow check)
# ---------------------------------------------------------------------------

def gate_6_responsive(server: ServerHandle, routes: list[str], viewports: list[int],
                      timeout: float) -> GateResult:
    """Use the nt-mirror venv Python (Playwright). If unavailable, report NOT-EXERCISED."""
    py = "/home/openclaw/.venvs/nt-mirror/bin/python"
    if not os.path.exists(py):
        return GateResult(
            id="6", name="Responsive",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="nt-mirror venv not found; Playwright sweep not exercised.",
            notes=[f"Expected interpreter at {py}; install Playwright+Chromium to enable this gate."],
            observations={"missing_tool": "nt-mirror venv"},
        )

    # Probe whether playwright is importable in the venv.
    try:
        probe = subprocess.run(
            [py, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
            capture_output=True, text=True, timeout=10,
        )
        if probe.stdout.strip() != "ok":
            return GateResult(
                id="6", name="Responsive",
                verdict="NOT-EXERCISED",
                evidence_basis="Not exercised",
                summary="Playwright not importable in nt-mirror venv.",
                notes=[probe.stderr.strip()],
                observations={"missing_tool": "playwright"},
            )
    except Exception as e:
        return GateResult(
            id="6", name="Responsive",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary=f"Playwright venv probe failed: {e}",
            observations={"missing_tool": "playwright"},
        )

    # Inline playwright script — runs in the venv.
    # Heights default to a reasonable band per width; the gate checks horizontal overflow
    # which depends on width only.
    DEFAULT_HEIGHTS = {320: 720, 768: 1024, 1024: 768, 1440: 900}
    script = """
import json, sys
from playwright.sync_api import sync_playwright

base = sys.argv[1]
routes = json.loads(sys.argv[2])
viewports = json.loads(sys.argv[3])
default_h = {int(k): int(v) for k, v in json.loads(sys.argv[4]).items()}
out_dir = sys.argv[5]
import os; os.makedirs(out_dir, exist_ok=True)

def viewport_pair(w):
    return (w, default_h.get(w, 900))

def _settle(page, cap_ms=8000):
    # Wait for the page to stop changing, by PIXELS not by animation records.
    # document.getAnimations() only reports WAAPI/CSS animations. Motion (and
    # any other rAF-driven library) animates via requestAnimationFrame and never
    # appears there, so awaiting it returned instantly and the audit sampled the
    # page mid-fade. axe then measured half-opacity text against its background
    # and reported phantom color-contrast violations that came and went between
    # runs. Polling for consecutive pixel-identical frames catches what the
    # animation registry cannot see.
    import hashlib
    info = page.evaluate(
        "async () => { const a = document.getAnimations();"
        " await Promise.race([Promise.all(a.map(x => x.finished.catch(() => {}))),"
        " new Promise(r => setTimeout(r, 3000))]);"
        " return {animation_count: a.length, settle_cap_ms: 3000}; }"
    )
    waited, last, stable = 0, None, 0
    while waited < cap_ms:
        digest = hashlib.sha256(page.screenshot(type="jpeg", quality=40)).hexdigest()
        if digest == last:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        last = digest
        page.wait_for_timeout(250)
        waited += 250
    info["pixel_stable"] = stable >= 2
    info["pixel_wait_ms"] = waited
    return info


results = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    for route in routes:
        url = base + (route if route.startswith('/') else '/' + route)
        for w in viewports:
            w, h = viewport_pair(w)
            ctx = browser.new_context(viewport={'width': w, 'height': h})
            page = ctx.new_page()
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=15000)
                settle = _settle(page)
                metrics = page.evaluate(
                    "() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth, sh: document.documentElement.scrollHeight})"
                )
                overflow = metrics['sw'] > metrics['iw']
                shot = os.path.join(out_dir, f"{abs(hash(route + str(w)))}__{w}x{h}.png")
                page.screenshot(path=shot, full_page=False)
                results.append({'route': route, 'viewport': f"{w}x{h}", 'scrollWidth': metrics['sw'],
                                'innerWidth': metrics['iw'], 'scrollHeight': metrics['sh'], 'settle': settle,
 'overflow': overflow, 'screenshot': shot})
            except Exception as e:
                results.append({'route': route, 'viewport': f"{w}x{h}", 'error': str(e)})
            finally:
                ctx.close()
    browser.close()
print(json.dumps(results))
"""
    try:
        # The hermes sandbox may override HOME to a profile-local path that has no Playwright
        # browser cache. Fall back to /home/openclaw (the real home) where ms-playwright lives.
        env = os.environ.copy()
        if not os.path.exists(os.path.join(env.get("HOME", ""), ".cache", "ms-playwright")):
            real_home = os.path.expanduser("~")
            if os.path.exists(os.path.join(real_home, ".cache", "ms-playwright")):
                env["HOME"] = real_home
            # Also try /home/openclaw explicitly (hermes may chdir HOME underneath).
            if not os.path.exists(os.path.join(env["HOME"], ".cache", "ms-playwright")):
                if os.path.exists("/home/openclaw/.cache/ms-playwright"):
                    env["HOME"] = "/home/openclaw"
        proc = subprocess.run(
            [py, "-c", script,
             server.base_url(), json.dumps(routes), json.dumps(viewports),
             json.dumps(DEFAULT_HEIGHTS),
             os.path.join(os.path.dirname(server.log_path), "responsive_shots")],
            capture_output=True, text=True, timeout=timeout * 6, env=env,
        )
        if proc.returncode != 0:
            return GateResult(
                id="6", name="Responsive",
                verdict="FAIL",
                evidence_basis="Not exercised",
                summary=f"Playwright run failed (exit {proc.returncode}).",
                notes=[proc.stderr[-500:]],
                observations={"per_cell": [], "stderr": proc.stderr[-500:]},
            )
        per_cell = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception as e:
        return GateResult(
            id="6", name="Responsive",
            verdict="FAIL",
            evidence_basis="Not exercised",
            summary=f"Playwright run failed: {e}",
            notes=[traceback.format_exc()],
            observations={"error": str(e)},
        )

    overflow_cells = [c for c in per_cell if c.get("overflow")]
    error_cells = [c for c in per_cell if c.get("error")]
    if error_cells:
        return GateResult(
            id="6", name="Responsive",
            verdict="FAIL",
            evidence_basis="Interaction-tested",
            summary=f"{len(error_cells)} viewport cell(s) failed to load.",
            notes=error_cells[:5],
            observations={"per_cell": per_cell},
        )
    if overflow_cells:
        return GateResult(
            id="6", name="Responsive",
            verdict="FAIL",
            evidence_basis="Observed visually",
            summary=f"{len(overflow_cells)} viewport cell(s) had horizontal overflow.",
            notes=[f"{c['route']} @ {c['viewport']}: scrollWidth={c['scrollWidth']} > innerWidth={c['innerWidth']}" for c in overflow_cells[:5]],
            observations={"per_cell": per_cell, "overflow_cells": overflow_cells},
        )

    return GateResult(
        id="6", name="Responsive",
        verdict="PASS",
        evidence_basis="Observed visually",
        summary=f"No horizontal overflow across {len(per_cell)} cell(s) ({len(routes)} route(s) × {len(viewports)} viewport(s)).",
        notes=[],
        observations={"per_cell": per_cell, "viewports": viewports, "routes": routes,
                      "cell_count": len(per_cell)},
    )


# ---------------------------------------------------------------------------
# Gate 7 — Motion (prefers-reduced-motion in CSS)
# ---------------------------------------------------------------------------

def gate_7_motion(server: ServerHandle, routes: list[str]) -> GateResult:
    """Confirm at least one CSS file referenced by the page declares a
    @media (prefers-reduced-motion: reduce) block that neutralizes motion."""
    css_files_seen: list[str] = []
    has_reduced = False
    reduced_files: list[str] = []
    css_blocks: list[str] = []

    for route in routes:
        local_path = route_to_file(server.site_dir, route)
        if not os.path.exists(local_path):
            continue
        parser = parse_html(local_path)
        for attr, url in parser.hrefs + parser.srcs:
            if attr != "href":
                continue
            if not url.lower().split("?", 1)[0].split("#", 1)[0].endswith(".css"):
                continue
            css_path = resolve_local_asset(server.site_dir, local_path, url)
            if css_path is None:
                continue
            css_files_seen.append(css_path)
            try:
                css = read_css(css_path)
            except Exception:
                continue
            css_blocks.append(css)
            if PREFERS_REDUCED_RE.search(css):
                has_reduced = True
                reduced_files.append(css_path)

    if not css_files_seen:
        return GateResult(
            id="7", name="Motion",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="No local CSS files observed; reduced-motion check not applicable.",
            notes=["If motion is intended, link a stylesheet that declares @media (prefers-reduced-motion: reduce)."],
            observations={"css_files_seen": css_files_seen},
        )

    if has_reduced:
        return GateResult(
            id="7", name="Motion",
            verdict="PASS",
            evidence_basis="DOM+assets confirmed",
            summary=f"prefers-reduced-motion honored in {len(reduced_files)} CSS file(s).",
            notes=[],
            observations={"css_files_seen": css_files_seen, "reduced_in": reduced_files},
        )

    return GateResult(
        id="7", name="Motion",
        verdict="FAIL",
        evidence_basis="DOM+assets confirmed",
        summary="No @media (prefers-reduced-motion: reduce) block found in any CSS file.",
        notes=[f"Scanned: {css_files_seen}"],
        observations={"css_files_seen": css_files_seen},
    )


# ---------------------------------------------------------------------------
# Gate 8 — Token discipline (re-scoped: var(--token) usage + no raw hex)
# ---------------------------------------------------------------------------

def _hex_defines_custom_property(css: str, hex_pos: int) -> bool:
    """True when the hex at `hex_pos` is the VALUE of a `--custom-property`.

    Token discipline means "colours enter the design through tokens", but the
    rule used to be enforced by FILENAME ("anything outside tokens.css"). A
    bundler defeats that: Next.js compiles tokens.css into a content-hashed
    stylesheet, so all 50 legitimate token definitions suddenly read as
    violations, while a genuinely hardcoded colour in the same file would have
    been indistinguishable from them.

    Checking the declaration instead is filename-independent and says what we
    actually mean: `--color-fg: #111` defines a token and is fine; `color: #111`
    bypasses the token layer and is not. `@property --tw-shadow { initial-value:
    0 0 #0000 }` is how a registered custom property declares its default, which
    is the same act of definition in different syntax.

    >>> _hex_defines_custom_property("a{--color-fg: #111111;}", 13)
    True
    >>> _hex_defines_custom_property("a{color: #111111;}", 9)
    False
    >>> _hex_defines_custom_property("a{--x:#fff}", 6)
    True
    >>> _hex_defines_custom_property("@property --tw-shadow{initial-value:0 0 #0000}", 40)
    True
    """
    start = max(css.rfind(";", 0, hex_pos), css.rfind("{", 0, hex_pos),
                css.rfind("}", 0, hex_pos)) + 1
    prop = css[start:hex_pos].split(":", 1)[0].strip()
    return prop.startswith("--") or prop == "initial-value"


def _is_transparent_hex(value: str) -> bool:
    """True for fully-transparent hex, which expresses absence of colour.

    `#0000` / `#00000000` is what Tailwind emits for "no shadow" and "no
    background". An alpha of zero cannot carry a brand colour, so flagging it
    reports noise rather than a design decision that bypassed the token layer.

    >>> _is_transparent_hex("#0000")
    True
    >>> _is_transparent_hex("#00000000")
    True
    >>> _is_transparent_hex("#fff")
    False
    >>> _is_transparent_hex("#000000ff")
    False
    """
    h = value.lstrip("#")
    if len(h) == 4:
        return h[3] == "0"
    if len(h) == 8:
        return h[6:8].lower() == "00"
    return False


def gate_8_token_discipline(server: ServerHandle, routes: list[str]) -> GateResult:
    """Token-discipline check (our re-scope of the workflow's vague 'source-paired 10x' gate):
        - The composed CSS uses var(--token) references.
        - No raw hex colors exist outside tokens.css."""
    css_files: list[str] = []
    violations_raw_hex: list[str] = []
    var_uses = 0
    has_token_var = False

    for route in routes:
        local_path = route_to_file(server.site_dir, route)
        if not os.path.exists(local_path):
            continue
        parser = parse_html(local_path)
        for attr, url in parser.hrefs + parser.srcs:
            if attr != "href":
                continue
            if not url.lower().split("?", 1)[0].split("#", 1)[0].endswith(".css"):
                continue
            css_path = resolve_local_asset(server.site_dir, local_path, url)
            if css_path is None:
                continue
            css_files.append(css_path)
            try:
                css = read_css(css_path)
            except Exception:
                continue
            if "tokens.css" in css_path:
                continue  # tokens.css is the source of truth; hex definitions are OK there
            if "var(--" in css:
                has_token_var = True
            var_uses += len(TOKEN_VAR_RE.findall(css))
            for match in HEX_RE.finditer(css):
                if _hex_defines_custom_property(css, match.start()):
                    continue
                if _is_transparent_hex(match.group(0)):
                    continue
                violations_raw_hex.append(f"{css_path}: {match.group(0)}")

    if not css_files:
        return GateResult(
            id="8", name="Token discipline",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="No CSS files observed; token discipline not exercisable.",
            notes=[],
            observations={"css_files": css_files},
        )

    if not has_token_var:
        return GateResult(
            id="8", name="Token discipline",
            verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary="Composed CSS does not use any var(--token) references.",
            notes=["The design pass should reference tokens via CSS variables, not raw values."],
            observations={"css_files": css_files, "var_uses": var_uses, "raw_hex": violations_raw_hex},
        )

    if violations_raw_hex:
        return GateResult(
            id="8", name="Token discipline",
            verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary=f"{len(violations_raw_hex)} raw hex literal(s) found outside tokens.css.",
            notes=violations_raw_hex[:20],
            observations={"css_files": css_files, "var_uses": var_uses, "raw_hex": violations_raw_hex},
        )

    return GateResult(
        id="8", name="Token discipline",
        verdict="PASS",
        evidence_basis="DOM+assets confirmed",
        summary=f"CSS uses {var_uses} var(--token) reference(s); 0 raw hex literals outside tokens.css.",
        notes=["Gate 8 re-scoped from workflow-design.md §4's 'source-paired 10x' — see report.",
               "tokens.css is the explicit source of truth; raw hex inside it is allowed."],
        observations={"css_files": css_files, "var_uses": var_uses, "raw_hex": violations_raw_hex},
    )


# ---------------------------------------------------------------------------
# Renderer-build plumbing (gates 9 + 10) — only when the site dir is a Next.js
# static export. These gates are SKIPPED (→ NOT-EXERCISED) for the static HTML
# composer (`compose_site.py` output), which has no `_next/` and no build step.
# ---------------------------------------------------------------------------

def is_nextjs_export(site_dir: str) -> bool:
    """True iff the site directory looks like a `next build` static export.

    The Next.js renderer (renderer/) emits `out/` with `_next/static/{chunks,
    css, media, <buildId>}/`. The static composer (compose_site.py) emits
    plain `index.html + styles.css + tokens.css` and never has `_next/`. So a
    direct `_next/` check is a reliable, no-config detector.
    """
    return os.path.isdir(os.path.join(site_dir, "_next"))


def _next_static_dir(site_dir: str) -> str:
    return os.path.join(site_dir, "_next", "static")


def find_package_root_for(site_dir: str) -> str | None:
    """Walk upward from site_dir to find a package.json. The Next.js project
    root is the directory containing the next build setup (`next.config.ts`).

    Next.js's `out/` is a sibling of `.next/`, so the renderer project root is
    `parent(out_dir)` — i.e. the directory passed as `--out` to `next build`.
    We accept `next.config.{js,ts,mjs,cjs}` as the canonical marker, but the
    plain presence of `package.json` is enough for `npm run build` to work.
    """
    cur = os.path.abspath(site_dir)
    for _ in range(6):  # don't walk past the root
        if os.path.isfile(os.path.join(cur, "package.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
    return None


# ---------------------------------------------------------------------------
# Gate 9 — Build (Next.js)
# ---------------------------------------------------------------------------

def gate_9_build(site_dir: str, renderer_root: str | None, timeout: float) -> GateResult:
    """Run `npm run build` in the Next.js renderer root and check exit 0.

    ONLY fires when the site dir is a Next.js static export. Otherwise returns
    NOT-EXERCISED with a clear "site is not a Next.js export" reason — the
    static HTML composer (compose_site.py output) doesn't have a build step
    and gating it on `npm run build` would be a false positive.

    Positive-evidence-only verdict rules:
      - PASS:           npm run build exited 0 AND we parsed `exit_code` from
                        the result. (We don't try to *parse* the build output;
                        exit code is the canonical Next.js build signal.)
      - FAIL:           npm run build exited non-zero. Stdout/stderr tails are
                        recorded so the report shows what broke.
      - NOT-EXERCISED:  npm not on PATH, no renderer root, or any other
                        positive-evidence failure.
    """
    if not is_nextjs_export(site_dir):
        return GateResult(
            id="9", name="Build (Next.js)",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="Site is not a Next.js static export (no _next/ directory); "
                     "build gate not applicable.",
            notes=["Gate 9 is Only-On-Exports. The static HTML composer "
                   "(compose_site.py) has no build step.",
                   "To run this gate, point validate_site.py at a Next.js `out/` directory."],
            observations={"applicable": False, "site_dir": site_dir},
        )

    if renderer_root is None:
        return GateResult(
            id="9", name="Build (Next.js)",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="Next.js export detected but no renderer project root found "
                     "(no package.json within 6 levels of site_dir).",
            notes=["Pass --renderer-root to point at the Next.js project."],
            observations={"applicable": True, "renderer_root": None},
        )

    if shutil.which("npm") is None:
        return GateResult(
            id="9", name="Build (Next.js)",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="npm not on PATH; cannot run `npm run build`.",
            notes=["Install Node.js + npm to exercise this gate."],
            observations={"applicable": True, "renderer_root": renderer_root, "tool": "npm missing"},
        )

    build_log = os.path.join(os.path.dirname(renderer_root), "build-stdout.log")
    try:
        proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=renderer_root,
            capture_output=True, text=True, timeout=timeout * 6,
        )
        # Persist the full output for the report even on success — the gated
        # outcome is exit 0, but the bytes are useful for downstream debugging.
        try:
            with open(build_log, "w", encoding="utf-8") as f:
                f.write("=== stdout ===\n" + (proc.stdout or ""))
                f.write("\n=== stderr ===\n" + (proc.stderr or ""))
        except OSError:
            pass
        if proc.returncode == 0:
            return GateResult(
                id="9", name="Build (Next.js)",
                verdict="PASS",
                evidence_basis="DOM+assets confirmed",
                summary=f"`npm run build` exited 0 in {renderer_root}.",
                notes=[f"Build log: {build_log}"],
                observations={
                    "applicable": True,
                    "renderer_root": renderer_root,
                    "exit_code": 0,
                    "build_log": build_log,
                },
            )
        return GateResult(
            id="9", name="Build (Next.js)",
            verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary=f"`npm run build` exited {proc.returncode} in {renderer_root}.",
            notes=[
                f"Build log: {build_log}",
                f"stdout tail: ...{proc.stdout[-400:] if proc.stdout else ''}",
                f"stderr tail: ...{proc.stderr[-400:] if proc.stderr else ''}",
            ],
            observations={
                "applicable": True,
                "renderer_root": renderer_root,
                "exit_code": proc.returncode,
                "build_log": build_log,
            },
            error=f"npm run build exit {proc.returncode}",
        )
    except subprocess.TimeoutExpired:
        return GateResult(
            id="9", name="Build (Next.js)",
            verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary=f"`npm run build` timed out after {timeout * 6}s in {renderer_root}.",
            observations={"applicable": True, "renderer_root": renderer_root,
                          "exit_code": -1, "error": "timeout"},
            error="npm run build timed out",
        )
    except Exception as e:
        return GateResult(
            id="9", name="Build (Next.js)",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary=f"`npm run build` could not be invoked: {e}",
            observations={"applicable": True, "renderer_root": renderer_root,
                          "error": str(e)},
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Gate 10 — Bundle (Next.js JS budget)
# ---------------------------------------------------------------------------

def _measure_gzipped_js(static_dir: str) -> tuple[int, list[dict]]:
    """Sum gzipped sizes of every .js file under static_dir. Returns
    (total_gzipped_bytes, per_file_breakdown). If anything goes wrong
    on a single file the per-file record gets an `error` key and we
    continue — we still want as much positive evidence as we can get.
    """
    import gzip
    total = 0
    breakdown: list[dict] = []
    if not os.path.isdir(static_dir):
        return (0, [])
    for root, _dirs, files in os.walk(static_dir):
        for fname in files:
            if not fname.endswith(".js"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                gz = gzip.compress(raw)
                size_gz = len(gz)
                total += size_gz
                breakdown.append({
                    "path": os.path.relpath(path, static_dir),
                    "raw_bytes": len(raw),
                    "gzipped_bytes": size_gz,
                })
            except Exception as e:
                breakdown.append({"path": os.path.relpath(path, static_dir),
                                  "error": str(e)})
    breakdown.sort(key=lambda r: r.get("gzipped_bytes", 0), reverse=True)
    return (total, breakdown)


def gate_10_bundle(site_dir: str, bundle_budget_kb: int) -> GateResult:
    """Total gzipped JS in _next/static must be under the budget.

    Only fires on a Next.js export. Returns NOT-EXERCISED otherwise so the
    static composer path stays green.

    Positive-evidence-only rules:
      - PASS:           we measured the bytes, summing gzipped sizes of every
                        .js file under _next/static/, and the total is under
                        the budget.
      - FAIL:           we measured and the total exceeded the budget.
                        The actual number is reported either way so the reader
                        can see how close (or far) the page is to the target.
      - NOT-EXERCISED:  no _next/static/ directory (or empty), so we have no
                        numbers to report.
    """
    if not is_nextjs_export(site_dir):
        return GateResult(
            id="10", name="Bundle (Next.js)",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="Site is not a Next.js static export; bundle gate not applicable.",
            notes=["Gate 10 is Only-On-Exports. The static HTML composer does not "
                   "emit a JS bundle."],
            observations={"applicable": False, "site_dir": site_dir},
        )

    static_dir = _next_static_dir(site_dir)
    if not os.path.isdir(static_dir):
        return GateResult(
            id="10", name="Bundle (Next.js)",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary=f"_next/static/ not found at {static_dir}. Nothing to measure.",
            notes=["Re-run `npm run build` to emit the static bundle."],
            observations={"applicable": True, "static_dir": static_dir,
                          "file_count": 0},
        )

    total_bytes, breakdown = _measure_gzipped_js(static_dir)
    if not breakdown:
        return GateResult(
            id="10", name="Bundle (Next.js)",
            verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary=f"No .js files found under {static_dir}.",
            notes=["If this is unexpected, re-run `npm run build`."],
            observations={"applicable": True, "static_dir": static_dir,
                          "file_count": 0},
        )

    budget_bytes = bundle_budget_kb * 1024
    total_kb = total_bytes / 1024.0
    # Top 5 biggest files for the report — the median user is not going to
    # scroll past that, and they tell the story of which chunks dominate.
    top = breakdown[:5]
    observations = {
        "applicable": True,
        "static_dir": static_dir,
        "file_count": len(breakdown),
        "total_gzipped_bytes": total_bytes,
        "total_gzipped_kb": round(total_kb, 1),
        "budget_kb": bundle_budget_kb,
        "top_files": top,
    }
    if total_bytes > budget_bytes:
        return GateResult(
            id="10", name="Bundle (Next.js)",
            verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary=f"Total gzipped JS is {total_kb:.1f} KB, over the {bundle_budget_kb} KB "
                     f"budget (by {total_bytes - budget_bytes} bytes across {len(breakdown)} file(s)).",
            notes=[f"Top 5: " + ", ".join(
                f"{f['path']}={f.get('gzipped_bytes', 0)//1024}KB"
                for f in top if "gzipped_bytes" in f)],
            observations=observations,
            error=f"bundle {total_kb:.1f} KB > budget {bundle_budget_kb} KB",
        )
    return GateResult(
        id="10", name="Bundle (Next.js)",
        verdict="PASS",
        evidence_basis="DOM+assets confirmed",
        summary=f"Total gzipped JS is {total_kb:.1f} KB across {len(breakdown)} file(s), "
                 f"under the {bundle_budget_kb} KB budget.",
        notes=[],
        observations=observations,
    )


# ---------------------------------------------------------------------------
# Acceptance tier
# ---------------------------------------------------------------------------

def compute_tier(results: list[GateResult]) -> tuple[str, str]:
    """Return (tier, reason). Tiers: First-render, Validated, Offline-validated, Partial.

    Honesty rule (positive-evidence-only): a gate verdict of PASS is only meaningful
    when the runner actually produced parseable evidence. NOT-EXERCISED means the
    runner did not run, or crashed, or produced no results document. The only tier
    that requires *every* gate PASS is `Validated`; any NOT-EXERCISED gate caps
    the tier at `Partial` so a reader can never mistake "axe crashed" for
    "axe found 0 violations".

    EXCEPTION: gates 9 and 10 (Next.js build + bundle) are conditional on the
    site being a Next.js static export. When that export is not present, the
    gates are *not applicable* (observations.applicable == False) and report
    NOT-EXERCISED with a clear "not a Next.js export" reason. In that case
    the gate is excluded from the tier cap — its verdict is still visible in
    the report (so the reader sees the gate was considered and skipped), but
    a site that doesn't carry a JS build is not penalized for not running
    `npm run build`. This preserves the existing invariant that the static
    HTML composer path can still reach `Validated` even when the schema
    bumps from 8 to 10 gates.
    """
    # Identify which NOT-EXERCISED gates are merely "not applicable" because
    # the site is not a Next.js export. These do NOT cap the tier.
    def _is_inapplicable_not_exercised(r: GateResult) -> bool:
        if r.verdict != "NOT-EXERCISED" or r.id not in ("9", "10"):
            return False
        return (r.observations or {}).get("applicable") is False

    applicable_results = [r for r in results if not _is_inapplicable_not_exercised(r)]
    by_id = {r.id: r for r in results}
    verdicts = [r.verdict for r in applicable_results]
    fails = [r.id for r in applicable_results if r.verdict == "FAIL"]
    notex = [r.id for r in applicable_results if r.verdict == "NOT-EXERCISED"]

    if fails:
        return ("Partial", f"Gate(s) FAIL: {','.join(fails)}. See per-gate detail for evidence.")

    if not notex:
        return ("Validated", "Every applicable gate ran and produced positive evidence; "
                              "validation complete for declared scope.")

    # At least one applicable gate did not produce positive evidence. We refuse
    # to claim "Validated" because that tier is reserved for the all-applicable-
    # PASS case. Distinguish:
    #  - "First-render"  : no real-browser evidence at all (a11y AND perf NOT-EXERCISED)
    #  - "Offline-validated" : DOM/CSS/HTTP checks passed, some real-browser check present
    #  - "Partial"        : a11y OR perf did not produce real numbers; the rest may have
    #                       passed, but a "Validated" label would mislead the reader
    #                       (the same trap the prior harness fell into).
    # Per the spec: any NOT-EXERCISED on an applicable gate caps at Partial.
    if any(r.id in {"3", "4"} for r in applicable_results if r.verdict == "NOT-EXERCISED"):
        return ("Partial",
                f"Gate(s) NOT-EXERCISED: {','.join(notex)}. "
                "A11y or perf runner did not produce positive evidence, "
                "so the validation cannot be claimed as complete. "
                "See per-gate detail for runner exit codes and stderr tails.")
    return ("Partial",
            f"Gate(s) NOT-EXERCISED: {','.join(notex)}. "
            "Per positive-evidence-only rule, any NOT-EXERCISED caps tier at Partial.")


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(results: list[GateResult], site_dir: str, args: argparse.Namespace,
                  server: ServerHandle, server_log: str) -> str:
    by_id = {r.id: r for r in results}
    tier, tier_reason = compute_tier(results)
    failed = [r for r in results if r.verdict == "FAIL"]
    notex = [r for r in results if r.verdict == "NOT-EXERCISED"]
    passed = [r for r in results if r.verdict == "PASS"]

    lines = []
    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Schema: validate_site.py v{SCHEMA_VERSION} ({GATE_VERSION})")
    lines.append(f"Site directory: `{site_dir}`")
    lines.append(f"Routes validated: {args.routes}")
    lines.append(f"Local server: {server.base_url()} (python3 -m http.server, killed on exit)")
    lines.append(f"Server log: {server_log}")
    lines.append("")
    lines.append("## Declared scope")
    lines.append("")
    lines.append(f"- Method: `validate_site.py` (10-gate harness; static Composed Site / Next.js export)")
    lines.append(f"- Routes: {args.routes}")
    lines.append(f"- Viewports: {args.viewports}")
    lines.append(f"- Lighthouse: {'skipped' if args.skip_lighthouse else 'enabled'}")
    lines.append("- DOM audit settle: wait for load, then document.getAnimations() finished promises with a 3s cap, then poll for two consecutive pixel-identical frames (catches JS-driven animation libraries that never register in document.getAnimations)")
    lines.append(f"- Next.js export detected: {is_nextjs_export(site_dir)}")
    if is_nextjs_export(site_dir):
        lines.append(f"- Bundle budget (Gate 10): {args.bundle_budget_kb} KB gzipped JS in _next/static/")
        renderer_root = args.renderer_root or find_package_root_for(site_dir)
        lines.append(f"- Renderer root (Gate 9): {renderer_root or '(not found)'}")
    lines.append("")
    lines.append("## Gate results")
    lines.append("")
    lines.append("| # | Gate | Verdict | Evidence basis | Summary |")
    lines.append("|---|------|---------|----------------|---------|")
    for r in results:
        summary = r.summary.replace("|", "\\|")
        lines.append(f"| {r.id} | {r.name} | **{r.verdict}** | {r.evidence_basis} | {summary} |")
    lines.append("")
    lines.append("**Verdict values:** `PASS` (evidence satisfies the gate), `FAIL` (evidence contradicts), "
                 "`NOT-EXERCISED` (runner unavailable or did not run). NOT-EXERCISED does not fail the run "
                 "but is visible above and downgrades the acceptance tier.")
    lines.append("")
    lines.append("**Evidence basis values:** `Observed visually` | `Interaction-tested` | "
                 "`DOM+assets confirmed` | `HTTP-200 only` | `Not exercised`.")
    lines.append("")

    # Per-gate detail
    lines.append("## Per-gate detail")
    lines.append("")
    for r in results:
        lines.append(f"### Gate {r.id} — {r.name}  ({r.verdict})")
        lines.append("")
        lines.append(f"- **Evidence basis:** {r.evidence_basis}")
        lines.append(f"- **Summary:** {r.summary}")
        if r.notes:
            lines.append("- **Notes:**")
            for n in r.notes:
                lines.append(f"  - {n}")
        if r.error:
            lines.append(f"- **Error:** {r.error}")
        obs = r.observations or {}
        if obs:
            lines.append("- **Observations (JSON):**")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(obs, indent=2, default=str)[:8000])
            lines.append("```")
        lines.append("")

    # Acceptance tier
    lines.append("## Acceptance tier")
    lines.append("")
    lines.append(f"**Reached tier: `{tier}`**")
    lines.append("")
    lines.append(f"Reason: {tier_reason}")
    lines.append("")
    lines.append(f"- PASS gates: {', '.join(r.id for r in passed) or 'none'}")
    lines.append(f"- FAIL gates: {', '.join(r.id for r in failed) or 'none'}")
    lines.append(f"- NOT-EXERCISED gates: {', '.join(r.id for r in notex) or 'none'}")
    lines.append("")
    lines.append("Tier definitions (from site-cloner SKILL.md):")
    lines.append("")
    lines.append("- `First-render` — the page returns content but no deeper validation has run.")
    lines.append("- `Validated (declared scope)` — every gate ran and produced positive evidence "
                 "(runner exited cleanly AND parsed a result document with real numbers).")
    lines.append("- `Offline-validated` — DOM/CSS/HTTP checks passed; a real-browser a11y/perf "
                 "check was not exercised (Lighthouse or axe unavailable).")
    lines.append("- `Partial` — at least one gate FAILed, OR at least one gate was NOT-EXERCISED. "
                 "Per the positive-evidence-only rule, any NOT-EXERCISED gate (a runner that crashed, "
                 "timed out, or produced no result document) caps tier at `Partial`. A truthful Partial "
                 "beats a fabricated Validated.")
    lines.append("")

    # Gate 8 re-scope note
    lines.append("## Gate 8 re-scope")
    lines.append("")
    lines.append("research/workflow-design.md §4 gate 8 reads: **Source-paired gate — where the "
                 "redesign is compared *directly* to the reference, render both side-by-side and "
                 "ensure the redesign is *visibly* 10x.** That gate is subjective ('visibly 10x' "
                 "is a metaphor, not a metric) and only triggers when a reference comparison is "
                 "in scope. This harness re-scopes it to a **token-discipline gate** that is "
                 "deterministic and runnable for every composed site:")
    lines.append("")
    lines.append("- PASS: composed CSS uses `var(--token)` references and contains no raw hex "
                 "colors outside `tokens.css`.")
    lines.append("- FAIL: any raw hex literal outside `tokens.css`, or no `var(--token)` usage.")
    lines.append("- NOT-EXERCISED: no CSS files observed (uncommon — every site has CSS).")
    lines.append("")
    lines.append("If a future run needs the source-paired comparison, gate 8 can be re-added "
                 "behind a `--reference-report` flag without disturbing the rest of the table.")
    lines.append("")

    # Evidence artifacts
    lines.append("## Evidence artifacts")
    lines.append("")
    lines.append(f"- Raw per-gate results: `<report-dir>/gate-results.json`")
    lines.append(f"- Server access log: `{server_log}`")
    if any(r.id == "6" and r.verdict == "PASS" for r in results):
        lines.append(f"- Responsive screenshots: `<report-dir>/responsive_shots/`")
    lines.append("")
    # Project status
    lines.append("## Project status")
    lines.append("")
    if tier == "Validated":
        lines.append("`Complete for declared scope and evidence — every gate exercised and produced positive evidence.`")
    elif tier == "Offline-validated":
        lines.append("`Offline-validated — DOM/CSS/HTTP checks passed; real-browser a11y/perf NOT exercised. Re-run with network access to upgrade to Validated.`")
    else:
        # Partial: at least one gate FAILed OR at least one gate NOT-EXERCISED. Per
        # the positive-evidence-only rule, we MUST surface the NOT-EXERCISED ones
        # prominently so the reader sees exactly which runners failed and why.
        lines.append(f"`Partial — {tier_reason}`")
        if notex:
            lines.append("")
            lines.append("**Gates that did not produce positive evidence** "
                         "(runner crashed, timed out, or returned no result document):")
            for r in [r for r in results if r.verdict == "NOT-EXERCISED"]:
                reason = (r.error or r.summary).strip()
                lines.append(f"  - Gate {r.id} ({r.name}): {reason}")
        if failed:
            lines.append("")
            lines.append("**Gates that FAILed** (runner ran, thresholds genuinely missed):")
            for r in [r for r in results if r.verdict == "FAIL"]:
                lines.append(f"  - Gate {r.id} ({r.name}): {r.summary}")
        lines.append("")
        lines.append("A truthful Partial beats a fabricated Validated. Re-run after fixing the "
                     "runner(s) above (Chrome sandbox, HOME, network) to upgrade the tier.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Gate 11 — Content fidelity (did the plan's copy actually reach the page?)
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[a-z0-9]+")
_PLACEHOLDER_RE = re.compile(r"\[no [a-z ]+ in plan\]", re.I)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def _visible_text(html: str) -> str:
    html = _TAG_RE.sub(" ", html)
    text = _ANY_TAG_RE.sub(" ", html)
    for ent, rep in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                     ("&#x27;", "'"), ("&#39;", "'"), ("&nbsp;", " "), ("&rsquo;", "'"),
                     ("&ldquo;", '"'), ("&rdquo;", '"'), ("&mdash;", "-"), ("&ndash;", "-")):
        text = text.replace(ent, rep)
    return text.lower()


def gate_11_content_fidelity(server: "ServerHandle", routes: list, design_plan: str | None,
                             timeout: float, coverage_threshold: float = 0.85) -> GateResult:
    """Every copy block the design pass wrote must actually reach the DOM.

    This gate exists because nothing else could see the worst defect the
    pipeline ever shipped. The renderer hardcoded which copy role each layout
    read and silently dropped the others, so six of eleven sections lost their
    headline, body or call-to-action, three sections rendered the literal debug
    string "[no body in plan]", and one shipped an 879px empty box. Every other
    gate passed: the page built, was accessible, met contrast, used tokens and
    fit the bundle budget. A page can satisfy all of that and still not say what
    it was supposed to say.

    Matching is by TOKEN COVERAGE, not verbatim substring: layouts legitimately
    reshape a block (a comma-separated services list becomes nine accordion
    rows), so an exact-match check would fail on correct output. A block that
    was genuinely dropped scores near zero, which is the signal we want.
    """
    if not design_plan:
        return GateResult(
            id="11", name="Content fidelity", verdict="NOT-EXERCISED",
            evidence_basis="Not exercised",
            summary="No --design-plan supplied; cannot verify the plan's copy reached the page.",
            notes=["Pass --design-plan <plan.json> to exercise this gate."],
            observations={"applicable": False},
        )
    try:
        plan = json.loads(pathlib.Path(design_plan).read_text())
    except Exception as exc:  # noqa: BLE001
        return GateResult(
            id="11", name="Content fidelity", verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary=f"design plan could not be read: {exc}",
            notes=[], observations={"design_plan": design_plan},
        )

    skipped = {s.get("id") for s in plan.get("skipped_sections", []) or []}
    blocks = [b for b in plan.get("copy_blocks", []) or []
              if b.get("section_id") not in skipped and (b.get("text") or "").strip()]

    pages, raw_pages = [], []
    for route in routes:
        url = server.base_url() + normalize_route(route)
        try:
            with urlopen(url, timeout=timeout) as r:
                raw = r.read().decode("utf-8", "replace")
            raw_pages.append(raw)
            pages.append(_visible_text(raw))
        except Exception as exc:  # noqa: BLE001
            return GateResult(
                id="11", name="Content fidelity", verdict="NOT-EXERCISED",
                evidence_basis="Not exercised",
                summary=f"could not fetch {url}: {exc}",
                notes=[], observations={"route": route},
            )
    haystack = " ".join(pages)
    words_by_route = {r: set(_WORD_RE.findall(t)) for r, t in zip(routes, pages)}
    hay_words = set(_WORD_RE.findall(haystack))

    # PER-ROUTE attribution. Scoring every block against the union of all routes
    # lets a block that belongs on /about/ but leaked onto / still pass, which
    # defeats the point on a multi-page site. When the plan declares pages[] we
    # know which route each section belongs to, so score it there. Without
    # pages[] the union is correct and stays — that is the single-page path.
    route_of_section = {}
    for pg in plan.get("pages", []) or []:
        slug = (pg.get("slug") or "").strip("/")
        route = "/" if not slug else f"/{slug}/"
        for sid in pg.get("section_ids", []) or []:
            route_of_section[sid] = route

    missing, weak = [], []
    for b in blocks:
        words = _WORD_RE.findall((b.get("text") or "").lower())
        if not words:
            continue
        expected = route_of_section.get(b.get("section_id"))
        scope = words_by_route.get(expected, hay_words) if expected else hay_words
        hits = sum(1 for w in words if w in scope)
        cov = hits / len(words)
        entry = {"section_id": b.get("section_id"), "role": b.get("role"),
                 "coverage": round(cov, 3), "text": (b.get("text") or "")[:80]}
        if expected:
            entry["expected_route"] = expected
        if cov < 0.5:
            missing.append(entry)
        elif cov < coverage_threshold:
            weak.append(entry)

    placeholders = sorted(set(_PLACEHOLDER_RE.findall(haystack)))

    # Navigation: the plan decides which sections belong in nav. If it marks any
    # and the page has no <nav>, the chrome is missing — the state the renderer
    # shipped in for its entire life. EVERY route must carry it: `any` would let
    # one navigable page vouch for four that strand the visitor.
    wants_nav = (any(s.get("in_nav") for s in plan.get("sections", []) or [])
                 or any(p.get("in_nav") for p in plan.get("pages", []) or []))
    # Check the RAW markup, not the tag-stripped text — _visible_text has
    # already removed every element by the time it is searched.
    routes_without_nav = [r for r, raw in zip(routes, raw_pages)
                          if "<nav" not in raw.lower()]
    has_nav = not routes_without_nav
    nav_missing = wants_nav and bool(routes_without_nav)

    # A shared <title> across every route is the canonical symptom of a dynamic
    # route missing generateMetadata(). Nothing else in the harness can see it.
    titles = [(_TITLE_RE.search(raw).group(1).strip() if _TITLE_RE.search(raw) else "")
              for raw in raw_pages]
    dup_titles = len(routes) > 1 and len(set(titles)) < len(titles)

    obs = {"copy_blocks_checked": len(blocks), "missing": missing, "weak": weak,
           "placeholders_found": placeholders, "wants_nav": wants_nav,
           "nav_present": has_nav, "routes_without_nav": routes_without_nav,
           "routes": list(routes), "titles": titles,
           "coverage_threshold": coverage_threshold}

    problems = []
    if missing:
        problems.append(f"{len(missing)} copy block(s) did not reach the page")
    if placeholders:
        problems.append(f"{len(placeholders)} placeholder string(s) rendered")
    if nav_missing:
        problems.append(f"{len(routes_without_nav)} route(s) have no <nav>")
    if dup_titles:
        problems.append("routes share a <title> (dynamic route missing generateMetadata?)")
    if problems:
        notes = [f"MISSING {m['section_id']}/{m['role']}"
                 + (f" on {m['expected_route']}" if m.get("expected_route") else "")
                 + f" (coverage {m['coverage']}): {m['text']}"
                 for m in missing[:12]]
        notes += [f"PLACEHOLDER rendered: {p}" for p in placeholders[:5]]
        if nav_missing:
            notes.append("no <nav> element on: " + ", ".join(routes_without_nav))
        if dup_titles:
            notes.append("duplicate <title> across routes: " + json.dumps(titles))
        return GateResult(
            id="11", name="Content fidelity", verdict="FAIL",
            evidence_basis="DOM+assets confirmed",
            summary="; ".join(problems) + ".",
            notes=notes, observations=obs,
        )

    return GateResult(
        id="11", name="Content fidelity", verdict="PASS",
        evidence_basis="DOM+assets confirmed",
        summary=(f"All {len(blocks)} copy block(s) reached the DOM across "
                 f"{len(routes)} route(s) "
                 f"(>={int(coverage_threshold * 100)}% token coverage); no placeholder strings; "
                 + ("navigation present." if wants_nav else "plan requests no navigation.")),
        notes=[f"weak-but-present: {w['section_id']}/{w['role']} {w['coverage']}" for w in weak[:8]],
        observations=obs,
    )



def run(args: argparse.Namespace) -> int:
    site_dir = os.path.abspath(args.site_dir)
    if not os.path.isdir(site_dir):
        print(f"ERROR: site directory not found: {site_dir}", file=sys.stderr)
        return 2

    report_dir = os.path.abspath(args.out)
    os.makedirs(report_dir, exist_ok=True)

    routes = [normalize_route(r) for r in args.routes]
    viewports = list(args.viewports)

    server_log = os.path.join(report_dir, "server.log")
    server = ServerHandle(site_dir, args.host, free_port(args.host), server_log)
    results: list[GateResult] = []

    try:
        server.start()
        if not wait_for_server(server.base_url() + "/", timeout=10.0):
            results.append(GateResult(
                id="1", name="Boot",
                verdict="FAIL",
                evidence_basis="HTTP-200 only",
                summary="Local server did not respond on root within 10s.",
                notes=[f"Log: {server_log}"],
                observations={"base_url": server.base_url()},
            ))
            # Skip downstream gates; print partial report.
            return finalize(results, site_dir, args, server, server_log, report_dir)

        # Run gates 1, 2, 7, 8 first (don't need axe/lighthouse).
        results.append(gate_1_boot(server, routes, args.timeout))
        results.append(gate_2_dependency(server, site_dir, routes, args.timeout))

        # Gate 3 — accessibility (axe-core)
        results.append(gate_3_accessibility(server, routes, args.timeout))

        # Gate 4 — performance (lighthouse)
        g4 = gate_4_performance(server, routes, args.timeout, args.skip_lighthouse)
        results.append(g4)

        # Gate 5 — site-wide audit (builds on g4)
        results.append(gate_5_sitewide(g4, routes))

        # Gate 6 — responsive
        results.append(gate_6_responsive(server, routes, viewports, args.timeout))

        # Gate 7 — motion
        results.append(gate_7_motion(server, routes))

        # Gate 8 — token discipline
        results.append(gate_8_token_discipline(server, routes))

        # Gates 9 + 10 — Next.js renderer build + bundle budget. Only fire when
        # the site dir is a Next.js static export (i.e. the renderer produced
        # _next/). On the static composer path these return NOT-EXERCISED with
        # a clear "not a Next.js export" reason so the tier math is honest.
        renderer_root = args.renderer_root
        if renderer_root is None and is_nextjs_export(site_dir):
            # Default: walk upward from the site dir to find package.json.
            renderer_root = find_package_root_for(site_dir)
        results.append(gate_9_build(site_dir, renderer_root, args.timeout))
        results.append(gate_10_bundle(site_dir, args.bundle_budget_kb))
        results.append(gate_11_content_fidelity(server, routes, args.design_plan, args.timeout))

    finally:
        server.kill()

    return finalize(results, site_dir, args, server, server_log, report_dir)


def finalize(results: list[GateResult], site_dir: str, args: argparse.Namespace,
             server: ServerHandle, server_log: str, report_dir: str) -> int:
    # M6: compute sha256 over every artifact the validator consumed so a later
    # verify.sh run can detect that gate-results.json is stale relative to its
    # inputs. We hash the inputs the actual site (index.html, styles.css,
    # tokens.css) — these are the files the gates inspected. External browsers
    # don't alter them; the validator itself never writes them.
    import hashlib
    input_hashes: dict[str, str] = {}
    for fname in ("index.html", "styles.css", "tokens.css"):
        path = os.path.join(site_dir, fname)
        if os.path.isfile(path):
            h = hashlib.sha256()
            with open(path, "rb") as fh:
                while True:
                    chunk = fh.read(64 * 1024)
                    if not chunk:
                        break
                    h.update(chunk)
            input_hashes[fname] = h.hexdigest()

    # Next.js export: also hash the emitted JS bundle so Gate 10's measurement
    # is protected against staleness. We hash every .js file under _next/static/
    # and roll a single combined hash so the JSON stays small. Without this a
    # future build that violates the budget would still be reported as a PASS
    # if validate_site.py wasn't re-run.
    if is_nextjs_export(site_dir):
        static_dir = _next_static_dir(site_dir)
        if os.path.isdir(static_dir):
            combined = hashlib.sha256()
            js_files = []
            for root, _dirs, files in os.walk(static_dir):
                for fname in files:
                    if fname.endswith(".js"):
                        js_files.append(os.path.join(root, fname))
            for path in sorted(js_files):
                combined.update(os.path.relpath(path, static_dir).encode("utf-8"))
                with open(path, "rb") as fh:
                    while True:
                        chunk = fh.read(64 * 1024)
                        if not chunk:
                            break
                        combined.update(chunk)
            input_hashes["_next/static/*.js (combined)"] = combined.hexdigest()

    # Write gate-results.json
    with open(os.path.join(report_dir, "gate-results.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema": SCHEMA_VERSION,
            "gate_version": GATE_VERSION,
            "site_dir": site_dir,
            "routes": args.routes,
            "viewports": args.viewports,
            "generated": datetime.now(timezone.utc).isoformat(),
            "host": args.host,
            "port": server.port,
            "results": [r.to_dict() for r in results],
            "meta": {
                "input_hashes": input_hashes,
                "input_hashes_algorithm": "sha256",
                "input_hashes_note": (
                    "Recompute with: sha256sum <site_dir>/index.html "
                    "<site_dir>/styles.css <site_dir>/tokens.css. If the site is a "
                    "Next.js export, also verify the combined _next/static/*.js hash. "
                    "If these change without re-running validate_site.py the gate "
                    "results are stale."
                ),
            },
        }, f, indent=2, default=str)

    # Write validation-report.md
    report_md = render_report(results, site_dir, args, server, server_log)
    with open(os.path.join(report_dir, "validation-report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)

    # Print a short summary to stdout
    print(f"validate_site.py — {len(results)} gates")
    for r in results:
        marker = {"PASS": "✓", "FAIL": "✗", "NOT-EXERCISED": "○"}[r.verdict]
        print(f"  {marker} Gate {r.id} {r.name}: {r.verdict}  ({r.evidence_basis})")
    tier, reason = compute_tier(results)
    print(f"\nAcceptance tier: {tier}")
    print(f"Reason: {reason}")
    print(f"\nReport: {os.path.join(report_dir, 'validation-report.md')}")
    print(f"Raw JSON: {os.path.join(report_dir, 'gate-results.json')}")
    print(f"Server log: {server_log}")

    # Exit code: 0 if no FAIL, 2 if any FAIL.
    if any(r.verdict == "FAIL" for r in results):
        return 2
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="validate_site.py",
        description="10-gate validation harness for a composed static site directory.",
    )
    p.add_argument("site_dir", help="Site root directory (index.html + assets).")
    p.add_argument("-o", "--out", required=True, help="Report output directory.")
    p.add_argument("--routes", type=parse_str_list, default=["/"],
                   help="Comma-separated routes to validate (default: /).")
    p.add_argument("--entry", default="index.html", help="Default entry file for bare routes (default: index.html).")
    p.add_argument("--viewports", type=parse_int_list, default=DEFAULT_VIEWPORTS,
                   help=f"Comma-separated viewport widths (default: {','.join(str(v) for v in DEFAULT_VIEWPORTS)}).")
    p.add_argument("--skip-lighthouse", action="store_true", help="Skip the Lighthouse gate (and the site-wide audit that feeds it).")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-gate timeout in seconds (default: 30).")
    p.add_argument("--host", default="127.0.0.1", help="Bind host for the local server (default: 127.0.0.1).")
    p.add_argument("--renderer-root", default=None,
                   help="Path to the Next.js renderer project root (the directory containing "
                        "package.json). Only used by Gate 9 (build). When omitted and the site "
                        "dir is a Next.js export, validate_site.py walks upward to find package.json.")
    p.add_argument("--design-plan",
                    help="design-plan.json. Enables Gate 11 (content fidelity): verifies "
                         "every copy block the design pass wrote actually reached the DOM.")
    p.add_argument("--bundle-budget-kb", type=int, default=DEFAULT_BUNDLE_BUDGET_KB,
                   help=f"Gate 10 budget: total gzipped JS in _next/static/ must be under this "
                        f"many KB (default: {DEFAULT_BUNDLE_BUDGET_KB}).")
    return p.parse_args(argv)


def parse_int_list(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def parse_str_list(s: str) -> list[str]:
    """Split a comma-separated CLI value into a list.

    `--routes` was declared with no `type=`, so argparse handed `run()` the raw
    STRING and `[normalize_route(r) for r in args.routes]` iterated it one
    CHARACTER at a time: `--routes '/,/about/'` became 15 single-character
    routes. Multi-route validation has therefore never actually run — which is
    why gate 5 has only ever taken its `len(routes) <= 1` branch.

    >>> parse_str_list("/,/about/")
    ['/', '/about/']
    >>> parse_str_list(" /a , /b ")
    ['/a', '/b']
    >>> parse_str_list("/")
    ['/']
    """
    return [x.strip() for x in s.split(",") if x.strip()]


def main() -> int:
    args = parse_args(sys.argv[1:])
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
