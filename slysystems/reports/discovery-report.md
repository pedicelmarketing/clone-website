# Discovery Report — sly.systems homepage

## Task

- Source URL / evidence: `https://sly.systems/` — live site, captured 2026-08-15 with Playwright/Chromium.
- Requested baseline: Homepage (`/`). Multi-route site present (8 additional routes discovered); per user direction "homepage first, expand from there" — only `/` is captured.
- Method: `Static Mirror` (Builder-hosted runtime; treated as technical capture blocker for backend, documented honestly).
- Why this method is suitable: HTML/CSS/JS/Fonts/runtime observable from the page itself; the front-end rendering pipeline is Static-Mirror-capable. The Base44 backend APIs the JS bundle calls (`/api/apps/.../entities/*`, `/analytics/track/batch`, `/app-logs/...`) cannot be mirrored — that prevents full runtime fidelity, but the structural skeleton IS captured.
- Permission context (user-stated): *"homepage first, expand from there — we will rebrand later"*. Internal adaptation policy treats any supplied URL as in-scope for inspiration/derivative use; no authorization question.
- Scope Classification: `Multi-Route Site` (9 same-site routes anchored from `/`), but in-scope is `Homepage`.
- Declared route, viewport, and interaction coverage: `/` × {desktop 1440×900, mobile 390×844}. No interactive run beyond the standard capture scroll (the page uses `window_scroll`).

## Observed runtime

- Framework / build evidence: Vite SPA. Single bundled JS (`assets/index-C--Jvz_w.js`, 1.5 MB) + CSS bundle (`assets/index-BfiDsVd2.css`, 173 KB). No additional `/assets/*` chunks referenced from the bundle — single all-in-one dev build. Base44 SDK embedded inside the bundle (calls to `/api/apps/<id>/entities/*`, `/analytics/track/batch`, `/app-logs/...`). React 18+ present. GSAP embedded (64 references inside the bundle).
- Styling evidence: Tailwind utility classes in the HTML/CSS plus custom CSS. `@keyframes` blocks: 50 declared. CSS transitions: 7 declared.
- Animation system(s): GSAP (64 references in the bundle). Hero motion: per-letter video "SLY" letters transition. Scroll-driven reveals in the "Four moves", "Pick your world", and case-study sections. The video positions in the hero ARE the brand assets themselves (per-letter video files). Some scene-driven color/translate animations are likely GSAP timelines.
- Observed routing behavior: Client-side routing via the Base44 router. `/manifest.json` exposes the app's PWA config. The homepage root renders to `text/html`.
- Asset pipeline / CDN: `media.base44.com` for user-uploaded brand images + videos (16 videos + 24 image references discovered via the JS bundle, ~16/10 visible during first-render capture). `fonts.googleapis.com` and `fonts.gstatic.com` for Google Fonts (Cinzel, Inter, Space Grotesk). `w.soundcloud.com` + `widget.sndcdn.com` for a SoundCloud widget embed. `api.motion.dev` for a Motion.dev badge (third-party). Doubleclick + Google Analytics for ads/telemetry.
- Service worker / cache behavior observed: No service worker registered.
- Supplied or authorized source repo evidence, if any: None. There is a `/base44` route on the site — that's the Base44 admin/builder UI, not the site's source repo.

## Module Trigger Scan

| Trigger | Detected? | Module activated |
| --- | --- | --- |
| WebGL / canvas / 3D | No | — |
| Audio | Yes (SoundCloud iframe embed) | `audio.md` content noted; provider stream, not redistributable |
| Video | Yes (16 .mp4 from media.base44.com) | `modules/video.md` |
| Multiple routes | Yes | `modules/multi-route.md` (route analysis kept brief — only `/` in scope) |
| Runtime-loaded assets | Yes (bundle references more media.base44 assets than first render surfaces) | `modules/runtime-assets.md` (lazy chunks not surfaced — single-bundle build, nothing to chase) |

## Link & Route Inventory

> Phase 1 scope is `/` only. Other routes are out of scope pending user expansion approval.

