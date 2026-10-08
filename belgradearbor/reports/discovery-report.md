# Discovery Report — belgradearbor.rs (EN)

## Task

- Source URL / evidence: `https://belgradearbor.rs/en` (live website; source inspection of served HTML, CSS and JS bundles; runtime capture via `capture_assets.py`). No user-provided screen recordings or screenshots were supplied, so live-site observation is the top evidence tier in use.
- Requested baseline: faithful local baseline of the English marketing site, to be used as the starting point for a separate derived website (phase 2, NT Site Editor — not part of this delivery).
- Method: `Static Mirror`
- Why this method is suitable: the site is a deployed Next.js frontend whose HTML, CSS, JS, media and 3D assets are all reachable same-origin static GETs. Runtime capture was not blocked — every declared route returned `access.state: ok`, HTTP 200, with no challenge, login wall or consent gate. There was no technical reason to fall back to Editable Recreation.
- Permission context (user-stated): recorded in the manifest as `inspiration / non-commercial reference baseline for a derived site`.
- Scope Classification: `Multi-Route Site`
- Declared route, viewport, and interaction coverage:
  - **Routes (10, user-selected):** `/en`, `/en/3d`, `/en/residences`, `/en/retail-spaces`, `/en/business`, `/en/contact`, `/en/about-the-investor`, `/en/privacy-policy`, `/en/residences/a-1-01` (residence detail template sample), `/en/retail-spaces/b-lk1` (retail detail template sample).
  - **Explicitly out of scope:** the remaining 207 residence and 48 retail detail pages, and the entire `/sr` Serbian tree. The sitemap lists 526 URLs; 10 were declared.
  - **Viewports:** desktop, tablet, mobile presets (`viewports.py`), plus a desktop+mobile pass per route during capture.
  - **Interactions exercised:** full-page scroll to bottom (14–16 steps per pass, both viewports). Click, hover, menu-open, modal, form submission and 3D camera interaction were **not** exercised — see Findings › Unknowns.

## Observed runtime

- Framework / build evidence: Next.js App Router deployed on Vercel. Evidence: `/_next/static/chunks/*` bundle layout, `/_next/image` optimizer endpoint, `x-vercel-cache` / `x-vercel-id` response headers, `dpl_4chUSd6yu8wiVu9envanYd5CW6A4` deployment query token on every build asset, `turbopack-*.js` runtime chunk, `vary: rsc, next-router-state-tree, next-router-prefetch` RSC negotiation headers.
- Styling evidence: Tailwind CSS utility classes in the served markup (e.g. `block h-full w-full object-cover`, `absolute -top-35 left-1/2 w-[150%] max-w-none -translate-x-1/2`). 4–5 CSS chunks per route under `/_next/static/chunks/*.css`.
- Animation system(s): no third-party animation library was found in the bundles (no GSAP, Framer Motion, Lenis or Locomotive markers). Motion is CSS transition/transform based, plus the React Three Fiber scene on `/en/3d`. See `animation-audit.md`.
- Observed routing behavior: server-rendered document per route with client-side RSC navigation. `vary: rsc, next-router-prefetch` and the observed `fetch` requests to `/en`, `/en/contact` (RSC payloads) confirm client-side route prefetching.
- Asset pipeline / CDN: same-origin Vercel edge. Images are served both as raw `/…​.webp` files and through the `/_next/image?url=…&w=…&q=…&dpl=…` optimizer, which returns `image/jpeg`. Query string is part of resource identity — different `w` values are different resources.
- Service worker / cache behavior observed: no service worker registration observed in any capture pass.
- Supplied or authorized source repo evidence, if any: none. No source maps, no `package.json`, no repo link found (see Static Mirror discovery evidence).

## Editable Recreation evidence (fallback method only)

Not applicable — Static Mirror succeeded.

## Module Trigger Scan

