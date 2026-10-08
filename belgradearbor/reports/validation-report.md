# Validation Report — belgradearbor.rs (EN)

## Acceptance tier reached

**`Partial static mirror — declared scope`**

Every declared route, viewport and exercised interaction passes except one systemic dependency gap: Next.js RSC prefetch payloads (`?_rsc=…`) return **200 on the source and 404 on the mirror**. The Dependency Gate therefore does not pass, and per the acceptance-tier rules this cannot be reported as a `Validated static mirror`. Everything else — boot, rendering, media playback, the WebGL scene, navigation, all 499 assets — passes with the evidence recorded below.

This is deliberately **not** presented as the higher tier. See §5 for exactly what the gap does and does not break.

## 1. Declared scope

- **Routes (10):** `/en`, `/en/3d`, `/en/residences`, `/en/retail-spaces`, `/en/business`, `/en/contact`, `/en/about-the-investor`, `/en/privacy-policy`, `/en/residences/a-1-01`, `/en/retail-spaces/b-lk1`
- **Viewports (3):** desktop 1440×900, tablet 768, mobile 390
- **Matrix:** 30 local cells, all 30 produced, paired 1:1 against the live source for baseline error subtraction
- **Out of scope:** 207 further residence pages, 48 further retail pages, the entire `/sr` tree

## 2. Evidence gates

| Gate | Verdict | Evidence |
| --- | --- | --- |
| **Boot gate** | **Pass** | Mirror boots via one documented command (§6), exercised end-to-end through the same channel a user would use. All 10 routes return HTTP 200 at byte sizes identical to live. |
| **Dependency gate** | **Fail** | 287 mirror-introduced same-origin 404s across the 30 cells, all of them `?_rsc=` prefetch URLs. Every external request **is** classified (§4). No other unresolved local 4xx remains. |
| **Experience gate** | **Pass** | No preloader or entry gate exists on any route. `/en/3d`, the one staged experience, reaches its terminal usable state — verified by screenshot (§3.3). |

## 3. Per-system verdicts

Each verdict states its verification method, per the Verification-Method Honesty rule.

### 3.1 Route delivery — **Pass for declared evidence** (`DOM+assets confirmed`)

All 10 routes serve 200 locally at exactly the live byte size, and all 10 stored documents are **SHA-256 identical to a fresh live fetch** and to their manifest hash (10/10 verified, 0 differing).

### 3.2 Video — **Pass for declared evidence** (`Interaction-tested`)

Runtime-injected video works. On `/en` after a 12-step scroll, 3 of 7 `<video>` elements had attached sources and all 3 were genuinely playing — `readyState: 4`, `paused: false`, `currentTime` advancing (hero.mp4 at 8.47s, interior.mp4 at 1.32s), decoded dimensions non-zero (2560×1440, 1920×1080). The remaining 4 are viewport-conditional `portrait`-class variants that do not attach a source at desktop width, matching source behaviour.

Range requests: the origin answers `206` on a byte range; the local server answers `206` with the same byte count. Preserved.

### 3.3 WebGL scene `/en/3d` — **Pass for declared evidence** (`Interaction-tested` + `Observed visually`)

- Canvas present and identified as **`three.js r184`**, 2160×1350 backing store at 1440×900 CSS.
- WebGL context acquired (headless software renderer, SwiftShader).
- **Rendered output confirmed visually**: screenshot at `reports/viewports-local/_3d-fullpage.png` shows the complete scene — the building with its lattice façade and planted terraces, road, cars, trees, pedestrians, sky, plus the NAVIGATION view-angle panel, PROPERTIES/FILTERS controls and the 10:00 am time-of-day slider.
- Colour-variance measurement on the settled frame: **131,792 distinct colours** over 1,296,000 pixels, dominant colour only 8.5% — a fully detailed render.
- All GLB models requested during the run returned **200** from the mirror; **zero** local request failures in the dedicated run.
- All 4 external functional dependencies fetched 200 (Draco decoder wasm + wrapper, drei HDR, drei cloud texture).

> **Measurement caveat recorded for honesty:** an earlier probe reported "1 distinct colour", i.e. an apparently blank canvas. That was a measurement artifact — three.js runs with `preserveDrawingBuffer: false`, so reading the canvas back via `drawImage` outside a render callback yields a cleared buffer. The screenshot method above is the valid one. The initial reading was wrong, not the mirror.

### 3.4 3D model aborts — **Not a defect** (`Interaction-tested`)

