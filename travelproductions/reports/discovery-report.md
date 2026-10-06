# Discovery Report

## Task

- **Source URL / evidence:** `https://travelproductions.film/es/inicio/` (supplied by operator).
  Evidence basis is the **live website** and **source inspection** — no user screen recordings or
  screenshots were provided, so those higher-priority evidence tiers are absent.
- **Requested baseline:** a faithful clone of the site, to be re-contented afterwards for a
  different client. Phase 1 (this report) is the baseline only.
- **Method:** `Static Mirror`
- **Why this method is suitable:** the deployed frontend is a conventional WordPress/Elementor page
  served as static HTML + CSS + JS with same-origin assets. Runtime capture succeeded on all 7
  routes with zero recorder errors and no challenge/consent/login gate. Editable Recreation was not
  needed — no *technical* blocker to capture exists.
- **Permission context (recorded in the manifest):** "reference/derivative baseline — structure to
  be re-contented for a different client; source copy, footage and licensed fonts not for
  redistribution". Per this copy's operating policy the supplied URL is treated as in scope for
  reference/derivative use; asset-hygiene rules remain in force and are enforced in the Asset
  Preservation Table.
- **Scope Classification:** `Multi-Route Site` — the **Spanish locale only** (7 routes).
- **Declared coverage:**
  - Routes: `/es/inicio/`, `/es/servicios/`, `/es/trabajos/`, `/es/sobre-nosotros/`,
    `/es/contacto/`, `/es/escena-3d/`, `/es/condiciones-legales/`
  - Viewports: `desktop` (1512×982) and `mobile`
  - Interactions: window scroll (14 steps/route) driving the GSAP ScrollTrigger reveals, Lenis
    momentum scrolling, nav hover, and the cookie-consent banner in its default (un-actioned) state.
  - **Explicitly out of scope:** the 18 English routes, and the 10 individual `/es/trabajos/<case>/`
    case-study detail pages. They were inventoried, not captured. A 7-route capture supports a
    7-route claim only.

## Observed runtime

- **Framework / build evidence:** WordPress 7.0.2, theme `hello-elementor`, **Elementor 4.2.1 +
  Elementor Pro**. Plugins observed: `connect-polylang-elementor` (locale routing),
  `mousewheel-smooth-scroll` (Lenis). Yoast SEO Premium 26.7 emits the metadata and JSON-LD graph.
  Google Site Kit 1.184.0 present.
- **Styling evidence:** Elementor's per-post generated CSS (`wp-content/uploads/elementor/css/post-*.css`,
  67 stylesheets captured across the 7 routes) plus theme and widget CSS. No CSS framework.
- **Animation system(s):** **GSAP 3.9.1 + ScrollTrigger** from cdnjs — the primary system, driving
  the scroll-reveal type and section choreography. **Lenis** momentum smooth-scroll wraps the whole
  document. One **Lottie** animation (rotating globe). Plus Elementor's own entrance animations.
  See `animation-audit.md`.
- **Observed routing behavior:** conventional multi-page server-rendered navigation — **no SPA**.
  Every route returns its own full HTML document; each is stored at its own path and no shared shell
  overwrites route-specific HTML. Locale routing is Polylang: `/` = English, `/es/` = Spanish, cross-
  linked with `hreflang` alternates.
- **Asset pipeline / CDN:** assets served from the origin under `wp-content/` and `wp-includes/`,
  with `?ver=` cache-busting query strings (which is why the manifest `route_map` is the authority
  for resolving them). Cloudflare fronts the origin (`static.cloudflareinsights.com` beacon
  observed). External: cdnjs (GSAP), `player.vimeo.com`, `cdn-luma.com`, Google telemetry.
- **Service worker / cache behavior observed:** **none.** No registration and no cache/precache
  evidence in any of the 7 captures. Nothing to bypass.
- **Supplied or authorized source repo evidence:** none. No repo link, no source maps, no exposed
  build manifest. The mirror is a deployed-runtime copy and is **not** recovered source.

## Editable Recreation evidence (fallback method only)

Not applicable — Static Mirror succeeded. No section was recreated from observation.

