# Validation Report

## Declared validation scope

- **Source URL / evidence:** `https://travelproductions.film/es/{inicio,servicios,trabajos,sobre-nosotros,contacto,escena-3d,condiciones-legales}/`
  — live site, captured and re-visited live for paired comparison. No user recordings or screenshots
  were supplied, so the two highest evidence tiers are absent.
- **Local URL / serving contract:** `http://127.0.0.1:8412/es/…` — see Serving Contract below.
- **Method:** `Static Mirror`
- **Routes:** the 7 ES routes above. **10 case-study detail routes and 18 EN routes are out of scope.**
- **Viewports:** `desktop` (1512×982) and `mobile` — 14 cells.
- **Interaction / loading / media states:** 14-step window scroll per route per viewport (ScrollTrigger
  reveals, Lenis momentum, Elementor parallax, autoplay video, Lottie), bounded DOM settling, default
  un-actioned cookie banner. **Not exercised:** consent accept/reject, pointer-driven cursor
  follower, mobile nav overlay tap, Vimeo player controls, Luma scene interaction.
- **Capture date/time:** 2026-07-30, source and local passes run back-to-back within each paired run
  (see `generated_at` in each `viewport-results.json`).

## Per-section checks

| Section / route | Viewport | Scroll behavior | Animation / media | Interaction states | Verification method | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `/es/inicio/` — nav, `h1`, hero reel, 3 label rows, portfolio grid, logo band, about band, footer | desktop | `window_scroll`, Lenis momentum active | ScrollTrigger heading wipe scrubs; hero reel plays; 7 cover videos play; Elementor parallax on the grid | Banner shown un-actioned | `Interaction-tested` (scroll) + `Observed visually` (paired screenshots) | **`Partial`** — one nondeterministic `.mp4` `ERR_ABORTED` per run keeps the cell from completing. See Fidelity Gaps row 3. |
| `/es/inicio/` — same | mobile | `window_scroll` | Mobile 720p hero cut plays; grid collapses to one column | Banner shown un-actioned | `Interaction-tested` | `Pass for declared evidence` |
| `/es/servicios/` | desktop, mobile | `window_scroll` | Heading wipes; section video plays | — | `Interaction-tested` | `Pass for declared evidence` (2/2) |
| `/es/trabajos/` | desktop | `window_scroll` | Case-study index cover videos play | Links to detail routes are out of scope → 404 locally | `Interaction-tested` | **`Partial`** — same nondeterministic media abort. |
| `/es/trabajos/` | mobile | `window_scroll` | as above | as above | `Interaction-tested` | `Pass for declared evidence` |
| `/es/sobre-nosotros/` | desktop, mobile | `window_scroll` | Lottie globe animates from the locally-acquired payload; office video plays | — | `Interaction-tested` | `Pass for declared evidence` (2/2) |
| `/es/contacto/` | desktop, mobile | `window_scroll` | Cover video plays | `mailto:` CTAs present — **no form to submit**, so nothing to stub | `Interaction-tested` | `Pass for declared evidence` (2/2) |
| `/es/escena-3d/` | desktop, mobile | `window_scroll` | Sculpture/church clips play locally | Luma splat viewer iframe present; **scene internals never exercised** | `Interaction-tested` for the page, `Not exercised` for the scene | `Pass for declared evidence` for the page. Scene = **`Fidelity Gap` (offline)**, row 2. |
| `/es/condiciones-legales/` | desktop, mobile | `window_scroll` | Legal text, no media | — | `Interaction-tested` | `Pass for declared evidence` (2/2) |
| **All routes** — 147 Vimeo player embeds | both | — | Players are live `Embed`s | Player controls **not exercised** | `DOM+assets confirmed` (iframes present, `src` intact) | **`Fidelity Gap` (offline only)**, row 1 |

## Global checks

- [x] **Typography and spacing checks completed for the declared comparison scope** — paired
      source/local desktop and mobile screenshots for all 7 routes. Safiro, Antonio, Open Sans and
      Roboto all resolve locally and render; the display type, tracking and grid match the source.
