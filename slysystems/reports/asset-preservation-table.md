# Asset Preservation Table — sly.systems homepage

> Every major asset the homepage references is classified here exactly once.
> Counts reference `mirror/mirror-manifest.json` as the authoritative inventory;
> this table documents the *why* behind every classification.

## Classification key

`Original` · `Local Copy` · `Embed` · `Kept External` · `User-Supplied Baseline Asset` · `Recreated` · `Recreated From Observation` · `Approximated` · `Blocked` · `Unknown`

## Major assets

### Same-origin (SLY's own runtime)

| # | Source URL | Local path | Classification | Why |
| --- | --- | --- | --- | --- |
| 1 | `https://sly.systems/` | `mirror/_/index.html` | `Local Copy` | Required entry-point document; SHA `ee432bad7f…`. |
| 2 | `https://sly.systems/assets/index-BfiDsVd2.css` | `mirror/assets/index-BfiDsVd2.css` | `Local Copy` | Production CSS bundle; SHA `8c7bf4df0b…`. |
| 3 | `https://sly.systems/assets/index-C--Jvz_w.js` | `mirror/assets/index-C--Jvz_w.js` | `Local Copy` | Production JS bundle (single-file build); SHA `b5a8fa5a1f…`. |
| 4 | `https://sly.systems/manifest.json` (and `/api/apps/.../manifest.json` alias) | `mirror/manifest.json` | `Local Copy` | PWA manifest; SHA `9e22e0ab…`. |

### Fonts (openly licensed)

| # | Source URL | Local path | Classification | Why |
| --- | --- | --- | --- | --- |
| 5 | `fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&display=swap` | `mirror/_external/fonts.googleapis.com/css2__q_5bbcc4972b5bad20` | `Local Copy` | Openly licensed via Google Fonts (Cinzel). |
| 6 | `fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap` | `mirror/_external/fonts.googleapis.com/css2__q_8edcc57969308014` | `Local Copy` | Openly licensed via Google Fonts (Inter). |
| 7 | `fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap` | `mirror/_external/fonts.googleapis.com/css2__q_3d9f8086ccab429c` | `Local Copy` | Openly licensed via Google Fonts (Space Grotesk). |
| 8 | `fonts.gstatic.com/s/cinzel/v26/8vIJ7ww63mVu7gt79mT7.woff2` | `mirror/_external/fonts.gstatic.com/s/cinzel/v26/8vIJ7ww63mVu7gt79mT7.woff2` | `Local Copy` | Companion woff2 to the Cinzel CSS. |
| 9 | `fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2` | `mirror/_external/fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2` | `Local Copy` | Companion woff2 to the Inter CSS. |
| 10 | `fonts.gstatic.com/s/spacegrotesk/v22/V8mDoQDjQSkFtoMM3T6r8E7mPbF4Cw.woff2` | `mirror/_external/fonts.gstatic.com/s/spacegrotesk/v22/V8mDoQDjQSkFtoMM3T6r8E7mPbF4Cw.woff2` | `Local Copy` | Companion woff2 to the Space Grotesk CSS. |

Rebrand note: rebrand may swap to a different font set. These three are captured as structural baseline; replace freely at rebrand.

### Brand media — kept external, rebrand target

| # | Source URL | Classification | Why |
| --- | --- | --- | --- |
| 11 | `https://media.base44.com/videos/public/6a38b9e683468637b6118425/*.mp4` (16 URLs) | `Kept External` (rebrand target) | SLY's brand videos served from the Base44 user-media CDN. **Not mirrored**: the user signalled a rebrand; --allow-host was not authorized for media.base44.com in this run; these files (collectively ~25 MB) would be discarded at rebrand. The captured JS bundle preserves the *references*; the rebrand replaces the URLs + files. |
| 12 | `https://media.base44.com/videos/public/6a38b9e683468637b6118425/*.mov` (1 reference, Kling-generated) | `Kept External` (rebrand target) | Same as #11. |
| 13 | `https://media.base44.com/images/public/6a38b9e683468637b6118425/*.png` (8 logos, hero imagery, OG images) | `Kept External` (rebrand target) | SLY's brand images. Same rebrand-target reasoning. |
| 14 | `https://media.base44.com/images/public/69f1a258fba70dbfa61e4a23/*.png` (favicon) | `Kept External` (rebrand target) | Site favicon. Same reasoning. |

Fidelity impact: locally the hero letters, case-study tiles, and logo wall appear as dark placeholders. Text + layout + navigation + typography are intact.

### Provider audio — embed, kept external

