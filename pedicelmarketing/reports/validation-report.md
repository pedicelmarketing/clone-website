# Validation Report

## Declared validation scope

- **Source URL / evidence:** `https://new-pedicel-website.webflow.io/` (Webflow staging origin for
  the pedicelmarketing.com project). The production host is offline — `www.pedicelmarketing.com`
  returns 404 from Webflow's edge, apex returns 403 — so staging is the only live source.
- **Local URL / serving contract:** `http://127.0.0.1:8137` via
  `scripts/serve.py mirror --contract mirror/serve-contract.json --port 8137`.
  (Port 8137 rather than the contract's default 8000, which is occupied by an unrelated
  uvicorn process on this machine. Port choice does not affect any claim below.)
- **Method:** `Static Mirror`
- **Routes:** 63 captured and served. **All 63** swept over HTTP; **10** exercised in a real
  browser across 3 viewports (30 cells).
- **Viewports:** desktop 1440×900, tablet, mobile.
- **Interaction / loading / media states:** window scroll (full-page, max scrollY 8764 on `/`),
  font loading (`fontStatus: loaded`), lazy image settling. Form *submission* not exercised —
  see Interaction Coverage.
- **Capture date/time:** captures 2026-08-01T01:0x–01:07Z; local validation 2026-08-01T01:32–01:37Z;
  source baseline run 2026-08-01T01:31Z.

## Per-section checks

| Section / route | Viewport | Scroll behavior | Animation / media | Interaction states | Verification method | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `/` | desktop/tablet/mobile | `window_scroll`, 8764px | IX2 reveals; 61 lazy images settled | nav, CTA | Observed visually | `Pass for declared evidence` |
| `/about-our-marketing-agency` | ×3 | `window_scroll` | IX2 reveals, team imagery | nav | Observed visually | `Pass for declared evidence` |
| `/services` | ×3 | `window_scroll` | service cards | nav | Observed visually | `Pass for declared evidence` |
| `/service-web-development` | ×3 | `window_scroll` | detail layout | nav | Observed visually | `Pass for declared evidence` |
| `/our-marketing-portfolio` | ×3 | `window_scroll` | case-study grid | nav | Observed visually | `Pass for declared evidence` |
| `/projects/coeo` | ×3 | `window_scroll` | case-study media | nav | Observed visually | `Pass for declared evidence` |
| `/blog` | ×3 | `window_scroll` | 48-item collection list | nav | Observed visually | `Pass for declared evidence` |
| `/audit` | ×3 | `window_scroll` | — | **form renders**; submit not exercised | Observed visually (render); `Not exercised` (submit) | `Pass for declared evidence` (render) + `Fidelity Gap` (submit) |
| `/contact-us` | ×3 | `window_scroll` | — | **form renders**; submit not exercised | Observed visually (render); `Not exercised` (submit) | `Pass for declared evidence` (render) + `Fidelity Gap` (submit) |
| `/blog/what-is-digital-marketing` | ×3 | `window_scroll` | rich text + YouTube embed | — | Observed visually | **`Accepted exception`** — JS `Unexpected token ')'`, **pre-existing at source** |
| Other 53 routes | — | — | — | — | **`HTTP-200 only`** | `Pass for declared evidence` (HTTP only) |

**The 53-route row is the key honesty caveat:** those routes were confirmed to serve HTTP 200 and to
have every referenced asset present on disk, but were **not opened in a browser**. That is
HTTP+asset evidence, not visual evidence, and is not claimed as such.

## Global checks

- [x] Typography and spacing — 36 self-hosted font files resolve; `fontStatus: loaded` in every cell
- [x] All kept same-site links resolve locally, point live/external intentionally, or are documented
- [x] Every in-scope structured module present on the correct route — incl. both forms and the
      48-item blog collection
- [x] No unresolved missing asset within exercised coverage — **0 local 404s** in the final pass
      (down from 51 distinct before the filename-encoding fix)
- [x] Performance observed — 128 MB / 822 files; settle ~1.5 s on `/`
- [x] Active module validation recorded: `multi-route.md` (63 routes, 3 CMS collections),
      `video.md` (one provider embed, preserved)
- [x] Asset Preservation Table statuses verified — no silent substitutions

## Static Mirror audit

- **Result tier: `Partial static mirror`.**
  27 of 30 browser cells pass. The 3 failing cells are one route × 3 viewports, failing on a
  JavaScript error that **reproduces identically on the live source** (evidence below). Because a
  declared matrix cell does not pass its gate, the honest tier is `Partial`, not
  `Validated static mirror — declared scope` — even though no failure is mirror-introduced.
