# Asset Preservation Table — belgradearbor.rs (EN)

> Status is exactly one of: `Original` | `Local Copy` | `Embed` | `Kept External` | `User-Supplied Baseline Asset` | `Recreated` | `Recreated From Observation` | `Approximated` | `Blocked` | `Unknown`.
> Machine-authoritative record of hashes, paths and counts: `../mirror/mirror-manifest.json`.

## Fonts

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| **PP Editorial Old** — Regular, Ultralight, UltralightItalic (3 × OTF) | `/_next/static/media/PPEditorialOld_{Regular,Ultralight,UltralightItalic}-s.p.*.otf`, self-hosted same-origin, preloaded via `Link:` response header | `Local Copy` | Acquired because it is a same-origin static asset of the declared baseline and the baseline must render faithfully. **Commercial Pangram Pangram typeface — NOT redistributable.** It must not be carried into the derived site or any deliverable; the derived site needs either a purchased licence or a substitute face. Flagged for phase 2. | None for the baseline (renders exactly as source). **Blocking constraint for phase 2.** |
| **Work Sans** — 2 × woff2 subsets (weight 300, Latin + Latin-ext/Vietnamese unicode-ranges) | `/_next/static/media/{57dc28f7118abe14,7ddd198311ba7843}-s*.woff2`, declared in `/_next/static/chunks/*.css` `@font-face` blocks | `Local Copy` | Google Fonts family under the SIL Open Font License, self-hosted by `next/font`. Freely redistributable — safe to carry into the derived site. | None |

## Video (8 files, 52 MB — video module active)

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| `hero.mp4` (9.0 MB) | `/home/hero.mp4`, desktop hero background | `Local Copy` | Runtime-injected — no `<source>` in SSR HTML; captured because the desktop scroll pass triggered it. Origin serves 206 on Range; local server preserves Range/206. | None |
| `hero-m.webm` (1.9 MB) | `/home/hero-m.webm`, mobile hero background | `Local Copy` | Captured only because a mobile viewport pass was run. A desktop-only capture would have missed it. | None |
| `popup.mp4` (19.3 MB) | `/home/popup.mp4`, inquiry/modal video | `Local Copy` | File acquired and serves locally. **Its trigger interaction was never exercised** — presence is confirmed, playback in context is not. | Unverified in context — see validation report `Not exercised`. |
| `amenities.mp4` (5.4 MB) | `/home/amenities/amenities.mp4` | `Local Copy` | Scroll-triggered load, captured | None |
| `business.mp4` (5.4 MB) | `/home/business/business.mp4` | `Local Copy` | Scroll-triggered load, captured | None |
| `location.mp4` (5.3 MB) | `/home/location/location.mp4` | `Local Copy` | Scroll-triggered load, captured | None |
| `interior.mp4` (6.6 MB) | `/home/residences/interior.mp4` | `Local Copy` | Scroll-triggered load, captured | None |
| `image1.mp4` (1.7 MB) | `/home/roots/image1.mp4`, plays behind mask SVGs | `Local Copy` | Scroll-triggered load, captured | None |
| `404.mp4` | `/404.mp4`, hardcoded in JS bundle | `Local Copy` | Acquired during bundle scan. The `/404` route itself is out of declared scope. | None — out of scope |

## 3D scene assets — `/en/3d` (WebGL module active)

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| 9 × GLB models, 63 MB (`grad-fin` 10.4 MB, `grad2` 17.6 MB, `zgrada` 15.9 MB, `nature` 19.3 MB, `ljudi` 2.3 MB, `pruga` 0.9 MB, `stanovi` 182 KB, `lokali` 73 KB, `car` 200 KB) | `/glb/test2/*.glb`, `model/gltf-binary`, observed in the `/en/3d` capture graph | `Local Copy` | Same-origin originals, all acquired. **Draco-compressed** — they cannot be parsed without the external decoder below. | None, provided the decoder resolves |
| 4 × car textures | `/glb/test2/cars/{blue,grey,orange,red}.png` | `Local Copy` | Acquired | None |
| **Draco decoder** — `draco_decoder.wasm` + `draco_wasm_wrapper.js` | `https://www.gstatic.com/draco/versioned/decoders/1.5.5/`, requested at runtime by the GLTF loader | `Kept External` | **Not localized.** The source site loads it from gstatic; keeping it external is the faithful reproduction. Apache-2.0 licensed, so localizing it later is permissible — but that would require rewriting the decoder path inside a minified chunk, i.e. a construction-time accommodation, and was not needed for the baseline. | **The 3D scene cannot decode any model without network access to `www.gstatic.com`.** This is the single hard blocker to an offline-validated tier. |
| **drei HDR environment** — `hdri/kiara_1_dawn_1k.hdr` | `https://raw.githack.com/pmndrs/drei-assets/456060a2…/hdri/` (also observed via `raw.githubusercontent.com`) | `Kept External` | Not localized, same reasoning. Provides scene lighting via drei `<Environment preset>`. pmndrs/drei-assets is MIT. | Scene lighting depends on a **community CDN with no uptime guarantee**. Fragility flagged for phase 2. |
| **drei cloud texture** — `cloud.png` | `https://raw.githubusercontent.com/pmndrs/drei-assets/9225a9f1…/cloud.png` (also `rawcdn.githack.com`) | `Kept External` | Not localized, same reasoning | Same CDN fragility |
| `/px.png`, `/nx.png`, `/py.png`, `/ny.png`, `/pz.png`, `/nz.png` | drei `<Environment>` default-file constant `nX` inside `/_next/static/chunks/*.js` | `Unknown` → resolved as **not an asset** | Investigated during bundle scan: these are **library default constants, not site assets**. All six 404 at origin and are never requested, because the site passes a `preset`, which switches the loader to the external HDR path. Correctly excluded from acquisition. | None |

