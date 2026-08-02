# Asset Preservation Table — Premium Padel Academy

> Status is exactly one of: `Original` | `Local Copy` | `Embed` | `Kept External` | `User-Supplied Baseline Asset` | `Recreated` | `Recreated From Observation` | `Approximated` | `Blocked` | `Unknown`.

Hashes, URLs and acquisition attempts are machine-authoritative in `mirror/mirror-manifest.json`;
per-file slot mapping is in `site/assets/media-provenance.json`. Neither is restated here.

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| Route documents ×4 (`/`, `/home`, `/camps`, `/contacto`) | `https://97jnvjsg4j.wixsite.com/riki-coach…` | **`Blocked`** | Acquisition refused: `personalized_evidence_observed_in_one_or_more_responses`. Wix SSRs each page with per-session tokens. `mirror-manifest.json` → `result: failed_required`, 4 required failures. | Cause of the method fallback. Structure and copy instead **`Recreated From Observation`** from live computed styles + DOM. |
| Page structure, section order, copy (all 4 routes) | Live DOM + computed styles, 1440×900 and 390×844, 2026-08-01 | `Recreated From Observation` | Rebuilt as hand-written HTML/CSS. Copy transcribed verbatim from the source, Spanish retained. | None observed within declared scope. Source's own typos in body copy were corrected (see Fidelity notes in validation report). |
| 15 photographs (hero, coaches, cards, bands) | `static.wixstatic.com/media/<id>` — the client's own uploads | **`Local Copy`** | Acquired through `mirror_assets.py --extra-urls` at a bounded `v1/fit/w_2400` variant, then bounded to 2000px, EXIF stripped, re-encoded q84. Client owns this media. | None. Higher resolution than the per-slot variants the source serves. |
| Brand logo | `static.wixstatic.com/media/b99928_6100…~mv2.png` | **`Local Copy`** | Same pipeline; alpha genuinely used, so kept PNG, bounded to 800px. | **Artwork reads "Premium Padel Aacademy"** — a typo in the client's own asset, reproduced as-is rather than silently redrawn. Flagged for decision. |
| `Instrument Serif`, `Instrument Sans` | Google Fonts, computed `font-family` on source | **`Kept External`** | Requested from `fonts.googleapis.com` / `fonts.gstatic.com`. Both SIL OFL. | None. **No paid face is used anywhere on the source**, so no licence decision is owed — unlike the earlier Travel-Productions-based build, which carried a restricted retail face. |
| Wix Thunderbolt runtime — 133 JS bundles, `static.parastorage.com` | Capture graphs, 186 requests on `/` | **`Blocked`** (deliberately not shipped) | Downloaded during the failed Static Mirror attempt and retained only as evidence under `mirror/`. Not referenced by, or copied into, the deliverable. | None — the rebuild has no dependency on it. Redistributing Wix's proprietary player under the client's domain is what the asset-hygiene rule prevents. |
| Wix promo bar ("Creado con WIX Harmony") | Source DOM, all routes | **Removed — client instruction** | Deliberately omitted. | Not a fidelity gap: an explicit client request, recorded as such. |
| Phone `+34 600 000 000` (7 occurrences on source) | Source DOM | **Removed — client instruction** | Omitted entirely; no `tel:` link remains (verified 0). | Not a fidelity gap: explicit client request. |
| Email `info@rikicoach.com` (6 occurrences on source) | Source DOM | **Replaced — client instruction** | Replaced with `Infopremiumpadelacademy@gmail.com` in both visible text and `mailto:` href, 8 hrefs total. | Not a fidelity gap. Note the source's own `/home` already read `infopremiumpadelacademy@gmail.com.com` — a duplicated `.com`, not carried across. |
| Contact form backend | Source uses a Wix-hosted form | **`Approximated`** | No server exists in this build. The form validates client-side and composes a `mailto:` so an enquiry always reaches the academy rather than silently failing. | Behavioural difference from the source. Requires the decision below. |
| Telemetry — `frog.wix.com`, `browser.sentry-cdn.com`, `panorama.wixapps.net` | Capture graphs | **`Blocked`** (not replayed) | Never acquired or replayed. POST pings are outside automatic acquisition by design. | None. Telemetry loss is not a fidelity failure. |

## Baseline approximations requiring approval

- **Contact form backend — `Approximated`.** The source posts to Wix; this build has no server, so submission composes a `mailto:` instead. It never silently swallows an enquiry, and the markup does not need to change when a real endpoint (Formspree, Brevo, a serverless function) is chosen. **Needs a decision on which backend to wire up.**

## Items needing a client decision (not approximations)

- **Logo typo — "Premium Padel Aacademy".** Present in the client's own artwork and live on the Wix site. Reproduced faithfully rather than edited, because correcting a brand asset is the client's call. Trivially fixable if wanted.
- **Juampi Vanella's title.** The source labels him "HEAD COACH" in the eyebrow while the section heading reads "Premium Coach's". Resolved as Riki = Head Coach, Juampi = Premium Coach. Confirm.