| # | Source URL | Classification | Why |
| --- | --- | --- | --- |
| 15 | `https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fintelligentsoundua%2Fgals-yellow-last-pines-remix-1&auto_play=false&show_artwork=false&visual=false` | `Embed` + `Kept External` | The SoundCloud player iframe. The audio stream is provider-hosted by SoundCloud and is not redistributable. The capture marked this URL as required-for-baseline (it's an iframe page), but the asset is not eligible for automatic acquisition. The `mirror_assets.py` records 1 required failure against this URL; classification makes it known, not silently baked into the deliverable. |
| 16 | `https://widget.sndcdn.com/widget-*.js`, `https://widget.sndcdn.com/assets/images/logo-200x120-3190df52.png`, `https://w.soundcloud.com/player/api.js`, `https://dwt.soundcloud.com/tags.js`, `https://wave.sndcdn.com/CppSGDo1GmsD_m.json` (8 scripts + 1 image) | `Kept External` (provider) | SoundCloud widget runtime. Provider-streamed; iframes load these from sndcdn/w.soundcloud at runtime when online. |
| 17 | `https://api-widget.soundcloud.com/resolve?url=…` (2 calls) | `Kept External` (provider) | SoundCloud API resolution calls. |

Fidelity impact: locally the audio iframe renders but does not play. The audio source itself is third-party music ("Intelligentsoundua — Gals Yellow Last Pines Remix 1"); rebrand likely drops/replaces this audio.

### Third-party badge

| # | Source URL | Classification | Why |
| --- | --- | --- | --- |
| 18 | `https://api.motion.dev/score/badge?url=sly.clubop.site` | `Embed` | Motion.dev site-score badge (the motion-dev library author publishes them). Tiny badge image, optional polish; rendered at the bottom-right of the source page. Kept external — the badge belongs to motion.dev, not SLY. Rebrand removes it. |

### Builder backend — out of mirror scope

| # | Source URL | Classification | Why |
| --- | --- | --- | --- |
| 19 | `https://sly.systems/api/apps/<id>/entities/User/me` (401 on origin) | `Kept External` (backend, not mirrorable) | Base44 runtime: who's-signed-in lookup. Origin returns 401 even for anonymous visits; local mirror returns 404. JS bundle throws "Base44Error: Request failed with status code 404" at this URL. Cannot be mirrored without standing up a Base44 backend. |
| 20 | `https://sly.systems/api/apps/<id>/entities/ShowcaseApp?sort=…` (personalized data) | `Kept External` (backend, not mirrorable) | Base44 runtime: case-study content payload. Personalized evidence, not eligible for automatic acquisition. |
| 21 | `https://sly.systems/api/apps/public/prod/public-settings/by-id/<id>` | `Kept External` (backend, not mirrorable) | Base44 runtime: app config. Personalized evidence. |
| 22 | `https://sly.systems/api/app-logs/<id>/log-user-in-app/home` (POST) | `Kept External` (backend, not mirrorable) | Base44 analytics log. POST telemetry. |
| 23 | `https://sly.systems/api/apps/<id>/analytics/track/batch` (POST) | `Kept External` (backend, not mirrorable) | Base44 analytics ingest. POST telemetry. |

Fidelity impact: locally the page initializes, but logged-in personalization, case-study content payload, and analytics are unavailable. Rebrand will replace this Base44 backend with the new client's stack, so this is the *intended* ending.

### Out-of-scope telemetry / ads (skipped_other)

| # | Source URL | Classification | Why |
| --- | --- | --- | --- |
| 24 | `https://www.googletagmanager.com/gtag/js?id=AW-18384236785` | `Kept External` (telemetry) | Google Ads conversion tag. Telemetry is never auto-acquired. |
| 25 | `https://ad.doubleclick.net/ccm/s/collect?auid=…` (POST) | `Kept External` (telemetry) | Doubleclick click-conversion collect. POST telemetry. |
| 26 | `https://www.google.com/ccm/collect?…` (POST) | `Kept External` (telemetry) | Google click-conversion collect. POST telemetry. |
| 27 | `https://api-widget.soundcloud.com/me?client_id=…` (POST) | `Kept External` (provider auth) | SoundCloud auth callback. POST. |
| 28 | `https://dwt.soundcloud.com/js/` (POST) | `Kept External` (provider telemetry) | SoundCloud analytics. POST. |

All of items 24–28 are POST or telemetry calls that the skill explicitly excludes from automatic acquisition. They are not required for visual fidelity and are reported here for completeness.

## Items NOT mirrored — summary

- 24 `media.base44.com` items (16 videos + 8 images including favicon, OG, json-ld logos) — kept external; rebrand target.
- 9 `soundcloud.com` family items (iframe page + 6 widget scripts + 1 widget image + 1 wave JSON) — kept external; provider stream.
- 1 `api.motion.dev` badge — embed.
- 10 backend POST / personalized calls — out of mirror scope (Base44 runtime).
- 4 telemetry / auth POSTs — out of mirror scope.

## Permission and asset-hygiene notes

This is an **internally-adapted fork** of NT Site Mirror. Per operating policy:

- No external authorization question is asked. The user-stated context is `"inspiration / non-commercial reference"`.
- Paid fonts, provider-streamed audio (SoundCloud), and protected media would never be silently baked into a derived deliverable — they are classified above and left external.
- `media.base44.com` is the Base44 user-media CDN (the platform that hosts the rendered site); it is *not* a paid-fonts CDN or a stream provider, so the items there do not fall under the "paid fonts / provider-streamed media / protected" exclusion list. They were kept external this run for a different reason: the user's imminent rebrand, and the explicit policy that `--allow-host` requires user confirmation.
