# Discovery Report

> Installed blank template — read-only. Copy it to `<project>/reports/discovery-report.md` and fill the project-local copy. Never write project data into the installed skill.
>
> Fill every applicable field. Write `Unknown` or `Not applicable` where appropriate; never guess. Record evidence, not implementation code.

## Task

- Source URL / evidence:
- Requested baseline:
- Method: `Static Mirror` | `Editable Recreation (fallback method)`
- Why this method is suitable:
- Permission context (user-stated):
- Scope Classification: `Hero Only` | `Homepage` | `Landing Page` | `Multi-Route Site` | `Portfolio Site` | `Application`
- Declared route, viewport, and interaction coverage:

## Observed runtime

- Framework / build evidence:
- Styling evidence:
- Animation system(s):
- Observed routing behavior:
- Asset pipeline / CDN:
- Service worker / cache behavior observed:
- Supplied or authorized source repo evidence, if any:

## Editable Recreation evidence (fallback method only)

> Complete only when Static Mirror is unsuitable and recreation is required to produce the requested faithful copy.

- Measured typography (families, weights, type scale):
- Measured color values:
- Measured spacing and layout relationships:
- Observed breakpoints / responsive behavior:
- Section and component structure:
- Evidence gaps that may limit fidelity:

## Module Trigger Scan

| Trigger | Detected? (Yes / Suspected / No) | Module activated |
| --- | --- | --- |
| WebGL / canvas / 3D | | `modules/webgl.md` |
| Audio | | `modules/audio.md` |
| Video | | `modules/video.md` |
| Multiple routes | | `modules/multi-route.md` |
| Runtime-loaded assets | | `modules/runtime-assets.md` |

## Link & Route Inventory

> Every discovered in-scope same-site route, nav/footer/CTA link, hash link, modal trigger, and form action gets an explicit status. Do not silently leave an in-scope local link broken.

| Link / route | Status (`Captured local` / `Recreated local` / `Intentional live external` / `Out of scope` / `Blocked` / `Unknown`) | Structured content on target? | Evidence / reason |
| --- | --- | --- | --- |
| | | | |

## Visible Module Inventory (source order)

> Record the modules observed within the declared scope, including tables, pricing/comparison/data grids, forms, legal blocks, and desktop-only, mobile-only, hidden, scroll-loaded, or interaction-dependent modules.

| # | Module | Type | Visibility conditions | Evidence status |
| --- | --- | --- | --- | --- |
| | | | | |

## Asset Graph (Static Mirror Mode)

- `capture_assets.py` output file:
- Capture graph schema / result (`ok` / `blocked_by_challenge` / `blocked_by_login` / `blocked_by_consent` / `navigation_error` / other):
- Initial status / final status / final URL / redirect evidence:
- Automatically eligible static GET/HEAD count / excluded POST, personalized API, telemetry, and unknown XHR/fetch count:
- Metadata references by state (`Observed` / `Probed` / `Captured`):
- Scroll coverage mechanism (`window_scroll` / `internal_container` / `wheel_virtual_scroll` / `none`):
- Service-worker registrations, cache/precache evidence, controlled result, and bypassed result:
- Same-origin assets (count / notable):
- External providers detected:
- Blocked / unresolved:

## Static Mirror discovery evidence

> Verify probe results: SPA servers often return `200` + `index.html` for missing paths — check content type and body before recording a hit.

- Repo / source link found: yes / no — URL:
- Probe URLs checked (+ real result, noting SPA false-200s):
- Sitemap / routes found:
- Manifest files found:
- Source maps found:
- Bundle scan findings (count / notable — dynamic imports, WASM, workers, models, textures, audio, fonts):
- Runtime interaction capture performed, with declared trigger coverage:
- Missing assets found from local server 404 logs:
- Blocked or unexercised discovery paths:

## Findings

### Facts
-

### Assumptions
-

### Unknowns
-