- [x] **All kept same-site links resolve locally, intentionally point live/external, or are
      documented out of scope** — full accounting in `discovery-report.md` § Link & Route Inventory.
      The 10 case-study links and the language switcher are recorded `Out of scope` and **do 404
      locally** — declared, not silently broken.
- [x] **Every in-scope structured module exists on the correct route and is structurally
      recognizable** — no route contains a table, pricing grid or spec matrix; `/es/contacto/` is
      `mailto:`-based with no form action; `/es/condiciones-legales/` legal text is intact.
- [x] **No unresolved critical overlap, stuck/frozen behavior, or missing asset within exercised
      coverage** — after the origin-localization accommodation, zero mirror-introduced 404s. The
      remaining `ERR_ABORTED` events are cancellations of files that are present (see row 3).
- [x] **Performance observations recorded** — 86.2 MB total, of which 78.5 MB (91%) is video. The
      desktop hero cut alone is 18.6 MB. Range/206 serving is therefore load-bearing, not optional.
- [x] **Active module validation results recorded** — `video.md`, `multi-route.md`,
      `runtime-assets.md`, `webgl.md` (see below).
- [x] **Asset Preservation Table statuses verified — no silent substitutions.** Nothing was
      substituted, approximated or downgraded. Every status is `Local Copy`, `Embed`, `Kept External`,
      `Blocked` (telemetry, intentional) or `Unknown` (never-requested font alternates).

**Per-module results:**
- `video.md` — 21 self-hosted `.mp4` preserved and playing locally at both viewports, separate
  desktop/mobile hero cuts both exercised. 147 Vimeo players preserved as `Embed`. **No video was
  replaced by a poster or static image anywhere.**
- `multi-route.md` — each of the 7 routes has its own captured HTML at its own path; no shared shell
  overwrote route-specific HTML (correct, since this is not an SPA). Route-by-viewport matrix run.
- `runtime-assets.md` — the one runtime-loaded same-origin payload (Lottie, 38 KB) was found by
  bundle/graph scan and acquired. No dynamic imports, workers, or WASM resolved same-origin.
- `webgl.md` — the only 3D surface is a third-party Luma Labs iframe. There is no local WebGL
  context, canvas scene, shader, or model file to preserve, so the requirement resolves to the
  `Embed` classification. The `canvas` references in the main document are WordPress emoji feature
  detection, not a scene.

## Static Mirror audit

- **Result tier: `Partial static mirror`.**
  Not `Validated` — 2 of 14 matrix cells did not complete, and `mirror_assets.py` exits non-zero.
  Not `Offline-validated` — the portfolio players and the 3D scene are third-party embeds that
  require network by design, so an offline run can never pass. **No higher tier is claimed.**
- **Discovery coverage:** `Complete for declared triggers`. All five module categories assessed and
  recorded. Omissions: the out-of-scope routes, and the un-exercised interaction states listed above.
- **Declared viewport (validation source of truth):** 1512×982 desktop; mobile preset as the second
  declared surface. Narrower preview surfaces are non-representative and were not used for verdicts.
- **Experience gate:** no preloader, entry gate, or progress screen exists on this site — **not
  applicable**. The cookie banner is an overlay, not a gate: content renders and scrolls behind it.
- **Evidence gates:** boot ☑ · dependency ☑ · experience ☐ (not applicable — no gate exists).
  - *Boot:* all 7 routes serve `200` through the one documented command; `206` confirmed on range
    requests.
  - *Dependency:* after the accommodation, no unresolved mirror-introduced local 4xx during declared
    coverage; every external request classified. **Offline validation not claimed** — never attempted,
    because the `Embed`s make it structurally impossible.