## Module Trigger Scan

| Trigger | Detected? | Module activated |
| --- | --- | --- |
| WebGL / canvas / 3D | **Yes** — `/es/escena-3d/` embeds a Luma Labs Gaussian-splat viewer (`cdn-luma.com/…/viewers/sparkles-…/viewer.js` + 6 scene artifacts). The `canvas` hits in the main document are WordPress's emoji-support feature detection, not a scene. | `modules/webgl.md` — reviewed. The scene is entirely inside a third-party iframe; there is no local WebGL context to preserve, so the requirement collapses to the `Embed` classification already recorded. |
| Audio | **No** — no audio files, no `AudioContext`, no mute/volume control observed on any route. | Not activated |
| Video | **Yes** — 21 self-hosted `.mp4` (background + cover video) and 147 Vimeo player embeds. | `modules/video.md` — activated |
| Multiple routes | **Yes** — `Multi-Route Site`, 7 declared ES routes; 35 pages exist site-wide. | `modules/multi-route.md` — activated |
| Runtime-loaded assets | **Yes** — 9 assets loaded during scroll on the homepage; the Lottie payload arrives as an XHR after first paint. | `modules/runtime-assets.md` — activated |

## Link & Route Inventory

| Link / route | Status | Structured content on target? | Evidence / reason |
| --- | --- | --- | --- |
| `/es/inicio/` | `Captured local` | Yes — hero, services, portfolio grid, client logo band, about band | Declared scope |
| `/es/servicios/` | `Captured local` | Yes — service breakdown | Declared scope |
| `/es/trabajos/` | `Captured local` | Yes — case-study index | Declared scope |
| `/es/sobre-nosotros/` | `Captured local` | Yes — team/about, Lottie globe | Declared scope |
| `/es/contacto/` | `Captured local` | Yes — contact block, `mailto:` CTAs | Declared scope |
| `/es/escena-3d/` | `Captured local` | Yes — Luma splat viewer iframe | Declared scope |
| `/es/condiciones-legales/` | `Captured local` | Yes — legal text | Declared scope |
| 10 × `/es/trabajos/<case-study>/` | `Out of scope` | Yes — per-case detail pages | Inventoried from `page-sitemap.xml` and in-page links; **not captured**. Links from the captured `/es/trabajos/` index therefore resolve to 404 locally. Recorded, not silently broken. |
| 18 × English routes (`/`, `/work/…`, `/services/`, `/about/`, `/contact/`, `/legals/`) | `Out of scope` | Yes | Operator scope is the Spanish locale. The `hreflang`/language-switcher links to them are dead locally. |
| `player.vimeo.com/video/…` (147) | `Intentional live external` | Video players | `Embed` — faithful only with network. See Asset Preservation Table. |
| `cdn-luma.com/…` splat viewer | `Intentional live external` | 3D scene | `Embed` — same. |
| `wa.me/…` (WhatsApp CTA), `instagram.com/travelproductions.film`, `linkedin.com/…` | `Intentional live external` | No | Outbound social/contact links; correct to leave live. |
| `mailto:hola@…`, `mailto:jose@…` | `Intentional live external` | No | Source's real addresses; replaced in phase 2. |
| `/wp-json/oembed/1.0/embed?url=…` | `Out of scope` | No | `<link rel="alternate">` metadata only; never fetched by the browser. Not captured; no impact. |
| `/es/feed/`, `/es/comments/feed/` | `Out of scope` | No | RSS metadata links, not part of the visual baseline. |

## Visible Module Inventory (source order — `/es/inicio/`)