The paired matrix flagged 3 same-origin request failures on `/en/3d` (`grad-fin.glb`, `ljudi.glb`, `zgrada.glb` — the three largest models at 10.4 / 2.3 / 15.9 MB). Investigated: the recorded failure reason is **`net::ERR_ABORTED`**, i.e. the client cancelled the request; these are not server errors. All three files are present, are in the route map, and return 200 with correct byte counts on direct request. Under headless software rendering the harness tears the page down while multi-megabyte models are still streaming. Recorded as an observation, not a fidelity gap.

### 3.5 Client-side navigation — **Pass for declared evidence** (`Interaction-tested`)

The site's nav lives inside a menu overlay (links carry `opacity-0` until opened) on desktop as well as mobile. With the menu opened and `/en/residences` clicked: navigation reached `http://127.0.0.1:8100/en/residences`, in **`client_side_soft_nav`** mode (no new navigation entry — the Next.js router handled it, it did not hard-reload), destination title `Residences | Belgrade Arbor`, headings rendered. **Client-side routing works in the mirror despite the failed prefetches.**

### 3.6 Mobile menu — **Pass for declared evidence** (`Interaction-tested`, with a caveat)

The menu button is clickable and was clicked successfully at 390px. Visible nav-link count was 9 before and 9 after, so the open/close state change could not be distinguished by that measure — the overlay markup is present in both states. Menu **openability** is confirmed; the visual open state is confirmed only indirectly, via §3.5 where opening the menu made the previously `opacity-0` links clickable and navigation succeeded.

### 3.7 Fonts — **Pass for declared evidence** (`DOM+assets confirmed`)

All 5 font files (3 × PP Editorial Old OTF, 2 × Work Sans woff2) serve 200 from the mirror.

### 3.8 Image optimizer variants — **Pass for declared evidence** (`DOM+assets confirmed`)

All **301** distinct `_next/image` URLs referenced by the captured HTML are in the route map and resolve. A request for a width never observed at any capture viewport returns an honest 404 rather than a wrong-size fallback — correct fail-closed behaviour, and a residual limitation at untested DPRs.

### 3.9 Telemetry — **Pass for declared evidence** (`Observed`)

The only external request failures during validation are Google Ads / DoubleClick / Analytics collect beacons. Telemetry failure is not a fidelity failure and no telemetry was replayed or shimmed.

## 4. Gaps and external dependencies

### 4.1 Fidelity Gap — RSC prefetch payloads

- **What:** Next.js prefetches a React Server Component payload for every link, at `<route>?_rsc=<hash>`. 287 such requests 404 on the mirror across the 30 cells. The same URLs return **200 on the live source**, so these are unambiguously mirror-introduced.
- **Why it was not fixed:** the payload is only served when the request carries an `RSC: 1` header — the identical URL without that header returns HTML (`text/html`, 184,053 bytes) instead of the flight payload (`text/x-component`, 119,854 bytes). `mirror_assets.py` sends only `User-Agent` and `Accept-Encoding` and has no header-injection option, so declaring these URLs through `--extra-urls` would have stored **HTML at the `?_rsc=` paths** — serving actively wrong content, which is worse than an honest 404. Acquiring them any other way would be a side-channel acquisition outside the manifest pipeline. It was therefore left as a documented gap rather than papered over.
- **Actual impact — measured, not assumed:** navigation still works. §3.5 confirms a click reaches the correct route via client-side soft navigation with content rendered. What is lost is the *prefetch optimisation*: the router fetches on demand instead of ahead of time, and the console carries 404 noise. No page fails to load and no content is missing.
- **Status:** `Fidelity Gap`. It is the sole reason the tier is `Partial` rather than `Validated`.

### 4.2 External dependencies (classified, intentionally kept external)

| Dependency | Host | Why external |
| --- | --- | --- |
| `draco_decoder.wasm`, `draco_wasm_wrapper.js` | `www.gstatic.com` | The source loads them from gstatic; keeping them external is the faithful reproduction. **Without network access to gstatic the 3D models cannot be decoded at all.** |
| `hdri/kiara_1_dawn_1k.hdr` | `raw.githack.com` / `raw.githubusercontent.com` | drei `<Environment>` scene lighting |
| `cloud.png` | `raw.githubusercontent.com` / `rawcdn.githack.com` | drei cloud texture |
| GTM, Google Analytics/Ads, DoubleClick, Meta pixel, HubSpot | various | Telemetry — never replayed |

### 4.3 Not exercised