- **Asset count / total folder size:** 184 files / 86.2 MB (`mirror-manifest.json` is authoritative).
- **Missing or unresolved files within declared coverage:** none.
- **Remaining external requests:**
  - *Critical:* `player.vimeo.com` (147 players), `cdn-luma.com` (3D scene). Without network these
    two features are dead; everything else renders.
  - *Harmless:* `s.w.org` emoji fallback; Google telemetry (deliberately not reproduced);
    `fonts.googleapis.com` stylesheet (redundant — Roboto resolves from two local copies).
- **Construction-time accommodations:** one. See the table below.

## Serving Contract

- **Serve command:** `python3 ~/.claude/skills/nt-site-mirror/scripts/serve.py mirror --port 8412 --no-spa`
- **Web root:** `travelproductions/mirror` · **Port:** 8412
- **Contract / manifest:** `mirror/mirror-manifest.json`, schema 1.3.
  **`serve-contract.json` and `serve-local.py` were never emitted** — the pipeline suppresses its
  generated artifacts when a run ends in `failed_required` (`generated_artifacts: []`). The mirror is
  therefore served through `serve.py` directly, which reads `route_map` from the manifest and gives
  identical routing. This is a consequence of the non-zero exit, recorded rather than worked around.
- **SPA fallback:** `Off` — explicitly, via `--no-spa`. This is a multi-page WordPress site; SPA
  fallback would mask genuine 404s on the out-of-scope routes.
- **Route-map coverage:** exact path-and-query. Verified that `?ver=`-suffixed Elementor CSS
  (e.g. `/wp-content/uploads/elementor/css/post-286.css?ver=1785410875`) resolves through the map to
  its collision-safe local filename. No unresolved variants encountered.
- **Plain static hosting valid: no.** Required accommodations:
  - **Range/206 media support: needed.** 21 videos, largest 18.6 MB; the browser range-requests them.
  - **Content-type replay: needed.** Local filenames carry collision-safe suffixes
    (`post-286__q_81c2868f7aedaa02.css`), so extension-based sniffing would mislabel them.
  - **Query-aware / variant routing: needed.** See route-map coverage above.
  - Other: none. No shim, rewrite rule, or serving-time fallback.
- **`file://` support:** `Unsupported`. Root-relative paths do not resolve, the route map cannot be
  applied, and range requests are unavailable. All validation was done through the local server.
- All claims in this report are conditional on this serving setup.

## Automated URL × Viewport Evidence

- **Result files:** `reports/viewports/viewport-results.json` (unpaired first pass),
  `reports/viewports-paired-{inicio,servicios,trabajos,sobre-nosotros,contacto,escena-3d,condiciones-legales}/viewport-results.json`
  (paired source/local), `reports/viewports-retry-{inicio,trabajos}/` (reproducibility check).
- **Matrix complete: no — 12 of 14 cells passed.** The 2 failures are `/es/inicio/` and
  `/es/trabajos/` at desktop, both `required_same_origin_request_failure` on a single `.mp4`.
- **Per-cell status and final URL recorded:** yes, for every cell.
- **Rejected challenge / login / consent-blocking / error / 404 states:** none encountered — every
  cell returned `200` with `final_url == requested_url` and no redirects, on both source and local.
- **Scroll mechanisms exercised:** `window_scroll` on all 14 cells, both source and local.
- **Service-worker results:** not applicable — no worker is registered anywhere on the site, so no
  controlled/bypassed pass was required.
- **Settling method:** `DOMContentLoaded + bounded reported settling`, maximum 6000 ms (9000 ms on
  the retry runs). `networkidle` was never used.

## Construction-Time Accommodations

