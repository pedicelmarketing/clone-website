# Validation Report — Premium Padel Academy

## Declared validation scope

- Source URL / evidence: `https://97jnvjsg4j.wixsite.com/riki-coach` (4 routes), observed 2026-08-01.
- Local URL / serving contract: `http://127.0.0.1:8712/` via `python3 tools/static_range.py site 8712` — plain static hosting plus byte-range support. Never `file://`.
- Method: **`Editable Recreation (fallback method)`** — Static Mirror attempted and blocked; see `discovery-report.md`.
- Routes: `index.html`, `clubs.html`, `camps.html`, `contacto.html`.
- Viewports: desktop 1440×900, tablet, mobile 390×844.
- Interaction / loading / media states: mobile menu open + close (click and Escape), contact-form validation and mailto composition, nav links, in-page anchors.
- Source and local capture date/time: both 2026-08-01.

## Per-section checks

| Section / route | Viewport | Scroll behavior | Animation / media | Interaction states | Verification method | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Header + nav / all 4 | desktop | sticky | none | hover, active state | Interaction-tested | Pass for declared evidence |
| Header + nav / all 4 | mobile | sticky | opacity fade | open, close, Escape, link-tap | Interaction-tested | Pass for declared evidence |
| Hero / all 4 | all 3 | window_scroll | static photo | — | Observed visually | Pass for declared evidence |
| Coaches / `/` | all 3 | window_scroll | 2 photos | — | Observed visually | Pass for declared evidence |
| Más de 15 Años (photo pair) / `/` | desktop | window_scroll | inset overlap retained | — | Observed visually + measured | Pass for declared evidence |
| Más de 15 Años (photo pair) / `/` | mobile | window_scroll | **overlap removed** | — | Measured — 0 overlapping pairs | Pass — client fix |
| Checklist / `/` | all 3 | window_scroll | none | — | Observed visually | Pass for declared evidence |
| 3 service cards / `/` | all 3 | window_scroll | none | link targets | DOM+assets confirmed | Pass for declared evidence |
| 4 media cards / `/home` | all 3 | window_scroll | 4 photos | — | Observed visually | Pass for declared evidence |
| 5 numbered steps / `/home` | all 3 | window_scroll | none | — | Observed visually | Pass for declared evidence |
| 3 statements / `/home` | all 3 | window_scroll | none | — | Observed visually | Pass for declared evidence |
| 2 splits / `/camps` | all 3 | window_scroll | 2 photos | — | Observed visually | Pass for declared evidence |
| 4 emoji features / `/camps` | all 3 | window_scroll | none | — | Observed visually | Pass for declared evidence |
| FAQ (3 items) / `/camps` | all 3 | window_scroll | none | — | Observed visually | Pass for declared evidence |
| Contact band / `/`, `/home`, `/camps` | all 3 | window_scroll | none | mailto link, CTA | Interaction-tested | Pass — client fix |
| Enquiry form / `/contacto` | all 3 | window_scroll | none | empty-field validation, mailto compose | Interaction-tested | Pass — `Approximated` backend |
| Footer / all 4 | all 3 | window_scroll | none | mailto link | DOM+assets confirmed | Pass for declared evidence |

## Global checks

- [x] Typography and spacing checks completed for the declared comparison scope — measured against source computed styles.
- [x] All kept same-site links resolve locally; the only external requests are Google Fonts, intentionally kept.
- [x] Every in-scope structured module (cards, steps, statements, FAQ, form) exists on the correct route and is structurally recognizable.
- [x] No unresolved critical overlap, stuck/frozen behavior, or missing asset within exercised coverage.
- [x] Performance observations recorded — 4.5 MB media total, all bounded to ≤2000px, `loading="lazy"` below the fold, `width`/`height` on every `img`.
- [x] Active module validation results recorded: `multi-route.md` — all 4 routes present, nav resolves on each.
- [x] Asset Preservation Table statuses verified — no silent substitutions.

## Automated evidence

**Route × viewport matrix** — `reports/viewports/viewport-results.json`, via the skill's `viewports.py`:

```
12/12 passed   (4 routes x desktop/tablet/mobile, all HTTP 200, final URL == requested URL)
```

**Layout audit** — the client's complaints, measured rather than eyeballed, 4 routes × {mobile 390, desktop 1440}:

