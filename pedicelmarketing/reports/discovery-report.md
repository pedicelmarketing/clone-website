# Discovery Report

## Task

- **Source URL / evidence:** `https://new-pedicel-website.webflow.io/` (Webflow staging origin for
  the `pedicelmarketing.com` project, site ID `64a2995238dba40820b37689`).
  The production host `www.pedicelmarketing.com` is **offline** — it returns HTTP 404 from Webflow's
  edge and the apex returns 403, because the custom-domain binding was removed from the Webflow
  project. DNS still resolves `www` to `proxy-ssl.webflow.com` via Hostinger's parking nameservers.
  The staging origin is therefore the only live source of truth for the site's current content.
- **Requested baseline:** faithful multi-route static mirror of the whole site, to be self-hosted on
  a Scaleway instance so `pedicelmarketing.com` can be restored off Webflow.
- **Method:** `Static Mirror`
- **Why this method is suitable:** the deployed runtime is reachable and every in-scope route returns
  HTTP 200 on the staging origin; the Webflow asset CDN also still serves 200. Runtime capture is
  not blocked (no challenge, login, or consent gate observed), so the Editable Recreation fallback
  is not warranted.
- **Permission context (user-stated):** owner-operated restore of the user's own site. The git
  remote for this workspace is `github.com/pedicelmarketing/clone-website` and the prior manifest
  recorded `"Owner confirmed"`. Recorded in the manifest as
  `"owner-operated restore of pedicelmarketing.com"`.
- **Scope Classification:** `Multi-Route Site` (Webflow CMS-driven, 3 collections)
- **Declared route, viewport, and interaction coverage:**
  - **Routes:** 63 — 7 top-level, 4 service detail, 4 project case studies, 48 blog posts.
    Derived by parsing every `<a href>` in the previously captured HTML and filtering to same-site
    targets; all 63 independently confirmed HTTP 200 against the staging origin before capture.
  - **Viewports:** mobile / tablet / desktop via `viewports.py`.
  - **Interactions:** window scroll (Webflow IX2 scroll-triggered reveals), nav menu, and the two
    form surfaces. Form *submission* is deliberately not exercised against the source — the capture
    tool never submits forms.

## Observed runtime

- **Framework / build evidence:** Webflow. `<html data-wf-domain data-wf-page data-wf-site>` on
  every route; `<!-- Last Published: Wed Feb 04 2026 10:22:17 GMT+0000 -->`; Webflow class
  conventions (`w-input`, `w-button`, `w-form-done`, `w-form-fail`) and `data-w-id` IX2 attributes.
- **Styling evidence:** one shared stylesheet,
  `cdn.prod.website-files.com/64a2995238dba40820b37689/css/new-pedicel-website.webflow.shared.3140baf36.css`
  (222,999 bytes), carrying an SRI hash (`sha384-MUC682O4yu6l…`) and `crossorigin="anonymous"`.
- **Animation system(s):** Webflow IX2 (interactions/animations bundled in the Webflow JS chunks).
  Scroll-triggered reveals only; no timeline/scrub library, no GSAP, no Lenis.
- **Observed routing behavior:** classic multi-page. Directory-index clean URLs
  (`/audit` → `audit/index.html`). **Not** an SPA — each route is a distinct server-rendered
  document, so SPA fallback must stay off in the serving contract.