| Artifact / path | Phase / actor | Required local accommodation | Source / provenance evidence | Revalidation evidence |
| --- | --- | --- | --- | --- |
| 17 captured text files (7 route `index.html` + 10 CSS/JS), 1,382 references | `construction` / `nt-site-mirror operator (localize_origin.py)` | Elementor addresses its own assets at the absolute source origin. Served from loopback those requests left the mirror; cross-origin font loads were then CORS-refused and the baseline could not render its own typography or media. The literal origin prefix (plain, escaped-JSON, and protocol-relative forms) was replaced with a root-relative path. **No copy, markup, layout, media selection or behaviour changed.** | `mirror-manifest.json.local_modifications[0]` — per-file `sha256_before`/`sha256_after` and pristine-copy path for all 17 files. Pre-edit originals in `mirror-pristine/`. Reproducible: `python3 tools/localize_origin.py mirror` (`--check` reports without writing). | Full 14-cell matrix re-run after the change: mirror-introduced local 4xx went from "every font, 4 videos and the Lottie CORS-refused" to **zero**, and passing cells went 0/14 → 12/14. Grep confirms the only remaining `travelproductions.film` strings are content (email addresses, an Instagram handle, and the origin inside an oembed query parameter) — nothing that fetches. |

## Interaction Coverage

- **Exercised (with result):**
  - Window scroll, 14 steps, every route × both viewports, on source *and* local — ScrollTrigger
    heading wipe scrubs correctly, Lenis momentum active, Elementor parallax active, autoplay video
    plays, Lottie globe animates. Pass on 12/14 cells.
  - Range requests on video: `206` confirmed.
  - Route navigation across all 7 in-scope routes: `200` each, correct per-route HTML.
- **Not exercised — and why:**
  - Cookie-consent accept/reject — the capture tool never clicks through an access or consent control.
  - Pointer-driven cursor follower (GSAP, row 4 of the animation audit) — no pointer movement is
    driven; source-inspection evidence only.
  - Mobile nav overlay tap (`Menú`/`Cerrar`) — no taps driven.
  - Vimeo player controls and Luma scene camera — third-party `Embed` internals, out of scope.
  - `prefers-reduced-motion` — not tested; no reduced-motion handling was found in the captured GSAP
    call sites, but absence there is not proof of absence site-wide.
  - The 10 case-study routes and 18 EN routes — out of declared scope.

## External Runtime Dependencies

| Dependency | Handling | Fidelity impact | Evidence |
| --- | --- | --- | --- |
| GSAP 3.9.1 + ScrollTrigger (cdnjs) | `Localized` (`_external/cdnjs.cloudflare.com/…`, authorized via `--allow-host`) | None — the primary motion system works without network | Heading wipe scrubs on all 12 passing cells |
| Roboto via `fonts.gstatic.com` | `Localized` (`_external/fonts.gstatic.com/…`) | None | Renders locally |
| `player.vimeo.com` — 147 players | `Kept external` | **Critical for offline.** Faithful with network (the source streams them too); dead without it | Refused by the pipeline as provider-hosted; iframes and `src` intact in captured HTML |
| `cdn-luma.com` — splat viewer + 6 artifacts | `Kept external` | **Critical for offline.** Same reasoning | Refused as outside the authorized host set |
| `fonts.googleapis.com/css2?family=Roboto…` | `Kept external` | None — redundant, Roboto resolves from two local copies | Refused: capture recorded personalized evidence on the response |
| `s.w.org` emoji SVG | `Kept external` | None observed | WordPress emoji fallback |
| GTM / GA4 (`G-T5Q0TX0MC4`) / DoubleClick / `google.fr/ads` / Cloudflare Insights | `Blocked` (intentional) | **Not a fidelity failure.** Telemetry is never auto-acquired and live tracking is never replayed locally. **No construction-time no-op was needed** — nothing blocked on them | `skipped_other` / `skipped_external` in the manifest |

## Fidelity Gaps

