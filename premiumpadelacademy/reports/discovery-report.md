# Discovery Report — Premium Padel Academy

## Task

- Source URL / evidence: `https://97jnvjsg4j.wixsite.com/riki-coach` — live site, captured 2026-08-01.
- Requested baseline: all four routes of the client's own Wix site, as the base for a re-versioned build.
- Method: **`Editable Recreation (fallback method)`** — Static Mirror was attempted first and failed.
- Why this method is suitable: Static Mirror could not *technically* produce the copy. Two independent blocks, both recorded:
  1. **Acquisition refused every page.** `mirror_assets.py` returned `result: failed_required` with 4 required failures — one per route — all `capture classification disallows automatic acquisition: personalized_evidence_observed_in_one_or_more_responses`. Wix server-renders each document with per-session tokens/cookies, so the classifier will not treat the HTML as a static asset. 200 files came down and **zero pages**.
  2. **The artifact could not carry the requested changes even if acquired.** Of 252 requests on the home route, **4** are same-origin; 186 go to `static.parastorage.com` (133 JS bundles — the Wix Thunderbolt player runtime), 31 to `static.wixstatic.com`, 20 to `frog.wix.com` telemetry. There is no author stylesheet: Wix computes layout at runtime from page-data JSON. Every requested fix is a layout change. Shipping Wix's proprietary runtime under the client's own URL is also what the asset-hygiene rule exists to prevent.
- Permission context (user-stated): client engagement — rebuild of the client's own site from their own Wix property. Recorded in the manifest `authorization_context`.
- Scope Classification: **`Multi-Route Site`** (4 routes) → `modules/multi-route.md` activated.
- Declared route, viewport, and interaction coverage: 4 routes × 3 viewports (desktop 1440, tablet, mobile 390); interactions exercised: mobile menu open/close (click + Escape), contact-form validation and mailto composition, in-page anchors, all nav links.

## Observed runtime

- Framework / build evidence: Wix Thunderbolt. `<meta name="generator" content="Wix.com Website Builder">`; `clientWorker.<hash>.bundle.min.js`; page data from `siteassets.parastorage.com/pages/pages/thunderbolt?...`.
- Styling evidence: no author stylesheet. Type and colour read from computed styles in a real browser (below).
- Animation system(s): none material — no scroll choreography, WebGL, or video. `animation-audit.md` therefore not applicable.
- Observed routing behavior: four real server-rendered documents, not an SPA. Nav `Clubs` points at `/home`, not `/clubs`.
- Asset pipeline / CDN: `static.wixstatic.com` media (per-slot `v1/fill/w_,h_` variants), `static.parastorage.com` runtime, `siteassets.parastorage.com` page data.
- Service worker / cache behavior observed: no service worker. `cache-control: no-cache`, `x-cache-status: MISS` — SSR per request.
- Supplied or authorized source repo evidence, if any: none.

## Editable Recreation evidence (fallback method)

Measured from live computed styles at 1440×900 and 390×844.

- **Measured typography**
  - Headings `Instrument Serif` 400 — desktop h1 103.5px, h2 81px, h3 65.3px.
  - Body/UI `Instrument Sans` 400/600 — lead 22.5px, body 18px, card title 31.5px w600 uppercase, footer meta 15.8px.
  - Both families are SIL OFL on Google Fonts. **No paid face anywhere on the source** — no licence decision is owed on this build.
  - **Source mobile scale: 36/32px headings, 22px, 18px, 16px body.** Only 3 sub-15px nodes per route, all belonging to the Wix promo bar's 10px Arial. This measurement set the rebuild's 15px floor.
- **Measured color values:** ink / dark band `#2F3E3A` · body `#6F7F78` · accent gold `#C2A46A` · warm band `#FAF9F6` · grey band `#F5F5F2` · white `#FFFFFF`.
- **Measured spacing and layout relationships:** ~1200px content column; hero is a full-bleed photo with an inset white card (28px radius); media ~18px radius; bands alternate white / `#FAF9F6` / `#F5F5F2`.
- **Observed breakpoints / responsive behavior:** single-column stack on mobile; nav collapses to a toggle.
- **Section and component structure:** recorded per route and reproduced in `site/`.
- **Evidence gaps that may limit fidelity:** Wix's internal breakpoint table and easing values are not observable without its runtime. The rebuild uses fluid `clamp()` ramps matched to the measured desktop and mobile endpoints rather than replicating those breakpoints.

## Module Trigger Scan

| Trigger | Detected? (Yes / Suspected / No) | Module activated |
| --- | --- | --- |
| WebGL / canvas / 3D | No | — |
| Audio | No | — |
| Video | No | — |
| Multiple routes | **Yes** — 4 routes | `modules/multi-route.md` |
| Runtime-loaded assets | Yes (Wix bundles); moot under Editable Recreation | noted, not carried forward |

## Link & Route Inventory

| Link / route | Status | Structured content on target? | Evidence / reason |
| --- | --- | --- | --- |
| `/` → `index.html` | `Recreated local` | Yes — coaches, checklist, 3 service cards | Observed visually + DOM confirmed |
| `/home` → `clubs.html` | `Recreated local` | Yes — 4 programme cards, 5 numbered steps, 3 statements | Observed visually + DOM confirmed |
| `/camps` → `camps.html` | `Recreated local` | Yes — 4 features, 3-item FAQ | Observed visually + DOM confirmed |
| `/contacto` → `contacto.html` | `Recreated local` | Yes — enquiry form | Interaction-tested |
| `fonts.googleapis.com` / `fonts.gstatic.com` | `Kept External` | n/a | OFL families; the only remaining external requests |
| Wix promo bar | **Removed — client request** | n/a | Instruction, not a fidelity gap |
| Phone `+34 600 000 000` | **Removed — client request** | n/a | Instruction, not a fidelity gap |