| Trigger | Detected? (Yes / Suspected / No) | Module activated |
| --- | --- | --- |
| WebGL / canvas / 3D | **Yes** — `/en/3d` is a React Three Fiber scene loading 9 Draco-compressed GLB models, car textures and a drei HDR environment | `modules/webgl.md` (read) |
| Audio | **No** — no `<audio>` elements, no AudioContext, no audio files in any capture graph or bundle scan | not activated |
| Video | **Yes** — 7 `<video>` elements on `/en` plus `/home/popup.mp4` on other routes; sources injected at runtime | `modules/video.md` (read) |
| Multiple routes | **Yes** — `Multi-Route Site` scope, 10 declared routes, shared nav/footer layout, RSC client-side transitions | `modules/multi-route.md` (read) |
| Runtime-loaded assets | **Yes** — `<video preload="none">` with no SSR `<source>`; GLB/HDR loaded only after the 3D scene mounts; `_next/image` variants selected by viewport/DPR | `modules/runtime-assets.md` (read) |

## Link & Route Inventory

| Link / route | Status | Structured content on target? | Evidence / reason |
| --- | --- | --- | --- |
| `/en` | `Captured local` | Yes — residence-type cards, amenities, installment plan | Declared scope; HTTP 200, SHA-256 identical to live |
| `/en/3d` | `Captured local` | Yes — interactive 3D building explorer | Declared scope; 9 GLB + textures captured |
| `/en/residences` | `Captured local` | Yes — unit filter/listing grid | Declared scope |
| `/en/retail-spaces` | `Captured local` | Yes — retail unit listing grid | Declared scope |
| `/en/business` | `Captured local` | Yes — business-space sections, gallery | Declared scope |
| `/en/contact` | `Captured local` | Yes — 3 native `<form>` blocks | Declared scope; forms are native, not HubSpot-embedded |
| `/en/about-the-investor` | `Captured local` | Yes — investor profile, slide gallery | Declared scope |
| `/en/privacy-policy` | `Captured local` | Yes — legal/policy sections | Declared scope |
| `/en/residences/a-1-01` | `Captured local` | Yes — floorplan SVGs, unit spec block, PDF download | Declared scope; detail-page template sample |
| `/en/retail-spaces/b-lk1` | `Captured local` | Yes — layout SVGs, unit spec block | Declared scope; detail-page template sample |
| `/en/residences/<207 others>` | `Out of scope` | Yes (same template) | User declared 2 sample detail pages only |
| `/en/retail-spaces/<48 others>` | `Out of scope` | Yes (same template) | User declared 2 sample detail pages only |
| `/sr` and all `/sr/*` | `Out of scope` | Yes | User declared the EN tree only; language switcher will not resolve locally |
| `/en#Amenities`, `/en#Around` | `Captured local` | n/a — hash anchors into `/en` | Same-document anchors |
| `/pdf/ba-pp-brosura-eng.pdf` | `Captured local` | Yes — brochure PDF (7.0 MB) | Referenced from detail pages; acquired |
| `/pdf/gradjevinska-dozvola.pdf` | `Captured local` | Yes — building permit PDF (143 KB) | Linked from `/en`; acquired |
| `https://arbor.square43.com/...` | `Intentional live external` | n/a | Staging host leaking into `canonical`, `hreflang`, OG/Twitter image metadata on the production site — a source-site quirk, reproduced as-is |
| `https://www.facebook.com/belgradearbor/`, `instagram.com/belgradearbor/`, `linkedin.com/company/belgrade-arbor` | `Intentional live external` | n/a | Social profile links |
| `https://www.poverenik.rs/...` | `Intentional live external` | n/a | Serbian data-protection authority, linked from privacy policy |

## Visible Module Inventory (source order)

Homepage `/en`, in source order:

