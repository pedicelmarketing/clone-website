# Validation Report

Generated: 2026-07-29T16:54:21.962167+00:00
Schema: validate_site.py v1.1 (10-gate-v1.1)
Site directory: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site`
Routes validated: /
Local server: http://127.0.0.1:51525 (python3 -m http.server, killed on exit)
Server log: /home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-validation/server.log

## Declared scope

- Method: `validate_site.py` (10-gate harness; static Composed Site / Next.js export)
- Routes: /
- Viewports: [320, 768, 1024, 1440]
- Lighthouse: enabled
- DOM audit settle: wait for load, then document.getAnimations() finished promises with a 3s cap, then poll for two consecutive pixel-identical frames (catches JS-driven animation libraries that never register in document.getAnimations)
- Next.js export detected: False

## Gate results

| # | Gate | Verdict | Evidence basis | Summary |
|---|------|---------|----------------|---------|
| 1 | Boot | **PASS** | HTTP-200 only | All 1 route(s) returned HTTP 200 via local server. |
| 2 | Dependency | **PASS** | HTTP-200 only | All 14 local reference(s) resolved HTTP 200. 3 external host reference(s) classified as Kept External. |
| 3 | Accessibility | **PASS** | DOM+assets confirmed | axe-core found 0 serious/critical violations across 1 route(s) (0 total). |
| 4 | Performance | **FAIL** | DOM+assets confirmed | Lighthouse below thresholds on 1 route(s). |
| 5 | Site-wide audit | **PASS** | DOM+assets confirmed | Only one route declared; per-route vs. whole-site comparison is not applicable. Single-route Lighthouse score was emitted by gate 4. |
| 6 | Responsive | **PASS** | Observed visually | No horizontal overflow across 4 cell(s) (1 route(s) × 4 viewport(s)). |
| 7 | Motion | **PASS** | DOM+assets confirmed | prefers-reduced-motion honored in 1 CSS file(s). |
| 8 | Token discipline | **PASS** | DOM+assets confirmed | CSS uses 114 var(--token) reference(s); 0 raw hex literals outside tokens.css. |
| 9 | Build (Next.js) | **NOT-EXERCISED** | Not exercised | Site is not a Next.js static export (no _next/ directory); build gate not applicable. |
| 10 | Bundle (Next.js) | **NOT-EXERCISED** | Not exercised | Site is not a Next.js static export; bundle gate not applicable. |
| 11 | Content fidelity | **NOT-EXERCISED** | Not exercised | No --design-plan supplied; cannot verify the plan's copy reached the page. |

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
      "final_url": "http://127.0.0.1:51525/"
    }
  },
  "base_url": "http://127.0.0.1:51525"
}
```

### Gate 2 — Dependency  (PASS)

- **Evidence basis:** HTTP-200 only
- **Summary:** All 14 local reference(s) resolved HTTP 200. 3 external host reference(s) classified as Kept External.
- **Observations (JSON):**

```json
{
  "reference_count": 14,
  "external_count": 3,
  "external_sample": [
    "https://fonts.googleapis.com",
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap",
    "https://fonts.gstatic.com"
  ],
  "external_hosts": [
    "fonts.googleapis.com",
    "fonts.gstatic.com"
  ]
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
      "url": "http://127.0.0.1:51525/",
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

### Gate 4 — Performance  (FAIL)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** Lighthouse below thresholds on 1 route(s).
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
        "performance": 85,
        "accessibility": 100,
        "best_practices": 96,
        "seo": 100
      },
      "fails": {
        "performance": 85
      }
    }
  },
  "table": [
    {
      "route": "/",
      "performance": 85,
      "accessibility": 100,
      "best_practices": 96,
      "seo": 100,
      "fails": [
        "performance"
      ]
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
        "performance": 85,
        "accessibility": 100,
        "best_practices": 96,
        "seo": 100
      },
      "fails": {
        "performance": 85
      }
    }
  },
  "routes": [
    "/"
  ],
  "gate_4_verdict": "FAIL"
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
      "scrollHeight": 4327,
      "settle": {
        "animation_count": 19,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 500
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-validation/responsive_shots/3868268770488195871__320x720.png"
    },
    {
      "route": "/",
      "viewport": "768x1024",
      "scrollWidth": 768,
      "innerWidth": 768,
      "scrollHeight": 3335,
      "settle": {
        "animation_count": 19,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 500
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-validation/responsive_shots/3204978122647168423__768x1024.png"
    },
    {
      "route": "/",
      "viewport": "1024x768",
      "scrollWidth": 1024,
      "innerWidth": 1024,
      "scrollHeight": 3335,
      "settle": {
        "animation_count": 19,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 500
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-validation/responsive_shots/6099157031174883951__1024x768.png"
    },
    {
      "route": "/",
      "viewport": "1440x900",
      "scrollWidth": 1440,
      "innerWidth": 1440,
      "scrollHeight": 3335,
      "settle": {
        "animation_count": 19,
        "settle_cap_ms": 3000,
        "pixel_stable": true,
        "pixel_wait_ms": 500
      },
      "overflow": false,
      "screenshot": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-validation/responsive_shots/659170345062500536__1440x900.png"
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
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site/tokens.css",
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site/styles.css"
  ],
  "reduced_in": [
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site/styles.css"
  ]
}
```

