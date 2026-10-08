# Asset Preservation Table

Source: `https://new-pedicel-website.webflow.io/` · Authorization context recorded in the manifest:
`owner-operated restore of pedicelmarketing.com`

Counts and hashes are authoritative in `mirror/mirror-manifest.json`; this table records the
**classification decision and why alternatives were rejected**.

**Totals:** 818 downloaded · 8 `failed` (all extraction artifacts — see note) · 441
`skipped_external` · 1 `local_modifications` entry.

| Asset | Source / evidence | Status | Baseline handling and constraints | Fidelity impact |
| --- | --- | --- | --- | --- |
| Route documents (HTML) ×63 | `new-pedicel-website.webflow.io/<route>` | `Local Copy` | Deployed markup for every in-scope route. Recreation rejected — static capture succeeded cleanly (63/63 graphs `ok`). | None |
| Webflow shared stylesheet ×1 | `cdn.prod.website-files.com/.../new-pedicel-website.webflow.shared.061801715.css` | `Local Copy` | 223 KB carrying all layout/typography. `integrity`/`crossorigin` stripped — the SRI hash is computed over the CDN bytes, so served from our own origin any byte difference makes the browser **refuse the file and render the page unstyled**. Keeping it external rejected: that hotlink is exactly what this work removes. | None |
| Webflow JS chunks + jQuery 3.5.1 ×7 | `cdn.prod.website-files.com`, `d3e54v103j8qbb.cloudfront.net` | `Local Copy` | Carries Webflow IX2 interactions. Omitting them would kill all scroll-triggered motion — a Fidelity Gap, not an optimization. | None |
| Webflow first-party analytics script ×1 | `new-pedicel-website.webflow.io/g0lnomhfn3mg…` (hashed path) | `Local Copy` | The page requests it as a **same-origin script**; absent it 404s on every load and fails the viewport cell. `--allow-telemetry-url` was rejected by the tool — it is "never applicable to scripts". Path verified stable across 3 loads and 2 routes before acquiring. Its outbound beacons are **not** replayed. | None |
| **Poppins** family ×18 `.otf` | `cdn.prod.website-files.com/64a2995238dba40820b37689/…` | `Local Copy` | SIL Open Font License — freely self-hostable. | None |
| **Switzer** family ×18 `.otf` | `cdn.prod.website-files.com/64a2995238dba40820b37689/…` | `Local Copy` | Indian Type Foundry, commercial. Fontshare's terms make webfont self-hosting conditional on ITF consent, which would normally force `Kept External` under the workspace asset-hygiene rule. **Classified `Local Copy` on the site owner's explicit statement that the licence is already held** — that statement is the sole basis. If it is ever wrong, the remedy is the Fontshare CDN. | None |
| Images ×710 (content, `srcset` variants, icons, favicons, og:image) | `cdn.prod.website-files.com` | `Local Copy` | Includes 272 Webflow `-p-<width>` responsive `srcset` variants that a first-load capture never requests (a browser fetches only the candidate matching its viewport), plus favicons and the og:image which browsers never fetch during capture. All enumerated by static scan and acquired via `--extra-urls` with `"required": true`. | None |
| **YouTube video** `nIdmeZV9LVY` via `cdn.embedly.com` | blog CMS rich text on `/blog/mastering-facebook-carousel-ads-2024` et al. | **`Embed`** | Provider-streamed. `modules/video.md` directs preserving the original provider embed; asset hygiene forbids downloading provider-streamed media. Downloading rejected on both grounds. Poster thumbnails resolve from `i.ytimg.com`. | None — plays via provider, as at source |
| PostHog (252 requests) | `us-assets.i.posthog.com`, `us.i.posthog.com` | `Kept External` | Live telemetry — SKILL.md forbids replaying live tracking in a local baseline. Owner's own project `phc_CoJfThYneBcnEpr7BhqZSDq8594ipjfAGlgubw5mgnt`, retained deliberately as part of the faithful restore. | None on render |
| Apollo visitor tracking (126 requests) | `assets.apollo.io`, `aplo-evnt.com` | `Kept External` | Live telemetry; owner's own app `663143ad6c4a6401c7441d03`. | None on render |
| GA4 / Google Ads (63 requests) | `googletagmanager.com`, `analytics.google.com`, `stats.g.doubleclick.net`, `www.google.*` | `Kept External` | Live telemetry; owner's own `G-YRE3WMB728`. Fires an `ads_conversion_Book_appointment_1` event — intentional, retained. | None on render |
| Calendly booking link | `calendly.com/ikedinachi/meeting` | `Kept External` | Third-party booking flow; must stay live to function. | None |
| Social profile links + YouTube posters (~44) | LinkedIn, Instagram, Facebook, X, YouTube, `i.ytimg.com` | `Kept External` | Outbound links and provider-hosted thumbnails. | None |
| **Form submission endpoint** (2 forms) | Webflow, bound to `data-wf-site="64a2995238dba40820b37689"` | **`Blocked`** | Not a copyable asset — the endpoint is bound to Webflow hosting. Recorded as a Fidelity Gap in the validation report and repaired in deployment Phase D, deliberately **outside** the baseline. | **Submissions silently discarded** until Phase D lands |

## Baseline approximations requiring approval

**None.** Nothing was approximated, recreated, downgraded, or substituted. Every asset is either a
byte copy of the source, a deliberately preserved provider embed, or a deliberately-kept-external
live service.

## Note on the 8 `failed` manifest entries

All 8 are **extraction artifacts of my own supplementary URL list, not missing assets.** Webflow
filenames contain literal parentheses (`project-LTF(2).jpg`) and the markup HTML-escapes the
surrounding quotes. A first-pass regex that excluded `(` / `)` truncated those URLs, and the
truncated forms return HTTP 403. A paren-aware, entity-aware re-extraction produced the correct
URLs — all of which return 200 — and they were acquired in round 3. The stale `failed` entries
persist because `mirror_assets.py --resume` preserves the download ledger rather than rewriting it.

**Verification that nothing is actually missing:** a paren-aware scan of every HTML/CSS/JS file in
the mirror finds **753 distinct referenced assets, all 753 of which resolve to a file on disk**, and
the final browser pass logged **0 local 404s**.