| # | Module | Type | Visibility conditions | Evidence status |
| --- | --- | --- | --- | --- |
| 1 | Fixed top nav — TRABAJOS / SERVICIOS / wordmark / SOBRE NOSOTROS / CONTACTO | Navigation | Always; collapses to a hamburger + `Menú` / `Cerrar` overlay below `md` | Observed visually (both viewports) |
| 2 | `h1` "Productora y agencia digital especializada en turismo" | Display type | Always | Observed visually |
| 3 | Full-width background video reel | Video | Always; separate desktop (1080p) and mobile (720p) cuts | Observed visually; playback confirmed |
| 4 | Cookie-consent banner ("HOLA" / Rechazar / Ok) | Overlay | First visit, un-actioned | Observed visually. **Not exercised** — the capture never clicks through a consent control. |
| 5 | Three label/value rows — SERVICIOS · LOCALIZACIÓN · EXPERIENCIA | Scroll-reveal type | Reveals on scroll via ScrollTrigger | Interaction-tested (14-step scroll) |
| 6 | Portfolio grid — 7 offset case-study cards, each a cover video + title + location + service line | Media grid | Always; staggered offsets collapse to one column on mobile | Observed visually both viewports |
| 7 | "Ver casos de éxito" CTA | Button | Always | Observed visually; target is out of scope |
| 8 | Client logo band | Logo wall | Always | Observed visually |
| 9 | "SOBRE NOSOTROS" band over office video | Video band | Always | Observed visually |
| 10 | Footer — contact, `mailto:`, social | Footer | Always | Observed visually |

Per-route module inventories for the other 6 routes are covered by the paired screenshot evidence in
`reports/viewports-paired-*/`; no route contains a table, pricing grid, spec matrix or form POST
target. `/es/contacto/` uses `mailto:` links, **not** a submitting form — so there is no form action
to preserve or stub.

## Asset Graph (Static Mirror Mode)

- **`capture_assets.py` output:** `reports/{inicio,servicios,trabajos,sobre-nosotros,contacto,escena-3d,condiciones-legales}.asset-graph.json`
- **Capture graph schema / result:** schema 1.3, `ok` on all 7. `blocked_by_challenge: false`.
  0 recorder errors across all captures.
- **Status / final URL / redirects:** `200` on all 7; final URL equals requested URL; **no redirects**.
- **Eligible static GET/HEAD vs excluded:** see each graph's `summary` and the manifest's
  `skipped_*` lists — the machine record is authoritative. Excluded classes were: POST/non-GET
  telemetry beacons, GTM/analytics scripts, one XHR (`World-global-3.json`, later resolved through
  `--extra-urls`), provider-hosted Vimeo documents, and external hosts outside the authorized set.
- **Metadata references by state:** 42 total across the 7 routes, `Observed` / `Probed` / `Captured`
  tracked separately in `mirror-manifest.json.metadata_references`.
- **Scroll coverage mechanism:** `window_scroll` on every route (Lenis hijacks the *feel*, not the
  mechanism — `window.scrollY` still advances, so no wheel-driven virtual-scroll handling was needed).
- **Service worker:** none registered, no cache evidence, nothing controlled, nothing to bypass.
- **Same-origin assets:** 184 files / 86.2 MB captured. Notable: 21 `.mp4` (78.5 MB — 91% of the
  bytes), 4 Safiro webfont cuts, 67 Elementor stylesheets.
- **External providers detected:** Vimeo (147 player documents), Luma Labs (splat viewer),
  cdnjs (GSAP), Google Fonts, Google telemetry, Cloudflare Insights.
- **Blocked / unresolved:** the 147 Vimeo documents and 1 Luma viewer document remain unacquirable
  by design and are the sole cause of the pipeline's non-zero exit. Fully classified in the Asset
  Preservation Table; nothing is left `Unknown` except the never-requested font alternates.

## Static Mirror discovery evidence

- **Repo / source link found:** no. No repository link on any route.
- **Probe URLs checked:** `/robots.txt` → real `200` text file. `/sitemap_index.xml` → real `200`
  XML, pointing at `/page-sitemap.xml` → real `200` XML listing all 35 pages. No SPA false-200s
  encountered (this is not an SPA — content type and body verified on each).
- **Sitemap / routes found:** 35 pages site-wide; 18 ES, 17 EN. 7 declared in scope.
- **Manifest files found:** none (`/manifest.webmanifest`, `/asset-manifest.json`,
  `/_next/build-manifest.json`, `/.vite/manifest.json` are not applicable to this stack and were
  not present).