- `popup.mp4` (19.3 MB) — file present and serving; its trigger interaction was never fired, so playback in context is unverified.
- Accordion/expander components, menu enter/exit transitions (rows 6 and 9 of the animation audit).
- Residence and retail listing filters; gallery navigation.
- 3D camera orbit, building/unit selection, the time-of-day slider, and the PROPERTIES/FILTERS panels — present and visible, but not driven.
- Form submission on `/en/contact` (3 forms) and the inquiry forms — never submitted, by design.

### 4.4 Out of scope

207 residence detail pages, 48 retail detail pages, the entire `/sr` Serbian tree. The language switcher will not resolve locally.

## 5. What is and is not claimed

**Claimed:** all 10 declared routes render correctly at 3 viewports from the local mirror, with byte-identical HTML, working video, a fully rendering WebGL scene, working client-side navigation, and all 499 assets resolving.

**Not claimed:** offline operation (the 3D scene hard-depends on gstatic); correctness of any route or language outside the declared 10; behaviour of the interactions listed in §4.3; that the prefetch layer is intact — it is not.

## 6. Local serve contract

| Item | Value |
| --- | --- |
| **Command** | `python3 ~/.claude/skills/nt-site-mirror/scripts/serve.py mirror --port 8100` |
| **Web root** | `clone-website/belgradearbor/mirror` |
| **Port** | 8100 (8000 was occupied by an unrelated `uvicorn` service on this machine) |
| **Entry URL** | `http://127.0.0.1:8100/en` |
| **SPA fallback** | Off — correct; this is a multi-page Next.js mirror, not a true SPA |
| **Route authority** | `mirror/mirror-manifest.json.route_map`, 499 exact path+query entries |
| **Range/206** | Supported, required for video |
| **Why not `file://`** | Root-absolute asset paths, exact path+query route identity for `_next/image`, correct content types, and Range/206 for video all require a real HTTP server |
| **Accommodations** | **None.** `local_modifications`, `construction_provenance` and `generated_artifacts` are all empty — the mirror boots exactly as downloaded. |

> `serve-contract.json` and `serve-local.py` were **not emitted**. `mirror_assets.py` skips its completion steps because it exits nonzero (§7), so no launcher was generated. `serve.py` treats `--contract` as optional and reads the manifest's `route_map` directly, which is the serving path used and validated throughout.

## 7. Tool-level condition — disclosed, not resolved

`mirror_assets.py` **exits 2 on every run** and this will not clear.

- **Cause:** `capture_assets.py` classifies each route document `personalized_data` solely because of the response header `cache-control: private, no-cache, no-store`. `collect_records` forces the requested page document to `required: true` but deliberately refuses to override an `acquisition.automatic: false` flag carried from the capture graph, so each of the 10 graph-derived document records is permanently counted as a required failure.
- **Verified false positive:** `/en` returns a byte-identical body (SHA-256 `a300cdce26bf…`) across anonymous, fabricated-cookie (`sessionid`+`hubspotutk`), and altered-User-Agent fetches. The only `Set-Cookie` is `NEXT_LOCALE=en`. The header is Vercel's default for a dynamically rendered Next.js route, not evidence of personalisation.
- **How the pages were acquired:** through the sanctioned `--extra-urls` path with `"required": true` and the verification evidence recorded in each record's `acquisition.reason`. All 10 are SHA-256 identical to live.
- **Consequence accepted:** no `serve-contract.json` / `serve-local.py` (§6). The exit code is reported as-is rather than described as success.

## 8. Evidence artifacts

| Artifact | Contents |
| --- | --- |
| `mirror/mirror-manifest.json` | Machine-authoritative: 499 downloads with hashes, 499 route-map entries, 118 skipped external, 412 skipped other, 7 attempts, capture-graph provenance |
| `reports/*.asset-graph.json` | 10 schema-1.3 capture graphs |
| `reports/extra-urls.jsonl` | 257 declared URLs in 6 commented groups, each with its acquisition reason |
| `reports/paired/<route>/viewport-results.json` | 10 paired source↔local matrices, 58 screenshots |
| `reports/viewports-local/` | Local-only matrix screenshots + `_3d-fullpage.png` (the WebGL evidence) |
| `reports/interaction-results.json` | Navigation, video playback, menu behaviour |
| `reports/webgl-results.json` | Canvas/engine, GLB responses, colour variance, external dependency status |
| `reports/interaction-check.py`, `reports/webgl-check.py` | The two behavioural probes, re-runnable |