- **Discovery coverage:** `Complete for declared triggers`. Trigger scan run across all 63 capture
  graphs: no WebGL/canvas/3D, no audio, no runtime-loaded chunks (`import(`, `new Worker`,
  `import.meta.url`, `.wasm` all absent). Video and multi-route triggered and their modules read.
- **Declared viewport (source of truth):** 1440×900.
- **Experience gate:** no preloader / entry gate / progress screen exists — not applicable.
- **Evidence gates:** boot ☑ / dependency ☑ / experience ☐ (n/a)
- **Asset count / size:** 822 files / 128 MB — see `mirror/mirror-manifest.json` (authoritative).
- **Missing or unresolved files within declared coverage:** none. 753/753 referenced assets resolve.
- **Remaining external requests:** all telemetry/analytics + one video embed + Calendly + social
  links. Zero external requests are required for the page to render. See table below.
- **Construction-time accommodations:** two, both path-resolution only — see below.

### Offline validation

**Not claimed.** A separate run with external network blocked has not been performed, so the
`Offline-validated` tier is not asserted. Static rendering does not depend on any external host
(all CSS/JS/images/fonts are local), so the expectation is that it would pass — but that is a
prediction, not evidence.

## Serving Contract

- **Serve command:** `python3 mirror/serve-local.py` (defaults to :8000), or
  `python3 <skill>/scripts/serve.py mirror --contract mirror/serve-contract.json --port <port>`
- **Production:** nginx, config at `deploy/nginx-pedicelmarketing.conf`
- **Web root:** `mirror/` · **Port:** 8137 for this validation run
- **Contract / manifest schema:** 1.3 — `mirror/serve-contract.json`, `mirror/mirror-manifest.json`
- **SPA fallback:** `Off` — confirmed multi-page; each route is a distinct server-rendered document
- **Route-map coverage:** 64 entries, no unresolved variants. Site root is stored at `_/index.html`;
  nginx maps it via `location = / { try_files /_/index.html =404; }`
- **Plain static hosting valid:** **yes** — after the filename-encoding accommodation below
  - Range/206: not needed (no media streaming)
  - Content-type replay: not needed (all extensions map conventionally)
  - Query-aware routing: not needed
- **`file://` support:** `Unsupported` — root-relative `/_external/...` paths require a server root
- Validation claims are conditional on this serving setup.

## Automated URL × Viewport Evidence

- **Result file:** `reports/viewports/viewport-results.json`
- **Matrix complete:** **no** — **27 passed / 30 expected**, 30/30 cells produced
- **Per-cell status and final URL recorded:** yes
- **Rejected challenge/login/consent/error/404 states:** none observed; no redirects; all cells HTTP 200
- **Scroll mechanisms exercised:** `window_scroll` (all cells)
- **Service worker:** none registered; `sw-allow` mode; no controller, no precache
- **Settling:** `DOMContentLoaded + bounded reported settling`; ~1529 ms observed on `/`
- **Source baseline:** `reports/viewports-source-baseline/viewport-results.json` — the live source
  page fails with the same `Unexpected token ')'` and the same `success: false`

## Construction-Time Accommodations

| Artifact / path | Phase / actor | Required local accommodation | Source / provenance evidence | Revalidation evidence |
| --- | --- | --- | --- | --- |
| `mirror/_external/**` (176 files) | `construction` / `deploy/fix_encoded_filenames.py` | Renamed percent-encoded filenames to their single-URL-decoded form. `mirror_assets.py` stores assets under the raw URL path, leaving a literal `%20` in the filename; every web server decodes the request path before the filesystem lookup, so those assets 404 despite downloading successfully. | `mirror-manifest.json#local_modifications`; 51 distinct 404s observed in `reports/serve.log` before the fix | 0 local 404s in `reports/serve-final.log` after |
| `mirror/**/*.html`, `*.css` (65 files) | `construction` / `deploy/rewrite_refs.py` | Point references at local paths (URL-quoted); strip `integrity`/`crossorigin` from now-local subresources (315); restore `data-wf-domain` to `www.pedicelmarketing.com` (63); drop the dead CDN `preconnect` (63). | `mirror-pristine/` retains the untouched download for diffing | Gates: 0 absolute CDN URLs, 0 noindex, 753/753 refs resolve |

Neither accommodation changes copy, branding, layout, media selection, or product behavior.
`deploy/build_mirror.sh` reproduces both deterministically from `mirror-pristine/`.

**SRI note:** stripping `integrity` is required, not cosmetic. The hash is computed over the CDN
bytes; served from our own origin, any byte-level difference makes the browser refuse the file and
the page renders unstyled.

## Interaction Coverage

**Exercised:** full-page window scroll on 10 routes × 3 viewports (IX2 scroll-triggered reveals
fire, lazy images resolve); font loading; nav rendering; both forms rendering at all 3 viewports.

