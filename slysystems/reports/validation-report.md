# Validation Report — sly.systems homepage

## Declared validation scope

- Source URL / evidence: `https://sly.systems/` — captured 2026-08-15T21:23Z, schema_version `1.3`.
- Local URL / serving contract: `http://127.0.0.1:8200/` served from `mirror/` via `~/.claude/skills/nt-site-mirror/scripts/serve.py mirror --port 8200 --no-spa`. `file://` is unsupported; route_map is in `mirror/mirror-manifest.json`. SPA fallback OFF.
- Method: `Static Mirror` (partial — builder-runtime dependency recorded as Fidelity Gap, not silently approximated).
- Routes: `/` only. Eight sibling routes are in the multi-route inventory but out of scope per "homepage first" instruction.
- Viewports: `desktop` (1440×900 default), `mobile` (390×844 default).
- Interaction / loading / media states: standard load + bounded settling scroll. No click interactions (tab picker / hover / form submit) exercised in this pass.
- Source and local capture date/time: source captured 2026-08-15T21:23:34Z; local validation 2026-08-15T21:27Z.

## Per-section checks

| Section / route | Viewport | Scroll behavior | Animation / media | Interaction states | Verification method | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Header + nav | desktop, mobile | persists | sticky + opacity transition | not exercised | DOM+assets confirmed | `Pass for declared evidence` |
| Hero "SLY" letters + "We are" + newsletter form | desktop, mobile | first viewport | GSAP per-letter video letters (4 mp4) + tagline reveal | not exercised (newsletter form submit returns 404 locally because base44 backend not mirrored) | Observed visually (local vs source screenshot grid matches) | `Fidelity Gap` — letter videos external, JS throws `Base44Error` at first render |
| Hero tagline ("The best opportunities…") | desktop, mobile | first viewport | GSAP scroll reveal | n/a | Observed visually + DOM+assets confirmed | `Pass for declared evidence` |
| Service card row ("Four moves") | desktop, mobile | below-the-fold scroll | 4 cards, GSAP staggered fade | not exercised (hover unverified) | DOM+assets confirmed; background media external | `Fidelity Gap` — card backgrounds external |
| Case-study picker ("Pick your world") | desktop, mobile | below-the-fold scroll | tab UI + tile video | not exercised (tab click) | DOM+assets confirmed; videos external | `Fidelity Gap` — tile videos external |
| Audio embed (SoundCloud) | desktop, mobile | mid-page | iframe (provider audio) | not exercised (audio play) | DOM+assets confirmed (iframe src present) | `Blocked` — provider stream; kept external per `audio.md` hygiene |
| Logo wall ("In the news") | desktop, mobile | mid-page | GSAP-staggered logo fade-in | n/a | DOM+assets confirmed; images external | `Fidelity Gap` — images external |
| Footer | desktop, mobile | persistent | static | n/a | DOM+assets confirmed | `Pass for declared evidence` |
| Motion.dev badge | desktop, mobile | bottom-right | none | n/a | External; not mirrored | `Out of scope` (third-party) |

## Global checks

- [x] Typography and spacing checks completed for the declared comparison scope (Cinzel + Inter + Space Grotesk captured; layout typography visible in screenshots)
- [x] All kept same-site links resolve locally, intentionally point live/external, or are documented out of scope (eight sibling routes documented out of scope)
- [x] Every in-scope structured module (tables, pricing, forms, legal) exists on the correct route and is structurally recognizable (newsletter form, case-study cards, audio embed all present in source-order)
- [ ] No unresolved critical overlap, stuck/frozen behavior, or missing asset was found within exercised coverage — see Fidelity Gaps; unverified
- [x] Performance observations recorded for the declared experience (see "Performance observations")
- [x] Active module validation results recorded: video (16), audio (1 embed), multi-route (9 discovered; 1 in scope), runtime-assets (single bundle; nothing lazy)
- [x] Asset Preservation Table statuses verified — no silent substitutions; every external asset is classified, every same-origin is captured

