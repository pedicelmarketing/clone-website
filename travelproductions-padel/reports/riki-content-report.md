# Content re-version — riki-coach → Premium Padel Academy

Replaces the placeholder copy and the Wikimedia stock imagery with the client's own
content: the copy adapted from their live site, and the photography they supplied.

**Layout and visuals are unchanged.** No container, style rule, breakpoint or motion
setting was touched. Every edit is copy, media or metadata, applied through the same
scripted passes as the previous build so the whole chain stays reproducible from the
pristine baseline.

## Sources

| Source | What was taken | Evidence basis |
| --- | --- | --- |
| `97jnvjsg4j.wixsite.com/riki-coach` (live) | All body copy, headings, programme names, methodology, FAQ, contact pair | `DOM+assets confirmed` — fetched and text-extracted 2026-07-31; nav resolved with Playwright |
| `examples/riki-coach/Assets/` (28 files) | 13 photographs + the brand monogram | `Observed visually` — every frame inspected before placement |
| `examples/riki-coach/recreation/` | **Not used as the copy source** — see below | `DOM+assets confirmed` |

### The local recreation was stale

`examples/riki-coach/recreation/` is an earlier recreation of the same site, and its
reports are unfilled templates. Checked against the live site it is out of date on
every page, so the **live site was used instead**. The differences are not cosmetic:

| | Local recreation | Live site (used) |
| --- | --- | --- |
| Brand | "Riki Coach" | **"Premium Padel Academy"** |
| Coaches | Riki Padrón alone | Riki Padrón **and Juampi Vanella** |
| Experience claim | "Más de 12 Años" | **"Más de 15 Años"** |
| Voice | first person singular | first person plural |
| Register | "élite" | "premium" |
| Sport | "tenis y pádel" throughout | mostly **pádel**; tennis only where the source still says so |

The live brand — **Premium Padel Academy** — independently confirms the name this build
was already using, which was set from the architecture document before the source was
consulted.

### Route discovery

The nav's `Clubs` item points at `/home`, not `/clubs` (which 404s). Three distinct
pages exist; `/riki-coach-head-coach-profesional` is an alias of the home page, and
`/portfolio` renders empty.

| Source page | Real URL | Mapped to |
| --- | --- | --- |
| Inicio | `/` | `/` and `/coaches/` |
| Clubs | `/home` | `/programmes/` |
| Camps | `/camps` | `/marbella/` |
| local service card | (on Inicio) | `/coaching/` |

## Language

The source is entirely Spanish. This build is English, so the copy is **translated and
adapted**, not transcribed. Substance, claims and structure are faithful; phrasing is
not. A Spanish variant is a second value column in `PAGE_TEXT` if it is wanted — the
architecture document already specifies one.

## `/coaches/` is no longer a placeholder

It previously shipped as a standalone noindex placeholder because no coach bios existed.
The source supplies them, so the page was rebuilt properly:

- regenerated from `travelproductions/mirror/es/sobre-nosotros/` through `restructure.py`;
- re-contented, media-filled and deployed through the same passes as every other route;
- the placeholder writer was deleted from `prepare_deploy.py`.

A new `replace_widgets()` pass was needed for it. Its copy sits in Elementor
`text-editor` widgets with no wrapping `<p>`, and one widget holds two paragraphs at
once — neither the text-node pass nor the `<p>`-anchored block pass can address that, so
widgets are swapped by their own `data-id`.

> **Caught during this pass:** the first attempt built the page from `mirror-pristine/`,
> which predates the origin-localisation step. That left 52 stylesheet links pointing at
> `https://travelproductions.film` — the page would have loaded its CSS and fonts from
> the source's live server. Rebuilt from `mirror/`; all six pages now hold **zero**
> references to the source origin.

## Source branding still present — found and removed

Two pieces of Travel Productions' identity survived every earlier pass and **were live
on the public preview**. Both are now gone.

**1. Their wordmark was the site logo, on all six routes.**
`Logo-Travel-web_blanco.svg` sat in the navigation of every page — 11 references. The
content pass had rewritten its `alt` text to "Logo Premium Padel Academy", which made it
worse rather than better: another company's logo captioned as this client's. The
academy's own monogram now fills the slot, rendered white-on-transparent at the
wordmark's own 632×230 box so it drops in with no CSS change.

**2. Their client logo wall was on `/coaches/`.**
36 references — Meliá Hotels, Selina, The Tais, Guía de Isora, proximity BBDO, Mogán,
Nicaragua, Islas Canarias, RIU, Ritz-Carlton. The `Logo-carrusel` removal existed but was
only mapped for the home page; the coaches route carries its own copy of the same band.
A logo wall is a claim about who you have worked for, and it was making that claim on
the client's behalf using someone else's clients.

Both were only visible because `/coaches/` was rebuilt this pass — it had previously
shipped as a standalone placeholder, which is what hid the second one. The first was
visible on every page all along.

**3. Eleven more third-party marks were still in the deliverable.**
Found while preparing the commit. Nine were unreferenced files sitting under a public
URL — Ayuntamiento de Peñíscola, Nicaragua tourism, Playas de Jandía, a WordPress login
logo. The tenth and eleventh were a **"Terres Festival — official competition" selection
badge still rendering on the home page** as an absolutely-positioned overlay: an award
claim about Travel Productions, displayed on the academy's home page. The badge widget is
removed by Elementor id and all eleven files are purged.

`site/wp-content/uploads/` now holds only `stock/` (client-owned) and `elementor/`
(OFL/Apache fonts and generated CSS). Zero third-party marks, zero references.