```
8/8 cells:  text nodes < 15px      = 0
            horizontal overflow    = 0
            unintended img overlap = 0
            page errors            = 0
            HTTP 4xx/5xx           = 0
```

**Menu interaction test** — 4/4 routes at 390×844:

```
panel 390x844 at (0,0) == viewport      covers viewport: true
link centre-x == 195 (viewport centre)  offset: 0px, all four links
panel intercepts centre point: true     (opaque, not see-through)
closes on Escape: true                  body scroll locked while open
```

**Copy diff against source** — every source string ≥12 chars matched against the build:

```
inicio 44 strings · clubs 31 · camps 28 · contacto 6
unexplained deltas: 0
(every unmatched string is a contact detail or brand line the client asked to change)
```

## Serving Contract

- Serve command: `python3 tools/static_range.py site 8712` (shipped in the project).
- Web root: `site/` · Port: 8712 local, 8614 for the published tunnel.
- SPA fallback: `Off` — four real documents.
- Plain static hosting valid: **yes**. No route map, no query-aware routing, no content-type replay needed. Range/206 supported but not required (no streamed media).
- `file://` support: `Unsupported` — relative asset paths and the fonts request need an origin.
- Validation claims are conditional on this serving setup.

## Published deployment

- **URL:** `https://immigrants-energy-marine-abstract.trycloudflare.com` — the address the client already has. It was preserved deliberately: only the origin server on `127.0.0.1:8614` was swapped, and the `cloudflared` process (started 2026-07-30 21:38) was left running. Killing it would have issued a new hostname and broken the client's link.
- **Origin:** `python3 tools/static_range.py site 8614`.
- **Previously served:** the Elementor-based `travelproductions-padel/site` build. That directory is untouched on disk; only what is served changed.
- **Live verification (real browser, not curl):** 4 routes × {mobile, desktop} = 8/8 pass — new email resolves, 0 occurrences of the old email, phone, or Wix branding, 0 page errors, 0 HTTP 4xx/5xx.

### Cloudflare rewrites the email in transit

The quick tunnel applies **Email Address Obfuscation**: `mailto:` links are replaced over the wire with `/cdn-cgi/l/email-protection#<hex>` plus an injected `email-decode.min.js`, which restores the real address in the browser.

Consequences worth knowing:

- A real browser resolves it correctly — verified: `href="mailto:Infopremiumpadelacademy@gmail.com"`, 0 unresolved stubs on all 8 cells.
- **`curl` on the published URL is not valid evidence** for the contact details; it returns the stub, not the address. The served HTML is also ~434 bytes larger than the file on disk because of the injected script. Any future content check against this URL must use a browser.
- With JavaScript disabled the address would not render. This is a property of the Cloudflare preview, not of the build — the local origin serves the plain `mailto:`, and it will behave normally on the client's own domain.

## Construction-Time Accommodations

| Artifact / path | Phase / actor | Required local accommodation | Source / provenance evidence | Revalidation evidence |
| --- | --- | --- | --- | --- |
| — | — | **None.** The build is hand-written; nothing required a shim to boot. | — | — |

## Client-requested changes (not fidelity gaps)

Recorded separately from fidelity findings, because these are instructions rather than defects.

| # | Request | Applied | Evidence |
| --- | --- | --- | --- |
| 1 | Remove the Wix "Harmony" banner | Yes | 0 occurrences in rendered output; the only remaining `wix` strings are two source-code provenance comments |
| 2 | Change the email to `Infopremiumpadelacademy@gmail.com` | Yes | 8 `mailto:` hrefs plus visible text; 0 occurrences of `rikicoach` |
| 3 | Remove the phone number | Yes | 0 occurrences of `600 000 000`; 0 `tel:` links |
| 4 | "La parte del contacto no me sale" | Yes | Replaced the empty placeholder box with a real contact band on 3 routes and a working enquiry form on `/contacto` — interaction-tested |
| 5 | "El menú me sale a la derecha, quiero que me salga en el medio" | Yes | Centred full-screen overlay; measured 0px offset from viewport centre, all 4 links, all 4 routes |
| 6a | Letters too small, worst on Camps | Yes | 0 nodes under 15px on every route/viewport. Previous build: 12.2px form labels on Camps, 13.6px body. The source's own mobile floor is 16px |
| 6b | Images overlap | Yes | 0 unintended overlaps at mobile. Previous build: `elite1.jpg`×`elite2.jpg` overlapping 68×140px |
| 6c | Home-page section too far from its title | Yes | Section rhythm rebuilt on one fluid scale; the previous ~154px dead band between the photo pair and the first card is gone |