- **Source maps found:** none exposed.
- **Bundle scan findings:** captured JS scanned for `import(`, `new Worker`, `new URL(`,
  `import.meta.url`, `fetch(`, and the `.wasm/.glb/.gltf/.ktx/.hdr/.exr/.drc/.bin/.mp3/.ogg/.woff/.woff2`
  extension set. **No** dynamic imports, workers, WASM, 3D models, textures or audio resolved to
  same-origin URLs. The only runtime-loaded same-origin payload was the Lottie JSON, which was found
  and acquired. The WebGL surface lives entirely inside the Luma iframe.
- **Runtime interaction capture performed:** yes — 14-step window scroll per route at both viewports,
  DOM settling bounded at 6 s, plus a `--probe-metadata` pass. Consent-banner actioning and
  case-study navigation were **not** exercised (out of scope / never click through an access control).
- **Missing assets found from local server 404 logs:** after the origin-localization accommodation,
  **none**. Before it, every same-origin absolute reference (fonts, 4 videos, the Lottie) was being
  fetched cross-origin from the live site and CORS-refused — 1,382 references across 17 files.
- **Blocked or unexercised discovery paths:** the 10 case-study detail routes and 18 EN routes
  (out of scope); the consent banner's accept/reject states; Vimeo player internals; the Luma scene's
  own runtime.

## Construction-time accommodation

One accommodation, `phase: construction`, recorded in `mirror-manifest.json.local_modifications`
with per-file before/after hashes and reproducible via `python3 tools/localize_origin.py mirror`:

**Origin localization.** Elementor's output addresses its own assets absolutely
(`https://travelproductions.film/…`). Served from loopback, those requests left the mirror entirely
and cross-origin font loads were refused by CORS, so the baseline could not render its own
typography or media. The literal origin prefix (plain, escaped-JSON and protocol-relative forms) was
replaced with a root-relative path in 17 captured text files — 1,382 references. Every target was
already present locally and resolvable through `route_map`. Pre-edit copies are preserved in
`mirror-pristine/`. No copy, markup, layout, media selection or behaviour was changed.

## Findings

### Facts

- WordPress 7.0.2 + Elementor Pro 4.2.1 on `hello-elementor`; Polylang locale routing; not an SPA.
- All 7 declared routes captured at `200` with no redirects and 0 recorder errors; all 7 serve `200`
  locally and range-serve `206`.
- Motion is GSAP 3.9.1 + ScrollTrigger over Lenis smooth-scroll; both localized and working locally.
- Video is 91% of the captured bytes. 21 files self-hosted; 147 more players are Vimeo-streamed.
- `/es/escena-3d/` is a third-party Luma Labs splat viewer iframe, not a local WebGL scene.
- No service worker anywhere on the site.
- The display face is **Safiro**, a licensed retail typeface self-hosted by the source.
- `mouseleaveHandler is not defined` throws on the **live site** as well as the mirror — machine-
  confirmed as `exact_failure_matched_explicit_source_local_pair`, i.e. a pre-existing source bug,
  not a mirror defect.
- `/es/contacto/` has no submitting form — contact is `mailto:` only.

### Assumptions

- Safiro's licence is assumed non-transferable (standard for retail webfonts). The specific terms
  were not obtained; the conservative handling is applied regardless.
- The `ERR_ABORTED` on a handful of `.mp4` requests is assumed to be normal browser cancellation of
  partially-buffered media rather than a missing asset. Evidence for that reading: every one of those
  files exists locally at full size, returns `200`, and answers a byte-range request with `206`.
- The never-requested Roboto `@font-face` alternates are assumed unnecessary at the declared
  viewports because no fallback rendering was observed.

### Unknowns

- Whether the consent banner's accept/reject paths load additional assets — **not exercised**.
- Whether the 10 out-of-scope case-study routes introduce section types absent from the 7 captured
  routes. Likely (they are detail templates), but unverified.
- Whether any route behaves differently at viewports between the two declared sizes — not tested.
- The Vimeo players' and Luma viewer's internal behaviour under offline conditions is unknown
  because those states were never exercised; they are declared `Embed`, not validated.
