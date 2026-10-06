# Asset Preservation Table

Source: `https://travelproductions.film/es/…` (7 declared ES routes)
Machine-authoritative record: `mirror/mirror-manifest.json` (schema 1.3). Counts, hashes, paths and
skip reasons are **not** restated here — this table records the *decision* per asset class and why
the alternatives were rejected.

**What was acquired:** 184 files, 86.2 MB. Of that **78.5 MB is video** (21 self-hosted `.mp4`).
Also 53 images, 67 stylesheets, 27 scripts, 8 fonts, 1 Lottie JSON, 7 route documents.

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| Safiro display family — 4 cuts (`safiro-{regular,medium,semibold,bold}-webfont.woff2`) | `wp-content/uploads/2024/05/` (self-hosted, same-origin) | `Local Copy` | **Restricted — must never ship.** Safiro is a licensed retail typeface (Atipo Foundry) that the source self-hosts under *its own* licence; that licence does not transfer. Captured because the baseline is illegible without it and substituting a face during the mirror would be a redesign, which the fidelity rules forbid. Excluded from git. | Baseline is faithful. Derived site must license Safiro itself or replace the face — a deliberate phase-2 decision, not a silent swap. |
| Antonio, Open Sans (`wp-content/uploads/elementor/google-fonts/…`) | Same-origin, Elementor-localized Google Fonts | `Local Copy` | SIL OFL. Freely redistributable; safe to carry forward. | None. |
| Roboto — two copies: Elementor-localized + `fonts.gstatic.com` (under `_external/`) | Same-origin + external host authorized with `--allow-host` | `Local Copy` | Apache-2.0. Localized so typography survives without network. | None. |
| `fonts.googleapis.com/css2?family=Roboto…` | External stylesheet | `Kept External` | Refused by the pipeline — the capture recorded personalized evidence on the response. Not required: Roboto already resolves from the two local copies. Recorded rather than forced. | None observed. |
| Unrequested `@font-face` alternates in Elementor's CSS | Referenced in CSS, never fetched | `Unknown` | Elementor emits the full Roboto axis; the browser fetches only the cuts it needs. Never observed, so not claimed as captured. | None at the declared viewports. |
| 21 self-hosted `.mp4` — hero reel (desktop + mobile cuts), section covers, case-study covers, 3D-scene clips | `wp-content/uploads/2024–2026/…`, same-origin static GETs | `Local Copy` | **Third-party footage — must never ship.** Captured in full; all range-serve `206` locally. This is the source's own commercial footage of *named* third-party clients. A derived site that kept it would present another company's showreel, and other people's properties, as its own. Excluded from git. | Baseline faithful. Phase 2 replaces all 21 wholesale. |
| 147 `player.vimeo.com/video/…` player documents | Observed in every route capture | `Embed` | **Not downloadable, and that is the faithful outcome.** The source streams them from Vimeo, so an iframe pointed at Vimeo *is* the accurate reproduction; a scraped local copy would be less faithful *and* a redistribution. The pipeline refused them (`provider-hosted resources are not auto-acquired`). | **This is why `mirror_assets.py` exits non-zero:** the capture marks iframe documents `required` and 147 can never be satisfied. Also blocks any offline-validated claim — the portfolio players need network. |
| Luma Labs splat viewer — `cdn-luma.com/public/lumalabs.ai/viewers/sparkles-…/{index.html,viewer.js,viewer.css}` + 6 scene artifacts | `/es/escena-3d/` capture | `Embed` | A third-party Gaussian-splat viewer iframe with the scene passed in the query string. Outside the authorized host set, so refused. Same reasoning as Vimeo. | Second contributor to the non-zero exit (1 required failure). Scene will not render offline. |
| GSAP 3.9.1 + ScrollTrigger (`cdnjs.cloudflare.com`, stored under `_external/`) | Script tags in every route | `Local Copy` | Authorized explicitly via `--allow-host`. Localized so the scroll choreography — the site's primary motion system — survives without network. | None. Note for phase 2: GSAP is free under its own licence but **not MIT**, so it cannot enter the MIT-only renderer pipeline; it is fine inside this WordPress baseline. |
| Lenis smooth-scroll (`wp-content/uploads/wpmss/lenis-init.min.js` + plugin assets) | Same-origin | `Local Copy` | Drives the momentum scrolling the whole layout is tuned against. | None. |
| `World-global-3.json` — Lottie, 38 KB (rotating globe) | `wp-content/uploads/2024/05/`, observed as XHR | `Local Copy` | Auto-classified `data_api` by the capture and refused. Verified static before overriding: same-origin, public `200`, `application/json`, `Last-Modified 2024-05-06`, byte-identical across routes. Declared `public_static` through `reports/extra-urls.jsonl` — the pipeline's own supplementary channel, reasoning recorded in the record. | Without it the globe module renders empty. Resolved. |
| jQuery 3.7.1, jQuery-migrate, jQuery UI core, `wp-emoji-release`, Elementor + Elementor Pro front-end bundles | Same-origin | `Local Copy` | Standard WordPress/Elementor runtime. | None. |
| 53 images — case-study stills, staff/office photography, and the **client logo band** (Meliá, Ritz-Carlton, RIU, Islas Canarias, Peñíscola, Mogán, Proximity BBDO, The Tais, Gran Meliá, Cabildo de Tenerife) | Same-origin uploads | `Local Copy` | **Must never ship.** The logo band is a wall of other companies' trademarks asserting a client relationship; the stills are commercial photography of third-party properties. Neither can carry into a derivative for a different client. Excluded from git. | Baseline faithful. Phase 2 replaces all of it. |
| `Logo-Travel-web_blanco.svg` — source wordmark | Same-origin | `Local Copy` | **Must never ship.** The source's own identity; baseline only. | Baseline faithful; replaced in phase 2. |
| `s.w.org/images/core/emoji/…svg` | External | `Kept External` | WordPress emoji fallback, outside the authorized host set. | None observed. |
| Telemetry — `googletagmanager.com/gtag/js` (`G-T5Q0TX0MC4`), `region1.analytics.google.com/g/collect`, `stats.g.doubleclick.net`, `google.fr/ads/ga-audiences`, `static.cloudflareinsights.com/beacon.min.js` | Observed in every route capture | `Blocked` (intentional) | Telemetry is never auto-acquired and live tracking is never replayed locally. No construction-time no-op was needed — nothing blocked on them. | Not a fidelity failure. The derived site needs its **own** measurement IDs; the source's must not be carried over. |

## Baseline approximations requiring approval

None. Nothing in this baseline is `Approximated` — every asset is either a verified `Local Copy`, an
`Embed` that is faithful *because* it stays external, `Kept External` with no observed impact, or
intentionally `Blocked` telemetry.

The two `Embed` rows are **`Fidelity Gap`s for offline use only**, not approximations: with network
available they behave exactly as the source does.

## Hard boundary for phase 2

Everything marked **must never ship** is baseline scaffolding, not content. The transferable part of
this capture is **structure** — the Elementor section geometry, the scroll choreography, the type
scale and rhythm, the grid, the nav behaviour. The copy, footage, photography, client logo band,
wordmark, licensed display face and analytics IDs belong to the source and are *replaced*, not
edited, in the re-version step.