## Visible Module Inventory (source order)

| # | Module | Type | Visibility conditions | Evidence status |
| --- | --- | --- | --- | --- |
| 1 | Header + nav (4 links) | navigation | all routes | Interaction-tested |
| 2 | Hero — photo + inset card | hero | all routes | Observed visually |
| 3 | Premium Coach's — 2 coach blocks | content | `/` | Observed visually |
| 4 | Más de 15 Años — copy + photo pair | split | `/` | Observed visually |
| 5 | ¿Qué puedes esperar? — 6-item checklist | list | `/` | Observed visually |
| 6 | 3 service cards | cards | `/` | Observed visually |
| 7 | Programas para Club — 4 media cards | cards | `/home` | Observed visually |
| 8 | Dinámica de impacto — 5 numbered steps | steps | `/home` | Observed visually |
| 9 | Programas 100% personalizados — 3 statements | content | `/home` | Observed visually |
| 10 | Entrena / Metodología — 2 splits | split | `/camps` | Observed visually |
| 11 | ¿Qué incluye? — 4 emoji features | features | `/camps` | Observed visually |
| 12 | FAQ — 3 items | structured | `/camps` | Observed visually |
| 13 | Contact band | contact | `/`, `/home`, `/camps` | Interaction-tested |
| 14 | Enquiry form | form | `/contacto` | Interaction-tested |
| 15 | Footer | footer | all routes | Observed visually |

## Asset Graph (Static Mirror Mode)

- `capture_assets.py` output files: `reports/{inicio,clubs,camps,contacto}.asset-graph.json` — all four exit 0.
- Capture graph result: `ok` for all four. The site returned 200; the block was at acquisition, not capture.
- Initial / final status / final URL: 200, no redirects, final URL equals requested URL on every route.
- Same-origin vs external request counts: 4/248, 4/243, 4/239, 4/228.
- Metadata references by state: 13 total, `Observed` / `Probed` kept separate per the schema.
- Scroll coverage mechanism: `window_scroll` (desktop and mobile passes).
- Service-worker registrations: none.
- Same-origin assets: 4 per route — the document, two `_api` calls, one worker bundle.
- External providers detected: `static.parastorage.com`, `static.wixstatic.com`, `siteassets.parastorage.com`, `frog.wix.com`, `browser.sentry-cdn.com`, `panorama.wixapps.net`.
- Blocked / unresolved: the 4 route documents (see Task).

## Static Mirror discovery evidence

- Repo / source link found: no.
- Probe URLs checked: not pursued — acquisition was already blocked at the document level, so deeper probing could not change the method decision.
- Sitemap / routes found: 4 same-site routes resolved from anchors on every route, consistently.
- Bundle scan findings: 133 JS bundles on `static.parastorage.com` (Wix runtime). Not carried forward — Editable Recreation does not consume them.
- Runtime interaction capture performed: scroll (14 steps) at desktop and mobile per route.
- Missing assets found from local 404 logs: none — the rebuild serves 0 HTTP 4xx/5xx across all 12 matrix cells.

### Note on source availability

The source returned **HTTP 503** (bare `nginx/1.30.1`) on `/` and `/camps`, and stalled after Early Hints on `/home`, at ~14:25 on 2026-08-01, while `wix.com` itself returned 200. It recovered within the hour, then passed 10/10 probes at 90–180ms. Read as a transient Wix origin wobble rather than a suspended site: pages are SSR'd per request with `x-cache-status: MISS`, so no cached copy absorbs an origin blip. Capture and acquisition ran after recovery. Inference from the error signature, not from Wix-internal evidence.

## Findings

### Facts
- Static Mirror acquisition failed on all four documents; `mirror-manifest.json` records `result: failed_required`.
- The source is ~98% third-party-hosted: 4 same-origin requests per route against ~240 external.
- The source's own mobile type floor is 16px; the earlier local recreation had dropped to 12.2px on `camps.html` form labels — the client's "letra pequeña" complaint, measured.
- The source's live contact details are `info@rikicoach.com` (×6) and `+34 600 000 000` (×7).
- `/home` already carries a partial email change by the client: `infopremiumpadelacademy@gmail.com.com` — a duplicated `.com`.
- The client's logo artwork reads **"Premium Padel Aacademy"** — a typo in the brand asset itself, live now.
- The source contradicts itself on Juampi Vanella's title: the eyebrow above his name reads "HEAD COACH", the section heading reads "Premium Coach's".

### Assumptions
- Juampi Vanella resolved as **Premium Coach** (Riki = Head Coach), following the section heading over the duplicated eyebrow. Flagged for confirmation.
- Club programme card images assigned in captured DOM order; all four render at identical `y`, so intra-row order is not independently verifiable.

### Unknowns
- Whether the client wants the logo typo corrected — their artwork, not ours to silently redraw.
- Whether a real form backend is wanted in place of the current `mailto:` composition.