### Gate 8 — Token discipline  (PASS)

- **Evidence basis:** DOM+assets confirmed
- **Summary:** CSS uses 114 var(--token) reference(s); 0 raw hex literals outside tokens.css.
- **Notes:**
  - Gate 8 re-scoped from workflow-design.md §4's 'source-paired 10x' — see report.
  - tokens.css is the explicit source of truth; raw hex inside it is allowed.
- **Observations (JSON):**

```json
{
  "css_files": [
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site/tokens.css",
    "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site/styles.css"
  ],
  "var_uses": 114,
  "raw_hex": []
}
```

### Gate 9 — Build (Next.js)  (NOT-EXERCISED)

- **Evidence basis:** Not exercised
- **Summary:** Site is not a Next.js static export (no _next/ directory); build gate not applicable.
- **Notes:**
  - Gate 9 is Only-On-Exports. The static HTML composer (compose_site.py) has no build step.
  - To run this gate, point validate_site.py at a Next.js `out/` directory.
- **Observations (JSON):**

```json
{
  "applicable": false,
  "site_dir": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site"
}
```

### Gate 10 — Bundle (Next.js)  (NOT-EXERCISED)

- **Evidence basis:** Not exercised
- **Summary:** Site is not a Next.js static export; bundle gate not applicable.
- **Notes:**
  - Gate 10 is Only-On-Exports. The static HTML composer does not emit a JS bundle.
- **Observations (JSON):**

```json
{
  "applicable": false,
  "site_dir": "/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-composed-site"
}
```

### Gate 11 — Content fidelity  (NOT-EXERCISED)

- **Evidence basis:** Not exercised
- **Summary:** No --design-plan supplied; cannot verify the plan's copy reached the page.
- **Notes:**
  - Pass --design-plan <plan.json> to exercise this gate.
- **Observations (JSON):**

```json
{
  "applicable": false
}
```

## Acceptance tier

**Reached tier: `Partial`**

Reason: Gate(s) FAIL: 4. See per-gate detail for evidence.

- PASS gates: 1, 2, 3, 5, 6, 7, 8
- FAIL gates: 4
- NOT-EXERCISED gates: 9, 10, 11

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
- Server access log: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/m6-validation/server.log`
- Responsive screenshots: `<report-dir>/responsive_shots/`

## Project status

`Partial — Gate(s) FAIL: 4. See per-gate detail for evidence.`

**Gates that did not produce positive evidence** (runner crashed, timed out, or returned no result document):
  - Gate 9 (Build (Next.js)): Site is not a Next.js static export (no _next/ directory); build gate not applicable.
  - Gate 10 (Bundle (Next.js)): Site is not a Next.js static export; bundle gate not applicable.
  - Gate 11 (Content fidelity): No --design-plan supplied; cannot verify the plan's copy reached the page.

**Gates that FAILed** (runner ran, thresholds genuinely missed):
  - Gate 4 (Performance): Lighthouse below thresholds on 1 route(s).

A truthful Partial beats a fabricated Validated. Re-run after fixing the runner(s) above (Chrome sandbox, HOME, network) to upgrade the tier.