**Purged from disk:** 28 files (0.2 MB) — the wordmark SVG, the source's favicons, and
23 client logo images. Verified: zero references and zero files matching `Logo-Travel`,
`Logo-carrusel`, `travel-productions` anywhere under `site/`.

## Media

All Wikimedia Commons stock is gone, replaced by 13 client photographs. The licence
position inverts: the stock set carried CC BY attribution on four images and CC BY-SA
share-alike on three. **The client's own files carry neither**, so the footer credits
line that was outstanding is no longer owed.

| Slot | Shows |
| --- | --- |
| `hero` | Wide aerial of the complex with the coastline behind |
| `programmes` · `club` · `camps` | Aerials of the courts; courts under La Concha |
| `lessons` · `technical` · `physical` · `group` | Coaching and group sessions |
| `match` | Competitive match play |
| `coaches` | Coach portrait |
| `courts` | Empty courts, landscape framing |
| `marbella` · `contact` | Puerto Banús; palm avenue at sunset |

EXIF is stripped at ingest — the originals came off phones and could carry location
metadata. Images are bounded to 2200px and re-encoded at q82; the set totals 3.4 MB.

The brand sheet carries a circular monogram, which is cropped to `logo.png` /
`favicon.png` and wired into all six pages. The build previously had no icon at all,
the source's having been removed with the rest of its identity.

## Validation

- **Local URL:** `http://127.0.0.1:8614/` — plain static host with byte-range support.
- **Routes:** all 6. **Viewports:** desktop, tablet, mobile — **18 cells**.
- **Result: 18/18 PASS, 0 HTTP errors, 0 page errors.**
- Confirmed over the public tunnel: all routes 200, and `grep` for source branding on
  the served HTML returns 0.

This is a better result than the previous build, which carried 234 Vimeo 403s and a
`mouseleaveHandler is not defined` throw in every cell. Both are gone: the Vimeo player
widgets were removed with the source's content, and the cursor-handler scope bug is
repaired by the content pass.

**Acceptance tier reached: `Validated` for the declared route × viewport scope.**
Not `Offline-validated` — the tier names the evidence, and the interaction states below
were not exercised.

**Not exercised:** consent accept/reject, cursor follower, mobile nav overlay tap,
hover states, scroll-triggered motion beyond what settles during capture.

### Reference scan

A static scan reports 40 unresolved local refs per page. These are **not live breakage**
and are unchanged from the validated baseline: 37 are `unicode-range` font variants the
browser never requests, and the rest are `view_icon.png` (a `<noscript>`/`srcset`
fallback), `/wp-json/…` and `/xmlrpc.php` (WordPress `<link rel>` entries no browser
fetches). Browser evidence supersedes the scan — 0 HTTP errors across 18 cells.

## Fidelity gaps and open items

| # | Item | Status |
| --- | --- | --- |
| 1 | **Juampi Vanella has no bio.** The source gives his name and role and nothing else. Carried across as exactly that — no bio was invented for a named person. | `Pending` — needs client copy |
| 2 | **The source contradicts itself on his title:** the eyebrow above his name reads "HEAD COACH", the heading beside it reads "Premium Coach". Resolved as Riki = Head Coach, Juampi = Premium Coach. | `Approved approximation` — confirm |
| 3 | **Phone `+34 600 000 000` is a placeholder on the source too.** Carried across unchanged rather than invented. `info@rikicoach.com` is the source's real published address. | `Pending` — real number needed |
| 4 | **"Portafolio Global"** — the Clubs page's six-item gallery of past club work is not represented. Our equivalent component was the case-study grid, removed in the earlier pass as Travel Productions' portfolio. | `Fidelity Gap` — needs a component |
| 5 | **The camps enquiry form** is a Wix-backed form on the source. The contact route carries details, not a working form. | `Fidelity Gap` |
| 6 | Claims carried across **as the client's own**: "more than 15 years", "one of the most prestigious padel clubs in the world", the M3 Academy association. Attributed, not asserted independently. | `Accepted` |
| 7 | Some frames carry third-party branding in shot (sponsor boards, club and retailer signage). Normal for venue photography, worth a look before a commercial domain. | `Pending` — client review |
| 8 | Safiro is still substituted with Open Sans. Family name kept, so it reverts in one line. 0 Safiro font files on disk or referenced. | `Approved approximation` |
| 9 | `noindex` + `robots.txt` remain in place. **Remove at launch.** | `Intentional` |
| 10 | Footer still links "Legal notice" at `/contact/`. No legal page exists. | `Pending` |
| 11 | The nav mark is the monogram cropped from a **JPEG brand sheet**, so it carries compression artefacts at large sizes. Ask the client for the vector original. | `Approved approximation` |
| 12 | **`examples/riki-coach/Assets/Marbella Photos/` is unused and unversioned.** Several filenames match the Marbella tourism office's professional-area galleries, which `architecture/PERMISSION-REQUEST.md` says need express council authorisation for commercial use. Held back pending provenance — see that folder's `.gitignore`. | `Blocked` — needs confirmation |

## Reproducing

```sh
python3 tools/restructure.py    site          # routes + assets (already applied)
python3 tools/recontent.py      site          # copy, metadata, source-identity removal
~/.venvs/nt-mirror/bin/python tools/ingest_media.py site   # client photography + monogram
python3 tools/apply_media.py    site          # fill background slots
python3 tools/prepare_deploy.py site          # fonts, noindex, favicon, purge
```

`.pre-recontent/` holds all six documents as they were before the copy pass, so the
content pass can be re-run from a clean state after any edit to the maps.