## Static Mirror audit (Static Mirror Mode only)

- Result tier: `Partial static mirror` — `First-render` items captured (HTML/CSS/JS/fonts/manifest), `Validated` portions incomplete because builder-runtime backend + external brand media + provider audio are all referenced but not local.
- Discovery coverage: `Complete for declared triggers` for HTML/CSS/JS/fonts/manifest; `Partial` for media.base44.com (24 items referenced, 0 mirrored); `Blocked` for `w.soundcloud.com/player/?url=…` (1 iframe URL required-for-baseline but not eligible).
- Declared viewport (validation source of truth): `1440×900` desktop + `390×844` mobile (script defaults). Narrower previews not claimed.
- Experience gate: not applicable — no preloader / progress / entry screen; first render surfaces 4×404/501 console errors immediately at JS init because the Base44 SDK probes `/api/apps/<id>/entities/User/me` + analytics on load.
- Evidence gates:
  - Boot gate: **pass** — `python3 serve.py mirror --port 8200 --no-spa` boots and serves the captured routes; HTTP 200 verified at `/`, `/manifest.json`, `/assets/index-BfiDsVd2.css`, `/assets/index-C--Jvz_w.js`.
  - Dependency gate: **fail** — the Base44 SDK calls 5 backend API endpoints not present in the mirror, generating `required_same_origin_http_error` console errors at JS init; 16 brand videos + 8 brand images also fail to load (cross-origin network failures). All errors are declared; none are mirror-introduced in the sense that the JS bundle itself requests them against the live origin.
  - Experience gate: n/a — no preloader.
- Asset count: **10 downloaded** (HTML + 3 same-origin + 6 Google Fonts); **3** virtual same-origin routes (single file reused); **1 required failure** (SoundCloud iframe URL).
- Missing or unresolved files within declared coverage: as above.
- Remaining external requests (critical vs harmless fallback):
  - **Critical for declared scope but unresolvable locally**: Base44 backend APIs (5 endpoints), media.base44.com brand media (24 entries), SoundCloud widget family (8 entries), Motion-dev badge (1).
  - **Harmless fallback**: Google Fonts CSS/woff2 (already localized via `--allow-host`), telemetry POSTs (auto-skipped).
- Construction-time accommodations: **None**. No shim, no origin rewrite, no telemetry no-op, no path rewrite. The mirror is byte-faithful to what was downloaded; the gap is "what wasn't downloaded and why", which is documented in `asset-preservation-table.md`.

## Serving Contract (Static Mirror Mode only)

- Serve command / config (shipped with the project):
  ```
  python3 ~/.claude/skills/nt-site-mirror/scripts/serve.py mirror --port 8200 --no-spa
  ```
  (The `mirror/serve-local.py` launcher was not emitted because the mirror final result is `failed_required` — the SoundCloud iframe is provider-streamed audio. Operator can run the above directly.)
- Web root: `mirror/` · Port: `8200` in this validation; default `8000` is occupied by another service on this host.
- Contract / manifest schema and path: `mirror/mirror-manifest.json` schema_version `1.3`. (`serve-contract.json` was not emitted for the same reason.)
- SPA fallback: `Off` (Vite SPA technically, but every route in scope is captured verbatim so no fallback needed; `route_map` covers them all).
- Exact path-and-query route-map coverage / unresolved variants:
  - `/` → `_/index.html`
  - `/assets/index-BfiDsVd2.css`
  - `/assets/index-C--Jvz_w.js`
  - `/manifest.json`
  - `/api/apps/manifests/<id>/manifest.json` → points at the same `manifest.json` (cache alias)
  - Unresolved variants: query strings other than what `/` carries; any path outside the 5 mapped routes (e.g. `/api/apps/<id>/entities/User/me`) returns 404 because the Base44 backend is intentionally not mirrored.
- Plain static hosting valid: **no** — `/api/apps/.../entities/...` and similar are required at JS init.
  - Range/206 media support: not needed (no Range-bearing assets in scope).
  - Content-type replay (manifest-recorded types): needed — `application/javascript`, `text/css`, `text/html`, `application/json`.
  - Query-aware / variant routing: not needed in current scope.
  - Other (shims, serving-time fallbacks): none.