- **Asset pipeline / CDN:** `cdn.prod.website-files.com` (Webflow's asset bucket) for CSS, JS,
  images and fonts; `d3e54v103j8qbb.cloudfront.net` for jQuery 3.5.1.
- **Service worker / cache behavior observed:** none registered.
- **Supplied or authorized source repo evidence, if any:** none. Webflow does not expose source.

## Editable Recreation evidence (fallback method only)

Not applicable — Static Mirror succeeded.

## Module Trigger Scan

| Trigger | Detected? | Module activated |
| --- | --- | --- |
| WebGL / canvas / 3D | **No** — zero `<canvas>`, no three.js/WebGL/GLSL/`.glb`/Draco signals across all capture graphs | not read |
| Audio | **No** — zero `<audio>`, no AudioContext, no `.mp3`/`.ogg`/`.wav` | not read |
| Video | **Yes** — one Embedly-wrapped YouTube embed (video `nIdmeZV9LVY`) inside blog CMS rich text, plus 4 `i.ytimg.com` poster thumbnails. No `<video>` elements, no background/scroll-linked video | `modules/video.md` **read** |
| Multiple routes | **Yes** — 63 routes across 3 Webflow CMS collections (blog, projects, services) | `modules/multi-route.md` **read** |
| Runtime-loaded assets | **No** — no `import(`, `new Worker`, `import.meta.url`, or `.wasm` in any graph. Webflow ships static JS chunks | not read |

## Link & Route Inventory

All 63 same-site routes are **in scope** and verified HTTP 200 on the staging origin prior to
capture. Grouped rather than enumerated per row; the machine-authoritative per-route record is
`mirror-manifest.json#route_map` and `reports/graphs/*.asset-graph.json`.

| Link / route | Status | Structured content on target? | Evidence / reason |
| --- | --- | --- | --- |
| `/` | `Captured local` | Hero, service cards, testimonial slider | HTTP 200; captured |
| `/about-our-marketing-agency`, `/services`, `/our-marketing-portfolio`, `/blog`, `/contact-us`, `/audit` | `Captured local` (6) | `/audit` + `/contact-us` carry **forms**; `/blog` is a 48-item listing | all HTTP 200; captured |
| `/service-brand-presence`, `/service-lead-generation`, `/service-social-media`, `/service-web-development` | `Captured local` (4) | service detail copy | CMS collection; all HTTP 200 |
| `/projects/coeo`, `/projects/isnmedical`, `/projects/latabernafantastica`, `/projects/sana` | `Captured local` (4) | case-study layouts | CMS collection; all HTTP 200 |
| `/blog/<48 slugs>` | `Captured local` (48) | CMS rich text; one carries the YouTube embed | CMS collection; all HTTP 200 |
| `https://calendly.com/ikedinachi/meeting` | `Intentional live external` | booking flow | third-party booking; must stay live |
| `cdn.embedly.com` → YouTube `nIdmeZV9LVY` | `Embed` | provider-streamed video | per `modules/video.md`, preserve the original provider embed; never download |
| Social profiles (LinkedIn, Instagram, Facebook, X, YouTube) | `Intentional live external` | n/a | outbound profile links |
| Form actions (`wf-form-Audit-Form`, `wf-form-Email-Form-Version-Two`) | **`Blocked`** | n/a | **no `action` attribute**; Webflow's JS AJAX-POSTs to Webflow keyed on the site ID, which only works on Webflow hosting. See Fidelity Gap below |

## Visible Module Inventory (source order)

| # | Module | Type | Visibility conditions | Evidence status |
| --- | --- | --- | --- | --- |
| 1 | Nav bar + dropdown | navigation | all routes; mobile burger under breakpoint | Observed visually |
| 2 | Hero | content | `/` | Observed visually |
| 3 | Service cards | grid | `/`, `/services` | Observed visually |
| 4 | Portfolio / case-study grid | grid | `/`, `/our-marketing-portfolio` | Observed visually |
| 5 | Testimonials | slider | `/`, `/about-our-marketing-agency` | Observed visually |
| 6 | Blog listing (48 items) | collection list | `/blog` | DOM+assets confirmed |
| 7 | Blog post rich text | CMS rich text | `/blog/*`; one contains the YouTube embed | DOM+assets confirmed |
| 8 | Audit form (7 fields) | **form** | `/audit` | DOM confirmed; **submission blocked** |
| 9 | Contact form (4 fields) | **form** | `/contact-us` | DOM confirmed; **submission blocked** |
| 10 | Footer + social links | navigation | all routes | Observed visually |

## Asset Graph (Static Mirror Mode)

- **`capture_assets.py` output files:** `reports/graphs/*.asset-graph.json` — one per route, 63 total.
- **Capture graph schema / result:** schema `1.3`; all 63 `ok`. No `blocked_by_challenge`,
  `blocked_by_login`, `blocked_by_consent`, or `navigation_error`.
- **Scroll coverage mechanism:** `window_scroll` (native document scroll; no virtual-scroll library).
- **Service-worker registrations:** none observed; no cache/precache evidence.
- **External providers detected:** `cdn.prod.website-files.com` (assets),
  `d3e54v103j8qbb.cloudfront.net` (jQuery), `us-assets.i.posthog.com` / `us.i.posthog.com`
  (PostHog), `www.googletagmanager.com` + `analytics.google.com` + `stats.g.doubleclick.net` (GA4),
  `assets.apollo.io` + `aplo-evnt.com` (Apollo), `connect.facebook.net`, `cdn.embedly.com` +
  `i.ytimg.com` (video embed), `calendly.com`.
- **Counts, hashes, failures, skip reasons:** see `mirror-manifest.json` (machine-authoritative);
  not restated here per workspace convention.

## Static Mirror discovery evidence

- **Repo / source link found:** no — Webflow does not expose source.
- **Probe URLs checked:** `/sitemap.xml` → **404** on the staging origin (real 404, not an SPA
  false-200: empty body, no `<loc>` elements). `/robots.txt` → empty body.
  Route discovery therefore came from link extraction, not a sitemap.
- **Sitemap / routes found:** no sitemap. 63 routes derived from `<a href>` extraction across the 7
  previously captured pages, then each independently confirmed 200 against staging.
- **Manifest files found:** none.
- **Source maps found:** none exposed.
- **Bundle scan findings:** no dynamic imports, workers, WASM, models, textures, or audio.
  Fonts are referenced from within the shared CSS (not from HTML), so they do **not** all appear as
  first-load runtime requests — a page fetches only the weights it renders. All 36 font files were
  therefore enumerated from `url()` declarations in the stylesheet and routed through
  `reports/extra-urls.jsonl` with `"required": true`, per the SKILL.md rule that supplementary
  acquisitions go through the pipeline rather than a side channel.
- **Runtime interaction capture performed:** window scroll exercised per route by `capture_assets.py`
  (`--scroll-steps` default), which is what reveals Webflow IX2 scroll-triggered image loads.
- **Missing assets found from local server 404 logs:** recorded during Phase A7 validation.
- **Blocked or unexercised discovery paths:** form submission (never exercised against the source,
  by tool design and by intent — submitting a real lead into the live Webflow endpoint would be
  wrong). Authenticated/admin areas: none exist.

## Findings

### Facts

- `www.pedicelmarketing.com` is offline (404 from Webflow's edge); the apex returns 403. There is no
  live production site to disrupt during cutover.
- The Webflow project remains published at `new-pedicel-website.webflow.io` and serves all 63 routes.
- The Webflow asset CDN still serves 200, so full asset localisation is achievable.
- The staging origin carries **no** `noindex` meta, **no** `X-Robots-Tag` header, and **no**
  canonical tag — verified across `/`, `/blog`, `/audit`, `/projects/coeo` and a blog post. The
  usual Webflow staging `noindex` is absent, so capture does not risk importing one. This is
  re-asserted as a hard gate in `deploy/rewrite_refs.py`.
- The prior mirror in `mirror-stale-20260801/` had `allowed_external_hosts: []` and therefore
  downloaded exactly one file; it is 7 pages with zero local assets and a stale manifest describing
  only `/audit`. It is retained as a snapshot, not used as a baseline.
- Fonts: 36 `.otf` files — 18 Poppins (SIL OFL) and 18 Switzer (Indian Type Foundry).
- Tracking IDs belong to the site owner and are retained deliberately as part of the faithful
  restore: GA4 `G-YRE3WMB728`, PostHog `phc_CoJfThYneBcnEpr7BhqZSDq8594ipjfAGlgubw5mgnt`,
  Apollo `663143ad6c4a6401c7441d03`, and a Google Search Console verification token.

### Assumptions

- The 63 routes constitute the complete site. This is derived from exhaustive link extraction, but
  with no sitemap available an orphan route linked from nowhere would not be discovered.
- Switzer is covered by a licence the site owner already holds (user-stated). Recorded as the basis
  for classifying it `Local Copy` rather than `Kept External`.

### Unknowns

- Whether the Webflow project will remain published. The staging origin is the only remaining source
  for the 48 blog posts and 8 other CMS routes; if it is unpublished, re-capture becomes impossible.
  This is why capture was run first.
- Whether any blog post references an asset that only loads on an interaction not exercised by the
  scroll pass. Phase A7's local 404-log sweep is the check for this.

### Fidelity Gap (declared up front)

**Form submission is blocked, and it fails silently.** Both forms declare `method="get"` with **no
`action`**. On Webflow hosting, `webflow.js` intercepts submit and AJAX-POSTs to Webflow's endpoint
keyed on `data-wf-site`. Self-hosted, that binding does not exist. The browser falls back to the
declared `method="get"`, reloads the same page with the field values in the query string, and shows
no error — the visitor believes the submission succeeded while the lead is discarded.

This is a `Fidelity Gap`, not a Pass, and it is **not** resolved within the mirror. It is repaired
in the separate deployment phase by pointing both forms at a local handler that relays through
Brevo — recorded there, not smuggled into the baseline.