## Images

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| 301 × `_next/image` optimizer variants | `/_next/image?url=…&w=…&q=…&dpl=…`, returns `image/jpeg` | `Local Copy` | Query string is part of resource identity. Only 83 were requested at the capture viewport; the other **218 were found by diffing the captured HTML's `srcset` attributes against the route map and acquired via `--extra-urls`**. Without them the mirror would 404 into broken images at other viewports/DPRs. | None within the 301 observed variants. A device requesting an unobserved `w` gets an honest 404 — see validation report. |
| Raw `.webp` originals (hero, gallery, amenities, footer, residence-options, etc.) | e.g. `/home/**/*.webp`, `/about-the-investor/*.webp`, `/business/gallery/*.webp` | `Local Copy` | Same-origin originals, acquired | None |
| Floorplan / layout SVGs | `/single-appartment/gallery/non-flat/{main,1..7}.svg` + `-m` mobile variants; `/single-business/…` | `Local Copy` | Acquired for both sampled detail pages | None |
| Icons, masks, nav SVG | `/icons/*.svg`, `/home/roots/mask{1,2,3}.svg`, `/navigation.svg`, `/favicon.ico` | `Local Copy` | Acquired | None |
| Site photography, video and 3D models (content, as distinct from files) | All same-origin | `Local Copy` — **rights unknown** | Acquired as part of the faithful baseline. Licence status is not determinable from the runtime. Treat as the site owner's property. | None for the baseline. **Must not be reused in a derived commercial site without permission** — flagged for phase 2. |

## Documents

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| `ba-pp-brosura-eng.pdf` (7.0 MB) | `/pdf/ba-pp-brosura-eng.pdf`, brochure CTA on detail pages | `Local Copy` | Acquired. Initially failed acquisition because it was typed `document` (the tool then expects HTML); retyped `media` and acquired. | None |
| `gradjevinska-dozvola.pdf` (143 KB) | `/pdf/gradjevinska-dozvola.pdf`, building-permit link on `/en` | `Local Copy` | Same as above | None |

## Telemetry and third-party (never replayed)

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| Google Tag Manager (`GTM-MSFLG4VN`), Google Analytics, Google Ads / DoubleClick, Meta pixel (`connect.facebook.net`), HubSpot (`js-eu1.hs-scripts.com` `148338609`, analytics, cookie banner, `track-eu1.hubspot.com`) | Observed in every route's capture graph; 88 telemetry requests + 124 non-GET requests excluded | `Kept External` | **Not replayed and not localized**, per the telemetry rule. No deterministic no-op shim was needed — nothing blocked local operation. Requests simply fail or are unmade locally. | None. Telemetry failure is not a fidelity failure. |
| RSC route-payload fetches (`vary: rsc` variants of each route) | Observed as `fetch` requests to `/en`, `/en/contact` etc. during capture | `Blocked` | Classified `personalized_data` by the capture tool and not acquired. | Full-page loads of every declared route work. **Client-side in-app navigation may not** — listed as an Unknown in the discovery report and exercised in validation. |

## Baseline approximations requiring approval

**None.** No asset in the declared scope was approximated, recreated, downgraded or substituted. Every in-scope same-origin asset is a `Local Copy`; the only non-local functional assets are the 4 external 3D dependencies, which are `Kept External` **because that is what the source does** — not as a downgrade.

## Carried into phase 2 (NT Site Editor) — not baseline issues

1. **PP Editorial Old must be replaced or licensed** before the derived site ships.
2. **All photography, video and 3D models belong to the source site owner** — replace or license them.
3. **`raw.githack.com` is a fragile dependency** for the 3D scene's lighting. Consider self-hosting the HDR and Draco decoder in the derived site.