**Not exercised — and why:**
- **Form submission.** Never exercised against the source: `capture_assets.py` does not submit
  forms by design, and submitting a real lead into the live Webflow endpoint would be wrong.
  Not exercisable against the mirror either — the forms are non-functional (see Fidelity Gaps).
  The relay in `deploy/form_handler.py` is untested end-to-end pending a Brevo API key.
- **53 of 63 routes in a browser.** HTTP-200 + asset-resolution evidence only.
- **Offline (network-blocked) run.** Not performed; `Offline-validated` tier not claimed.
- **Cross-browser.** Chromium only.

## External Runtime Dependencies

| Dependency | Handling | Fidelity impact | Evidence |
| --- | --- | --- | --- |
| `cdn.prod.website-files.com` (CSS, JS, 700 images, 36 fonts) | `Localized` | None — all local | 0 absolute CDN URLs remain |
| `d3e54v103j8qbb.cloudfront.net` (jQuery 3.5.1) | `Localized` | None | manifest `downloaded` |
| Webflow first-party analytics (`/g0lnomhfn3mg…` hashed path) | `Localized` (script asset) | None on render | round-4 acquisition; path verified stable across loads and routes |
| GA4 `G-YRE3WMB728` | `Kept external` | None on render — owner's own property, retained deliberately | inline script preserved |
| PostHog `phc_CoJfThYneBcnEpr7BhqZSDq8594ipjfAGlgubw5mgnt` | `Kept external` | None on render — owner's own | 252 skipped_external entries |
| Apollo `663143ad6c4a6401c7441d03` | `Kept external` | None on render — owner's own | skipped_external |
| YouTube via `cdn.embedly.com` (video `nIdmeZV9LVY`) | **`Embed`** | Provider-streamed; preserved as the original embed per `modules/video.md`. Never downloadable. | blog CMS rich text |
| `calendly.com/ikedinachi/meeting` | `Kept external` | Booking flow must stay live | outbound link |
| Social profile links | `Kept external` | None | outbound links |

**No external host is required for the page to render.** Telemetry failures are not fidelity
failures (SKILL.md, Analytics/tracking).

## Fidelity Gaps

| Feature | Missing / downgraded behavior | Constraint | Available baseline paths | Status |
| --- | --- | --- | --- | --- |
| **Form submission** (`wf-form-Audit-Form`, `wf-form-Email-Form-Version-Two`) | Both declare `method="get"` with **no `action`**. On Webflow, `webflow.js` AJAX-POSTs to Webflow's endpoint keyed on `data-wf-site`. Self-hosted that binding is gone and **the failure is silent** — the browser falls back to `method="get"`, reloads with fields in the query string, and the visitor believes it worked while the lead is discarded. | Webflow's form endpoint is bound to Webflow hosting | Relay to own endpoint (chosen); third-party form service; restore Webflow hosting | **`Pending`** — repaired in deployment Phase D via `deploy/form_handler.py` + `deploy/form-shim.js`, **not** in the baseline |
| YouTube video embed | None — preserved as original provider embed | Provider-streamed, never downloadable | Preserve embed (chosen) | `Accepted exception` |

## Pre-existing source defects (not mirror-introduced)

| Route | Defect | Evidence it is pre-existing |
| --- | --- | --- |
| `/blog/what-is-digital-marketing` | JS `Unexpected token ')'` — a syntax error inside CMS rich-text content | A `viewports.py` run against the **live source** returns the identical `page_errors: ["Unexpected token ')'"]` and `success: false` (`reports/viewports-source-baseline/`). Additionally, a script-block diff of `mirror-pristine/` vs the rewritten `mirror/` for this file shows **0 of 13 blocks differ** — the rewriter did not touch any script. |

Worth fixing at the CMS source, since it breaks JS on that post on the live site too.

## Project status

**`Partial`** — for the declared 63 routes and 3 viewports.

- **Completed:** 63/63 routes captured and serving 200; 818 assets localized with 753/753 references
  resolving; 36 fonts self-hosted; 27/30 browser cells pass; 0 local 404s; 0 absolute CDN URLs;
  0 noindex; reproducible build via `deploy/build_mirror.sh`.
- **Blocked:** nothing in the mirror. Deployment Phases B–E are blocked on Scaleway credentials
  (the value supplied was a 40-hex string, not Scaleway's access-key/secret-key/project/org format)
  and Phase D on a Brevo API key.
- **Approved baseline approximations:** none. No asset was approximated, recreated, or substituted.
- **Not exercised / unresolved:** form submission (source and mirror); 53 routes not opened in a
  browser; no offline network-blocked run; Chromium only; the `/blog/what-is-digital-marketing`
  source defect left as-is (faithful reproduction).