| # | Module | Type | Visibility conditions | Evidence status |
| --- | --- | --- | --- | --- |
| 1 | Header / nav + language switcher (ENG/SRB) + Inquire CTA | Navigation | Always; mobile collapses to menu button | DOM+assets confirmed |
| 2 | Hero with background video | Video hero | Always; `hero.mp4` desktop / `hero-m.webm` mobile | DOM+assets confirmed |
| 3 | Introduction + leaf imagery (4 webp) | Content | Always | DOM+assets confirmed |
| 4 | Roots section (mask SVGs + `image1.mp4`) | Video/mask | Scroll-triggered load | DOM+assets confirmed |
| 5 | Horizontal scroll gallery (3 optimizer images) | Scroll-linked gallery | Scroll-triggered | DOM+assets confirmed |
| 6 | Residences overview + `interior.mp4` | Video + content | Scroll-triggered | DOM+assets confirmed |
| 7 | Residence-type cards (Studio…Three Bedroom, unit counts) | Structured data grid | Always | DOM+assets confirmed |
| 8 | Business section + `business.mp4` | Video + content | Scroll-triggered | DOM+assets confirmed |
| 9 | Amenities + `amenities.mp4` / `amenities-bg.webp` | Video + content | Scroll-triggered | DOM+assets confirmed |
| 10 | Location / Around + `location.mp4`, map imagery | Video + content | Scroll-triggered | DOM+assets confirmed |
| 11 | Installment plan | Structured content | Always | DOM+assets confirmed |
| 12 | 3D Experience teaser → `/en/3d` | CTA | Always | DOM+assets confirmed |
| 13 | Inquiry form | Form | Always | DOM confirmed; **not submitted** |
| 14 | Footer (front/tree-l/tree-r optimizer images, social, legal) | Footer | Always | DOM+assets confirmed |
| — | `popup.mp4` inquiry/modal video (19.3 MB) | Video modal | **Interaction-gated — not exercised** | Asset captured; trigger not exercised |

Detail-page template (`/en/residences/a-1-01`, `/en/retail-spaces/b-lk1`): hero, gallery (8 webp), floorplan SVG set (`main.svg` + `1..7.svg` with `-m` mobile variants), unit spec block, brochure PDF CTA, message/plant imagery, inquiry form.

## Asset Graph (Static Mirror Mode)