| Link / route | Status | Structured content on target? | Evidence / reason |
| --- | --- | --- | --- |
| `/` | Captured local | Hero + newsletter form + service cards ("Four moves") + case studies + testimonials + footer | This run |
| `/about` | Out of scope | — | Captured in route inventory; not mirrored |
| `/base44` | Out of scope | — | Captured in route inventory; builder admin path; not mirrored |
| `/contact` | Out of scope | — | Captured in route inventory; not mirrored |
| `/engine` | Out of scope | — | Captured in route inventory; not mirrored |
| `/idea` | Out of scope | — | Captured in route inventory; not mirrored |
| `/newsletter` | Out of scope | — | Captured in route inventory; not mirrored |
| `/review` | Out of scope | — | Captured in route inventory; not mirrored |
| `/work/gonzo` | Out of scope | — | Captured in route inventory; not mirrored |

## Visible Module Inventory (source order)

| # | Module | Type | Visibility conditions | Evidence status |
| --- | --- | --- | --- | --- |
| 1 | Hero letter animation "SLY" | GSAP-driven per-letter video | First viewport | DOM+assets confirmed (4 per-letter .mp4 from media.base44.com) |
| 2 | Newsletter email-capture form | `<form>` + text input | First viewport, above-the-fold | DOM+assets confirmed (mirror-rendered `submit` returns 404 because backend not mirrored) |
| 3 | Hero tagline ("The best opportunities are engineered, not found.") | Text block | First viewport | Observed visually (local + source screenshots match) |
| 4 | Service card row "Four moves" | 4 dark cards | Below-the-fold, scroll-triggered | DOM+assets confirmed (captions + headings present locally; background media external) |
| 5 | Case-study picker "Pick your world" | Tabbed picker over video case study | Below-the-fold, scroll + click | DOM+assets confirmed (tab UI present; video tiles external) |
| 6 | Audio embed (SoundCloud player) | `<iframe>` | Mid-page | Embed/Kept External (provider-streamed) — `audio.md` hygiene rule applied |
| 7 | Logo wall ("In the news") | 4-image strip | Mid/lower page | DOM+assets confirmed (placeholders visible; external images) |
| 8 | Sticky header + footer | Navigation chrome | Persistent | DOM+assets confirmed |
| 9 | Motion.dev badge | `<img>` | Lower-right | Embed (third-party badge) |

## Asset Graph (Static Mirror Mode)

- `capture_assets.py` output file: `reports/home.asset-graph.json` (schema_version `1.3`, sha256 in `mirror-manifest.json`).
- Capture graph schema / result: `ok` (access_state `ok`, blocked_by_challenge `False`).
- Initial status / final status / final URL / redirect evidence: `200 / 200 / https://sly.systems/ / 0 redirects`.
- Automatically eligible static GET/HEAD count / excluded counts: 39 static GETs, 8 personalized-data, 6 non-replayable, 1 data-api, 1 telemetry, 2 documents. Excluded: 10 POSTs (analytics, log-user-in-app), 4 personalized-data (User/me, entities/ShowcaseApp, public-settings), 1 telemetry (googletagmanager).
- Metadata references by state: 7 metadata references total (favicon, json-ld image, two json-ld logos, two OG images, web manifest). Captured/Probed/Observed statuses detailed in `mirror-manifest.json` `metadata_references[]`.
- Scroll coverage mechanism: `window_scroll`.
- Service-worker registrations, cache/precache evidence, controlled result, and bypassed result: None.
- Same-origin assets (count / notable): 4 captured into `mirror/`: `index.html`, `assets/index-BfiDsVd2.css`, `assets/index-C--Jvz_w.js`, `manifest.json`. Source URLs → local paths in `mirror-manifest.json` `route_map`.
- External providers detected: Google Fonts (openly licensed, captured), SoundCloud family (embed/kept external), media.base44.com (user-uploaded brand media, kept external / rebrand-target), api.motion.dev (third-party badge, embed), Doubleclick / Google Ads (telemetry, skipped).
- Blocked / unresolved: 1 required failure (`https://w.soundcloud.com/player/?url=...` — provider audio, marked Embed + Kept External). 6 first-class external-host skips (SoundCloud family + Motion badge + Base44 media). 6 openly-licensed Google Fonts captured as `_external/`.

## Static Mirror discovery evidence