- `file://` support: `Unsupported` — Vite/JS modules use absolute paths and CORS; the skill disallows file:// validation by design.
- Validation claims are conditional on this serving setup.

## Automated URL × Viewport Evidence

- `viewports.py` result file: `reports/viewports/local-vs-source.json`.
- Matrix complete: **no** — `complete_matrix=false; produced=4; passed=0; failed=4`. The script returns nonzero exit; the matrix IS produced for evidence but the skill's "VALIDATION FAILURE: incomplete URL x viewport matrix" verdict stands.
- Per-cell status and final URL recorded: yes — all 4 cells produced `final_url`, `title="SLY — Custom AI Software & Automation for Growing Businesses | Miami AI Product Group"`, `initial_status=200`, `success=false`. The non-pass reason is `required_runtime_failures_observed` (Base44 backend 404/501 + cross-origin brand-media failures).
- Rejected challenge, login, consent-blocking, error, and 404 states: none rejected — both URLs returned 200; the failures are all post-load network errors.
- Scroll mechanisms exercised: `window_scroll` (default; same as the capture pass).
- Service-worker-controlled and bypassed results, where relevant: no SW registered; `service_worker_mode: allow` did not change behavior.
- Settling method: `DOMContentLoaded + bounded reported settling` — default 5000 ms; both URLs settled within bounds.

## Construction-Time Accommodations

| Artifact / path | Phase / actor | Required local accommodation | Source / provenance evidence | Revalidation evidence |
| --- | --- | --- | --- | --- |
| — | `construction` / — | None — the mirror is byte-faithful to what was downloaded. | `mirror/mirror-manifest.json` `local_modifications: []` | Re-served over `serve.py` and served all 4 same-origin assets at HTTP 200 with correct content-types and `no-store`. |

## Interaction Coverage