- `capture_assets.py` output files: `reports/{en, en-3d, en-residences, en-retail-spaces, en-business, en-contact, en-about-the-investor, en-privacy-policy, en-residences-a-1-01, en-retail-spaces-b-lk1}.asset-graph.json` (schema 1.3, 10 files).
- Capture graph schema / result: schema 1.3; **`ok` for all 10 routes**. No `blocked_by_challenge`, `blocked_by_login`, `blocked_by_consent` or `navigation_error`.
- Initial status / final status / final URL / redirect evidence: every route `initial_status 200` → `final_status 200`, final URL identical to requested URL, **zero redirects**, zero unauthorized redirects.
- Automatically eligible static GET/HEAD count per route: `/en` 95, `a-1-01` 91, `b-lk1` 87, `/en/3d` 63, `/en/residences` 52, `/en/retail-spaces` 52, `/en/about-the-investor` 52, `/en/business` 48, `/en/privacy-policy` 38, `/en/contact` 38. Excluded across the run: 124 non-GET/HEAD requests, 88 telemetry requests, 200 records carrying the `personalized_data` classification (see Findings › Facts #1).
- Metadata references by state: 30 total recorded across the 10 graphs, `Observed` / `Probed` / `Captured` tracked separately in each graph.
- Scroll coverage mechanism: `window_scroll` on both desktop and mobile passes for all 10 routes. No virtual/internal-container scrolling detected.
- Service-worker registrations, cache/precache evidence, controlled result: none observed on any route.
- Same-origin assets: **496 files acquired**, `route_map` has 496 exact path+query entries, 169 MB on disk. Notable — 9 GLB models (63 MB total, largest `nature.glb` 19.3 MB), 8 video files (52 MB, largest `popup.mp4` 19.3 MB), 5 font files, 301 `_next/image` optimizer variants, 2 PDFs (7.1 MB).
- External providers detected: Google Tag Manager, Google Ads/DoubleClick, Meta (Facebook) pixel, HubSpot (analytics + cookie banner), Google Analytics — all telemetry, none replayed. Plus 4 **functional** external assets for the 3D scene (see below).
- Blocked / unresolved: none blocked. 4 external functional dependencies deliberately kept external — `www.gstatic.com` Draco decoder (`draco_decoder.wasm`, `draco_wasm_wrapper.js`), `raw.githack.com` / `raw.githubusercontent.com` drei-assets `hdri/kiara_1_dawn_1k.hdr` and `cloud.png`.

## Static Mirror discovery evidence

- Repo / source link found: **no**. No repository link in any page.
- Probe URLs checked (+ real result, noting SPA false-200s): `/robots.txt` → **404** (returns a 70 KB HTML error document, not a robots file — a false-200-shaped result confirmed by content type `text/html` and 404 status). `/sitemap.xml` → **real 200, `application/xml`, 90.5 KB, 526 `<loc>` entries** — verified genuine by content type and body. `/manifest.webmanifest` → **404** (HTML error document).
- Sitemap / routes found: 526 URLs — 263 EN + 263 SR. Route families: 208 `/en/residences/*`, 49 `/en/retail-spaces/*`, 6 top-level EN routes. Sitemap `<loc>` values point at the **staging host** `arbor.square43.com`, not the production domain.
- Manifest files found: none (`/asset-manifest.json`, `/.vite/manifest.json`, `/_next/build-manifest.json`, `/package.json` not exposed).
- Source maps found: none.
- Bundle scan findings: 46 downloaded JS chunks scanned for `import(`, `new Worker`, `new URL(`, `import.meta.url`, `fetch(` and the extension set. Found **96 hardcoded same-origin asset paths**, of which 64 were already mirrored and 32 were not. Of those 32: **26 confirmed HTTP 200 at origin and were acquired**; **6 (`/px.png`, `/nx.png`, `/py.png`, `/ny.png`, `/pz.png`, `/nz.png`) are drei `<Environment>` library default constants, not site assets** — they 404 at origin and are never requested, because the site passes a `preset` which switches the loader to the external HDR path. No `.wasm`, `.ktx2`, `.drc` or `.bin` same-origin assets found; the only WASM is the external Draco decoder.
- Runtime interaction capture performed, with declared trigger coverage: full-page scroll at desktop and mobile viewports per route, 14–16 steps, 700–800 ms per step, bounded settle ≤6 s. Scroll revealed 2–43 additional assets per route (`/en/residences` highest at 43). Click/hover/modal/form/3D-camera interactions were not exercised.
- Missing assets found from local server 404 logs and reference diffing: **222 mirror-introduced gaps found and resolved** — 218 `_next/image` srcset variants referenced by the captured HTML but never requested at the capture viewport (these would have produced broken images at other viewports/DPRs), 2 PDFs, 1 JS chunk, 1 image. After acquisition, a full re-diff of all 410 HTML- and bundle-referenced assets against the `route_map` returned **0 missing**.
- Blocked or unexercised discovery paths: interaction-gated states (see Unknowns).

## Findings

### Facts

1. **Every route document was classified `personalized_data` by the capture tool and could not be auto-acquired.** The sole trigger is the response header `cache-control: private, no-cache, no-store, max-age=0, must-revalidate`, recorded in each graph as `privacy_signals: ["cache_control_private"]`. This was verified to be a **false positive**: `/en` returns a byte-identical body (SHA-256 `a300cdce26bf…`) across three fetch conditions — anonymous, with a fabricated `sessionid`+`hubspotutk` cookie, and with a different User-Agent. The only `Set-Cookie` is `NEXT_LOCALE=en`, a locale preference rather than a user identity. The 10 documents were therefore declared through the sanctioned `--extra-urls` path with `"required": true` and the verification evidence recorded in each record's `acquisition.reason`; all 10 downloaded and are SHA-256 identical to live.
2. **`mirror_assets.py` exits 2 on every run and will not clear.** `collect_records` forces the requested page document to `required: true` but explicitly refuses to override an `acquisition.automatic: false` flag carried from the capture graph, so each of the 10 graph-derived document records is permanently counted as a required failure — even though the same URL is successfully acquired via the declared `--extra-urls` record. Consequence: the tool skips its completion steps, so **`serve-contract.json` and `serve-local.py` were never emitted** and `generated_artifacts` is empty. `serve.py` accepts `--contract` as optional and reads `mirror-manifest.json.route_map` directly, which is the serving path used here.
3. All 10 declared routes captured cleanly: `access.state: ok`, HTTP 200, zero redirects, no challenge/login/consent gate, no service worker.
4. 496 same-origin assets acquired, 169 MB, `route_map` 496 entries, 0 integrity errors across all runs.
5. `_next/image` is query-identity-sensitive: 301 distinct optimizer URLs are referenced by the captured HTML, differing only in `w`. All 301 are mapped.
6. Videos are runtime-injected: all `<video>` elements ship `preload="none"` with **no `<source>` child in the SSR HTML**; sources are attached by client JS. 8 video files totalling 52 MB were captured. Origin serves them with HTTP 206 on a Range request; the local server does too.
7. `/en/3d` is a React Three Fiber scene. Its SSR body contains only the nav — everything else is client-rendered. It loads 9 Draco-compressed GLB models (63 MB) and 4 car textures from `/glb/test2/`.
8. Fonts are all self-hosted same-origin: **Work Sans** (2 woff2 subsets, SIL Open Font License) and **PP Editorial Old** (3 OTF weights — Regular, Ultralight, UltralightItalic — a **commercial Pangram Pangram typeface**).
9. No accommodations were required. `local_modifications`, `construction_provenance` and `generated_artifacts` are all empty — the mirror boots exactly as downloaded.
10. The production site's `canonical`, `hreflang`, OpenGraph and Twitter image metadata point at the staging host `arbor.square43.com`, as does every `<loc>` in the sitemap. Reproduced as-is per the no-redesign rule.

### Assumptions

1. The two sampled detail pages (`a-1-01`, `b-lk1`) are representative of all 255 detail pages. Based on shared asset paths (`/single-appartment/*`, `/single-business/*`) and identical component structure, not on inspecting the other 255.
2. `hero-m.webm` is the mobile hero variant and `hero.mp4` the desktop one, inferred from which viewport pass requested each.
3. The drei-assets and Draco decoder URLs are stable. `raw.githack.com` is a community CDN with no uptime guarantee — flagged for phase 2 rather than changed here.

### Unknowns

1. **Interaction-gated states were not exercised** and are therefore unverified: mobile menu open, the `popup.mp4` modal (19.3 MB, captured but its trigger never fired), form submission, residence/retail listing filters, gallery navigation, and all 3D camera/selection interaction on `/en/3d`. Assets these paths might load beyond what scroll revealed are unknown.
2. Whether `/en/3d` reaches a usable terminal render state locally — pending the browser validation matrix; recorded in `validation-report.md`, not assumed here.
3. Whether client-side RSC navigation works locally. Next.js router prefetches RSC payloads for `vary: rsc` variants of each route; those responses were classified `personalized_data` and are not in the mirror. Full-page loads of every route work; in-app link clicks may fall back or fail.
4. The exact `q=` (quality) and `w=` variant set the optimizer would produce at untested DPRs. 301 observed variants are covered; a device requesting an unobserved `w` would receive an honest 404.
5. Licence status of the site's photography, video and 3D models. Not determinable from the runtime; all are same-origin originals and must be treated as the client's property, not reusable in a derived site without permission.