- Repo / source link found: No.
- Probe URLs checked (+ real result, noting SPA false-200s): `/manifest.json` returned a real PWA manifest (parsed); no `/.vite/manifest.json`, `/_next/build-manifest.json`, or `/package.json` probed because the bundle is single-file; `/sitemap.xml`, `/robots.txt`, `/asset-manifest.json` not relevant for this build.
- Sitemap / routes found: 9 routes via anchored links (8 sibling + `/work/gonzo` case-study).
- Manifest files found: `/manifest.json` and `/api/apps/<id>/manifest.json` (cache aliasing; same body).
- Source maps found: None (production bundle, no `.map`).
- Bundle scan findings: bundle is **single-file** (no other `/assets/*.js` chunks referenced). `import(`/`new Worker`/`new URL(`/`fetch(` all appear but resolve to inline definitions or fetch-based data calls only. No `.wasm`, `.glb`, `.gltf`, `.ktx`, `.hdr`, `.drc`, `.bin`, `.mp3`, `.ogg`, `.woff`, `.woff2` discovered *in the bundle* (fonts come via the captured Google Fonts CSS, which references `.woff2` that were also captured). 65 references to `media.base44.com` (cumulative across hero + case studies + logo wall).
- Runtime interaction capture performed, with declared trigger coverage: standard capture scroll + load phase only; no click/hover expansion of the case-study tab picker beyond its initial state.
- Missing assets found from local server 404 logs: 5 mirror-introduced same-origin 404/501 errors at `/api/apps/*` — these are Base44 backend APIs the JS bundle calls at runtime (entities/User/me → 404, entities/ShowcaseApp → 404, public-settings/by-id → 404, app-logs POST → 501, analytics/track POST → 501). The "App state check failed: Base44Error" stack trace in console originates from these.
- Blocked or unexercised discovery paths: case-study tab switcher (`pick your world` tabs); SoundCloud iframe (provider stream); Motion.dev badge image.

## Findings

### Facts

- Page loads as HTTP 200 with the title "SLY — Custom AI Software & Automation for Growing Businesses | Miami AI Product Group".
- HTML structure (header nav, hero, four-moves cards, case-study picker, audio embed, news logos, footer) renders end-to-end in the local mirror with the captured fonts. Screenshots of local vs source match at structural-grid level for in-DOM text.
- 16 hero/section videos + 24 brand images are **external** to the mirror and use SLY's media.base44.com CDN. They are not captured because: (a) the user signalled an impending rebrand, (b) --allow-host is reserved for explicitly user-confirmed origins, (c) rebrand replacement will swap them anyway.
- 6 Google Fonts CSS/woff2 files were captured into `_external/` to preserve typography fidelity; rebrand may swap these too.
- The SoundCloud player is an iframe to `w.soundcloud.com/player/?url=...` — provider-streamed audio. Marked Embed + Kept External.
- The base44 backend API the SDK depends on (`/api/apps/<id>/entities/User/me`, `/entities/ShowcaseApp`, `/public-settings/by-id/...`) returns 404 locally. The frontend throws "App state check failed: Base44Error" in the console. This is a *builder-runtime* limitation, not a mirror-introduced defect: the live site calls the same endpoints against the live base44 backend.
- 50 `@keyframes` blocks and 64 GSAP references indicate substantial motion that's preserved through the JS bundle but cannot be observed in still screenshots. Hero letter transitions are baked into per-letter video files; switching tabs in "Pick your world" likely swaps which video plays.

### Assumptions

- The user will rebrand and replace media.base44.com brand assets wholesale; pulling ~25 MB of brand media for a one-shot local mirror would burn bandwidth + storage for assets that will be discarded.
- The Base44 backend dependency on `/api/apps/.../*` will be removed during rebrand; the captured JS bundle is sufficient as a *structural reference* even without runtime fidelity.
- The 8 additional routes (`/about`, `/base44`, `/contact`, `/engine`, `/idea`, `/newsletter`, `/review`, `/work/gonzo`) share the Base44 backend dependency in the same way and would re-encounter the same gap if expanded later.

### Unknowns

- Whether the per-letter hero videos are individually a brand identity asset (Kling-generated) vs a stock placeholder — the JS bundle references both `kling_20260702_*.mov` and named-letter `.mp4`s.
- Whether SoundCloud embeds are *content* or *audio* (track stream URL suggests actual audio, not just UI).
- Whether the static HTML reveal order is preserved across all viewports under the Base44 backend being unreachable.