| Feature | Missing / downgraded behavior | Constraint | Available baseline paths | Status |
| --- | --- | --- | --- | --- |
| Portfolio video players (147 Vimeo embeds) | Nothing is missing **with network**. Without network the players do not load. | Provider-streamed media is never auto-acquired — and a scraped local copy would be *less* faithful than the iframe as well as a redistribution of the source's footage. | 1. Keep as `Embed` (chosen — faithful, and the source does the same). 2. Ask the owner for the master files. 3. Approximate with posters — **rejected**, that would downgrade a video feature to a still. | `Pending` — no user acceptance has been sought or given. Recorded, not assumed accepted. |
| Luma Labs 3D scene (`/es/escena-3d/`) | Nothing with network; scene absent offline. | Third-party viewer iframe, scene passed in the query string; outside the authorized host set. | 1. Keep as `Embed` (chosen). 2. Obtain the source's own Luma account/scene. 3. Rebuild the splat — out of scope for a baseline. | `Pending` |
| Nondeterministic `.mp4` `ERR_ABORTED` (1–2 per desktop run) | None demonstrable. The matrix cell fails, but no asset is actually absent. | The browser cancels partially-buffered media during scroll; `viewports.py` counts any same-origin request failure as required. | Evidence that this is not a defect: **(a)** every implicated file exists locally at full size, returns `200`, and answers a byte-range request with `206`; **(b)** the file that aborts **changes between runs** (`Office-Travel-productions.mp4` → `peniscola_-_cover-720p.mp4` → `San_miguel_cover.mp4`); **(c)** the **live source aborts its own videos too** in the same passes (`Playas-de-jandia-Cover_comprimido.mp4`, `BDD-Cover_.mp4` on `travelproductions.film`). The paired matcher only excuses an *exact URL* match, so a different file aborting locally than on the source is not auto-excused. | `Pending` — the evidence points to a harness artifact, not a mirror defect, but the matrix is genuinely incomplete and **this report does not claim otherwise.** |
| 10 case-study routes, 18 EN routes | Links from captured pages 404 locally. | Out of declared scope. | Capture them — a scope extension, not a repair. | `Out of scope` (see Link & Route Inventory) |
| `mouseleaveHandler is not defined` | A JS error throws on page load. | **Pre-existing source bug.** | Machine-confirmed as a source baseline exception (`exact_failure_matched_explicit_source_local_pair`) — it throws on the live site identically. Not repaired: fixing a source bug would be a change, and the mirror's job is fidelity. | `Accepted exception` — accepted on *machine evidence* that the source behaves the same, not on user acknowledgement. |

## Project status

**`Partial`** — for the declared scope of 7 ES routes × 2 viewports × scroll-driven interaction,
served through `serve.py` on port 8412.

- **Completed:**
  - All 7 routes captured (`200`, no redirects, 0 recorder errors) and serving locally (`200`, `206`).
  - 184 assets / 86.2 MB localized, including all 21 self-hosted videos, all 4 Safiro cuts, the
    Lottie payload, GSAP + ScrollTrigger, and Lenis.
  - **12 of 14 URL × viewport cells pass** with paired live-source comparison.
  - Motion system reproduced and interaction-tested: the ScrollTrigger heading wipe, Lenis momentum
    and Elementor parallax all behave locally as they do on the source.
  - Every asset classified with no silent substitution; boot and dependency gates pass.
  - One construction-time accommodation, minimal, reversible, hash-recorded and reproducible.
- **Blocked:**
  - `mirror_assets.py` exits **2** (`failed_required`): 147 Vimeo player documents + 1 Luma viewer
    document can never be acquired. This is structural, not fixable, and it also suppressed the
    `serve-contract.json` / `serve-local.py` artifacts.
  - Offline validation is **structurally impossible** while the portfolio and 3D scene are
    third-party embeds. Not attempted; not claimed.
- **Approved baseline approximations:** none. Nothing was approximated.
- **Not exercised / unresolved:**
  - 2 desktop cells incomplete on a nondeterministic media abort (evidence above suggests a harness
    artifact; not claimed as a pass).
  - Consent accept/reject, cursor follower, mobile nav tap, `prefers-reduced-motion`, Vimeo and Luma
    internals.
  - `zoom_out2` container animation — present in markup, behaviour unverified.
  - 10 case-study routes and 18 EN routes — out of scope.
