# Validation Report

Generated: 2026-07-28T23:13:00.142863+00:00
Schema: validate_site.py v1.1 (10-gate-v1.1)
Site directory: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-site`
Routes validated: /
Local server: http://127.0.0.1:48953 (python3 -m http.server, killed on exit)
Server log: /home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-validation/server.log

## Declared scope

- Method: `validate_site.py` (10-gate harness; static Composed Site / Next.js export)
- Routes: /
- Viewports: [320, 768, 1024, 1440]
- Lighthouse: enabled
- DOM audit settle: wait for load, then document.getAnimations() finished promises with a 3s cap, then poll for two consecutive pixel-identical frames (catches JS-driven animation libraries that never register in document.getAnimations)
- Next.js export detected: True
- Bundle budget (Gate 10): 300 KB gzipped JS in _next/static/
- Renderer root (Gate 9): renderer

## Gate results

| # | Gate | Verdict | Evidence basis | Summary |
|---|------|---------|----------------|---------|
| 1 | Boot | **PASS** | HTTP-200 only | All 1 route(s) returned HTTP 200 via local server. |
| 2 | Dependency | **PASS** | HTTP-200 only | All 15 local reference(s) resolved HTTP 200. 0 external host reference(s) classified as Kept External. |
| 3 | Accessibility | **PASS** | DOM+assets confirmed | axe-core found 0 serious/critical violations across 1 route(s) (0 total). |
| 4 | Performance | **PASS** | DOM+assets confirmed | Lighthouse met thresholds on 1 route(s). |
| 5 | Site-wide audit | **PASS** | DOM+assets confirmed | Only one route declared; per-route vs. whole-site comparison is not applicable. Single-route Lighthouse score was emitted by gate 4. |
| 6 | Responsive | **PASS** | Observed visually | No horizontal overflow across 4 cell(s) (1 route(s) × 4 viewport(s)). |
| 7 | Motion | **PASS** | DOM+assets confirmed | prefers-reduced-motion honored in 1 CSS file(s). |
| 8 | Token discipline | **PASS** | DOM+assets confirmed | CSS uses 302 var(--token) reference(s); 0 raw hex literals outside tokens.css. |
| 9 | Build (Next.js) | **PASS** | DOM+assets confirmed | `npm run build` exited 0 in renderer. |
| 10 | Bundle (Next.js) | **PASS** | DOM+assets confirmed | Total gzipped JS is 299.6 KB across 15 file(s), under the 300 KB budget. |

**Verdict values:** `PASS` (evidence satisfies the gate), `FAIL` (evidence contradicts), `NOT-EXERCISED` (runner unavailable or did not run). NOT-EXERCISED does not fail the run but is visible above and downgrades the acceptance tier.

**Evidence basis values:** `Observed visually` | `Interaction-tested` | `DOM+assets confirmed` | `HTTP-200 only` | `Not exercised`.

## Per-gate detail

### Gate 1 — Boot  (PASS)

- **Evidence basis:** HTTP-200 only
- **Summary:** All 1 route(s) returned HTTP 200 via local server.
- **Notes:**
  -   / -> HTTP 200
- **Observations (JSON):**

```json
{
  "per_route": {
    "/": {
      "status": 200,
      "final_url": "http://127.0.0.1:48953/"
    }
  },
  "base_url": "http://127.0.0.1:48953"
}
```

### Gate 2 — Dependency  (PASS)

- **Evidence basis:** HTTP-200 only
- **Summary:** All 15 local reference(s) resolved HTTP 200. 0 external host reference(s) classified as Kept External.
- **Observations (JSON):**

```json
{
  "reference_count": 15,
  "external_count": 0,
  "external_sample": [],
  "external_hosts": []
}
```

### Gate 3 — Accessibility  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** axe-core found 0 serious/critical violations across 1 route(s) (0 total).
- **Observations (JSON):**

```json
{
  "engine": "in-process playwright + axe.min.js (npx cache)",
  "per_route": {
    "/": {
      "route": "/",
      "url": "http://127.0.0.1:48953/",
      "status": 200,
      "exit": 0,
      "ok": true,
      "violations": 0,
      "serious_critical": 0,
      "by_impact": {
        "minor": 0,
        "moderate": 0,
        "serious": 0,
        "critical": 0
      },
      "ids": []
    }
  },
  "succeeded_routes": [
    "/"
  ]
}
```

### Gate 4 — Performance  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** Lighthouse met thresholds on 1 route(s).
- **Notes:**
  - Thresholds: {'performance': 90, 'accessibility': 95, 'best_practices': 95, 'seo': 95}
- **Observations (JSON):**

```json
{
  "per_route": {
    "/": {
      "exit": 0,
      "ok": true,
      "stdout_tail": "",
      "stderr_tail": "",
      "scores": {
        "performance": 100,
        "accessibility": 100,
        "best_practices": 100,
        "seo": 100
      },
      "fails": {}
    }
  },
  "table": [
    {
      "route": "/",
      "performance": 100,
      "accessibility": 100,
      "best_practices": 100,
      "seo": 100,
      "fails": []
    }
  ],
  "thresholds": {
    "performance": 90,
    "accessibility": 95,
    "best_practices": 95,
    "seo": 95
  }
}
```

### Gate 5 — Site-wide audit  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** Only one route declared; per-route vs. whole-site comparison is not applicable. Single-route Lighthouse score was emitted by gate 4.
- **Notes:**
  - Re-run with --routes /,/about to see a multi-route table.
- **Observations (JSON):**

```json
{
  "per_route": {
    "/": {
      "exit": 0,
      "ok": true,
      "stdout_tail": "",
      "stderr_tail": "",
      "scores": {
        "performance": 100,
        "accessibility": 100,
        "best_practices": 100,
        "seo": 100
      },
      "fails": {}
    }
  },
  "routes": [
    "/"
  ],
  "gate_4_verdict": "PASS"
}
```

### Gate 6 — Responsive  (PASS)

- **Evidence basis:** Observed visually
- **Summary:** No horizontal overflow across 4 cell(s) (1 route(s) × 4 viewport(s)).
- **Observations (JSON):**

```json
{
  "per_cell": [
    {
      "route": "/",
      "viewport": "320x720",
      "scrollWidth": 320,
      "innerWidth": 320,
      "scrollHeight": 3864,
      "settle": {
        "animation_count": 0,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 1250
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-validation/responsive_shots/4536874512350609667__320x720.png"
    },
    {
      "route": "/",
      "viewport": "768x1024",
      "scrollWidth": 768,
      "innerWidth": 768,
      "scrollHeight": 3104,
      "settle": {
        "animation_count": 0,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 1250
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-validation/responsive_shots/7192147166333163111__768x1024.png"
    },
    {
      "route": "/",
      "viewport": "1024x768",
      "scrollWidth": 1024,
      "innerWidth": 1024,
      "scrollHeight": 3555,
      "settle": {
        "animation_count": 0,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 1250
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-validation/responsive_shots/4706711957811836581__1024x768.png"
    },
    {
      "route": "/",
      "viewport": "1440x900",
      "scrollWidth": 1440,
      "innerWidth": 1440,
      "scrollHeight": 3548,
      "settle": {
        "animation_count": 0,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 1250
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-validation/responsive_shots/3498006941112091910__1440x900.png"
    }
  ],
  "viewports": [
    320,
    768,
    1024,
    1440
  ],
  "routes": [
    "/"
  ],
  "cell_count": 4
}
```

### Gate 7 — Motion  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** prefers-reduced-motion honored in 1 CSS file(s).
- **Observations (JSON):**

```json
{
  "css_files_seen": [
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-site/_next/static/css/51ed7c7ce09f30c8.css"
  ],
  "reduced_in": [
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-site/_next/static/css/51ed7c7ce09f30c8.css"
  ]
}
```

### Gate 8 — Token discipline  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** CSS uses 302 var(--token) reference(s); 0 raw hex literals outside tokens.css.
- **Notes:**
  - Gate 8 re-scoped from workflow-design.md §4's 'source-paired 10x' — see report.
  - tokens.css is the explicit source of truth; raw hex inside it is allowed.
- **Observations (JSON):**

```json
{
  "css_files": [
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-site/_next/static/css/51ed7c7ce09f30c8.css"
  ],
  "var_uses": 302,
  "raw_hex": []
}
```

### Gate 9 — Build (Next.js)  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** `npm run build` exited 0 in renderer.
- **Notes:**
  - Build log: build-stdout.log
- **Observations (JSON):**

```json
{
  "applicable": true,
  "renderer_root": "renderer",
  "exit_code": 0,
  "build_log": "build-stdout.log"
}
```

### Gate 10 — Bundle (Next.js)  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** Total gzipped JS is 299.6 KB across 15 file(s), under the 300 KB budget.
- **Observations (JSON):**

```json
{
  "applicable": true,
  "static_dir": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-site/_next/static",
  "file_count": 15,
  "total_gzipped_bytes": 306765,
  "total_gzipped_kb": 299.6,
  "budget_kb": 300,
  "top_files": [
    {
      "path": "chunks/263-c97a21ebe23abe43.js",
      "raw_bytes": 207542,
      "gzipped_bytes": 66514
    },
    {
      "path": "chunks/framework-acd67e14855de5a2.js",
      "raw_bytes": 182716,
      "gzipped_bytes": 57691
    },
    {
      "path": "chunks/4bd1b696-c023c6e3521b1417.js",
      "raw_bytes": 173019,
      "gzipped_bytes": 54228
    },
    {
      "path": "chunks/255-300d9cc44f394368.js",
      "raw_bytes": 173762,
      "gzipped_bytes": 46426
    },
    {
      "path": "chunks/polyfills-42372ed130431b0a.js",
      "raw_bytes": 112594,
      "gzipped_bytes": 39373
    }
  ]
}
```

## Acceptance tier

**Reached tier: `Validated`**

Reason: Every applicable gate ran and produced positive evidence; validation complete for declared scope.

- PASS gates: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
- FAIL gates: none
- NOT-EXERCISED gates: none

Tier definitions (from site-cloner SKILL.md):

- `First-render` — the page returns content but no deeper validation has run.
- `Validated (declared scope)` — every gate ran and produced positive evidence (runner exited cleanly AND parsed a result document with real numbers).
- `Offline-validated` — DOM/CSS/HTTP checks passed; a real-browser a11y/perf check was not exercised (Lighthouse or axe unavailable).
- `Partial` — at least one gate FAILed, OR at least one gate was NOT-EXERCISED. Per the positive-evidence-only rule, any NOT-EXERCISED gate (a runner that crashed, timed out, or produced no result document) caps tier at `Partial`. A truthful Partial beats a fabricated Validated.

## Gate 8 re-scope

research/workflow-design.md §4 gate 8 reads: **Source-paired gate — where the redesign is compared *directly* to the reference, render both side-by-side and ensure the redesign is *visibly* 10x.** That gate is subjective ('visibly 10x' is a metaphor, not a metric) and only triggers when a reference comparison is in scope. This harness re-scopes it to a **token-discipline gate** that is deterministic and runnable for every composed site:

- PASS: composed CSS uses `var(--token)` references and contains no raw hex colors outside `tokens.css`.
- FAIL: any raw hex literal outside `tokens.css`, or no `var(--token)` usage.
- NOT-EXERCISED: no CSS files observed (uncommon — every site has CSS).

If a future run needs the source-paired comparison, gate 8 can be re-added behind a `--reference-report` flag without disturbing the rest of the table.

## Evidence artifacts

- Raw per-gate results: `<report-dir>/gate-results.json`
- Server access log: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-renderer-validation/server.log`
- Responsive screenshots: `<report-dir>/responsive_shots/`

## Project status

`Complete for declared scope and evidence — every gate exercised and produced positive evidence.`