## Copy edits relative to source — disclosed

Copy is otherwise transcribed verbatim. These deliberate edits were made, and are listed so they can be reverted if unwanted:

| Route | Source | Build | Reason |
| --- | --- | --- | --- |
| `/` | "ofre**z**cemos" | "ofrecemos" | Spelling |
| `/` | "con **nostros**" | "con nosotros" | Spelling |
| `/` | "han enriquecido **mi** forma de enseñar" | "**nuestra** forma" | Surrounding paragraph is first-person plural; the singular reads as an editing leftover. **Judgement call — revert if deliberate.** |
| `/` | "clubes de **padel**" | "clubes de **pádel**" | Missing accent |
| `/home` | "perfiles de jugadores **·**." (stray space) | "jugadores." | Stray space before the period |
| `/home` | "infopremiumpadelacademy@gmail.com**.com**" | "Infopremiumpadelacademy@gmail.com" | The duplicated `.com` is a typo live on the source; used the address as the client wrote it in the brief |
| `/camps` | "y **diversion**" | "y diversión" | Missing accent |
| `/camps` | "Entrena **,** descubre" | "Entrena, descubre" | Stray space before the comma |
| `/camps` | "lectura del juego **,** la toma de decisiones" | "lectura del juego **y** la toma" | Comma splice in a three-item list |

Two changes made and then **reverted to match the source**: "Viajes y experiencias internacionales de **tenis y** pádel" (`/`) and "la escuela de **tenis o** pádel" (`/home`). Both mention tennis on the live site and there was no instruction to drop it.

## Interaction Coverage

- **Exercised (with result):** mobile menu open/close by click — pass; close via Escape — pass; close on link-tap — pass; body scroll lock — pass; panel geometry and opacity — pass; contact-form empty-field validation — pass; mailto composition — pass; all nav links on all 4 routes — pass; in-page anchors — pass.
- **Not exercised — and why:** actual mail delivery (depends on the visitor's mail client); real hardware (Chromium emulation only); touch gestures beyond tap; Safari and Firefox rendering; print styles. None of these were in the declared scope.

## External Runtime Dependencies

| Dependency | Handling | Fidelity impact | Evidence |
| --- | --- | --- | --- |
| `fonts.googleapis.com` / `fonts.gstatic.com` (Instrument Serif, Instrument Sans) | `Kept External` | None — the source's own families, both SIL OFL | 12 references across 4 pages; 0 other external hosts |
| Wix Thunderbolt runtime, `frog.wix.com` telemetry, Sentry | `Blocked` / not shipped | None — the rebuild has no dependency on any of them | 0 references under `site/` |

## Fidelity Gaps

| Feature | Missing / downgraded behavior | Constraint | Available baseline paths | Status |
| --- | --- | --- | --- | --- |
| Contact form submission | Source posts to a Wix backend; this build composes a `mailto:` instead | No server in this deliverable | Wire Formspree / Brevo / a serverless endpoint — the markup needs no change | `Approved approximation` — disclosed; needs a backend decision |
| Wix breakpoint table and easing values | Not replicated | Not observable without the Wix runtime | — | `Accepted exception` — fluid `clamp()` ramps matched to measured desktop and mobile endpoints |

## Project status

**`Complete for declared scope and evidence`**

Acceptance tier: **`Validated recreation — declared scope`** (Editable Recreation tier). Not `Offline-validated` — the Google Fonts requests were not exercised with external network blocked.

- **Completed:** 4 routes × 3 viewports (12/12); the 8-cell layout audit; menu interaction testing on all 4 routes; a full copy diff against the source with 0 unexplained deltas; all 6 client-requested changes verified by measurement.
- **Blocked:** Static Mirror acquisition of the 4 route documents (`failed_required`) — the reason for the method, recorded in `mirror/mirror-manifest.json`.
- **Approved baseline approximations:** contact-form backend (`mailto:` composition).
- **Not exercised / unresolved:** offline run with external network blocked; real-device and non-Chromium browsers; mail delivery.
- **Open client decisions:** the "Aacademy" logo typo; Juampi Vanella's title; which form backend to wire up.