- Exercised (with result):
  - Page load + bounded settling scroll (per `viewports.py`). Console: 7 console errors (5 are Base44 backend 404/501, 1 is the Base44 SDK's `App state check failed: Base44Error`, 1 unclassified).
- Not exercised — and why:
  - Click on `Pick your world` case-study tabs — out of scope for first-render validation; local JS cannot swap data because backend is down.
  - Hover on "Four moves" service cards — visual inspection only; no hover state asserted.
  - Newsletter form submit — the form rendered but submit would 404 at `/api/...`; not exercised.
  - SoundCloud iframe `play()` — provider stream; not exercisable locally.
  - GSAP timeline scrubbing / hero letter transitions — unobservable in still screenshots.

## External Runtime Dependencies

| Dependency | Handling | Fidelity impact | Evidence |
| --- | --- | --- | --- |
| `sly.systems/api/apps/<id>/entities/User/me` | `Kept external` (backend, not mirrorable) | "App state check failed: Base44Error" logged at first render | `viewports.py` `required_same_origin_http_error`, `http_errors[]` in local-vs-source.json |
| `sly.systems/api/apps/<id>/entities/ShowcaseApp?sort=…` | `Kept external` (backend, not mirrorable) | Case-study content unreadable locally; default showcase tiles shown skeleton | Same JSON, second console error |
| `sly.systems/api/apps/public/prod/public-settings/by-id/<id>` | `Kept external` (backend, not mirrorable) | App config unreadable | Same JSON, third console error |
| `sly.systems/api/app-logs/<id>/log-user-in-app/home` (POST) | `Kept external` (backend, not mirrorable) | 501 — not implemented by static serve | Same JSON |
| `sly.systems/api/apps/<id>/analytics/track/batch` (POST) | `Kept external` (backend, not mirrorable) | 501 — not implemented by static serve | Same JSON |
| `media.base44.com/videos/.../0[1-4]-hero-letter-{S,L,Y}-*.mp4` and 12 more | `Kept external` (rebrand target) | Hero letters show as dark placeholders locally; 4 hero letters + 11 case-study/feature videos | `viewports.py` `observed_failures[]` cross-origin entries; JS bundle references 65 distinct media.base44 URLs |
| `media.base44.com/images/.../*.png` (8 URLs) | `Kept external` (rebrand target) | Logo wall + OG image + favicon missing locally | Same JSON |
| `w.soundcloud.com/player/?url=…` | `Embed` + `Kept external` (provider audio) | Audio iframe renders but does not play; provider stream | `mirror-manifest.json` `failed[]` (1 required failure for this URL); preserved as Embed |
| `widget.sndcdn.com/*` (6 scripts + 1 image) | `Kept external` (provider) | SoundCloud widget JS not loaded locally | `mirror-manifest.json` `skipped_external[]` |
| `fonts.googleapis.com`, `fonts.gstatic.com` | `Localized` (`--allow-host`) | None — fonts served from `mirror/_external/…` | `mirror/_external/fonts.googleapis.com/`, `mirror/_external/fonts.gstatic.com/` |
| `api.motion.dev/score/badge?url=…` | `Embed` | Tiny Motion.dev badge missing from lower-right | Out of scope (third-party) |

## Fidelity Gaps

| Feature | Missing / downgraded behavior | Constraint | Available baseline paths | Status |
| --- | --- | --- | --- | --- |
| Hero per-letter "SLY" videos | 4 letter videos from `media.base44.com` are not local | External host, rebrand target, no `--allow-host` authorized | Capture with `--allow-host media.base44.com` (one-line addition); or accept as rebrand target — the JS bundle preserves the URL slots | `Pending` — awaiting rebrand decision |
| 12 case-study / feature videos | Reference URLs in JS bundle, not local | Same | Same | `Pending` |
| 8 brand images (logos, OG, favicon) | Reference URLs, not local | Same | Same | `Pending` |
| SoundCloud iframe audio | Iframe renders, audio does not play | Provider-streamed audio; asset hygiene rule applies | Replace with user's own audio embed at rebrand; cannot mirror provider stream | `Accepted exception` (asset hygiene) |
| Base44 SDK backend API calls (5 endpoints) | Logs `App state check failed: Base44Error` at every page load | Static mirror cannot stand up the Base44 backend | Editable Recreation path — rebuild without Base44 SDK; or fall back to a hosted proxy that stubs responses | `Pending` — affects Runtime Fidelity but not Structural Fidelity |

## Performance observations

- HTML payload 24 KB; CSS 173 KB; JS bundle 1.5 MB. Single bundle — no chunked loading.
- Fonts blocked on three CSS requests + three woff2 fetches; all served locally.
- Page-first-paint with missing-media still presents text + nav in <1s locally. With external network, brand media is presumably progressively loaded.
- 7 console errors observed at load (5 backend 404/501 + 2 derived). All are **declared**; none are accidental.

## Project status

`Partial`

State the declared routes, viewports, states, and evidence behind the status.

- **Completed**: HTML + CSS + JS + manifest captured and served. Google Fonts captured and served. Title, header navigation, hero text, service card row structural layout, case-study picker DOM, audio iframe URL, footer all rendered correctly in local mirror. `viewports.py` produced the 4-cell matrix; both URLs returned HTTP 200 with the same title; structural layout matches between local and source screenshots.
- **Blocked**: per-letter hero videos, case-study videos, logo-wall images, Motion badge (external + rebrand target). SoundCloud audio (provider stream). Base44 backend API calls (builder runtime, not mirrorable).
- **Approved baseline approximations**: none. The mirror is byte-faithful to what was downloaded; nothing was re-imagined or substituted.
- **Not exercised / unresolved**: tab-clicks on the case-study picker, hover on service cards, newsletter form submit, hero letter transitions are visible only in motion; SoundCloud audio play; scroll-past-footer behavior. None of these is required for first-render structural fidelity, but the next rebrand pass will need to validate them against the *derived* site (per Phase-2 rebrand workflow).
