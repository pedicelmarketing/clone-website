# Media & Deployment Report — Premium Padel Academy Marbella

Follows the copy pass (`reports/recontent-report.md`). Two jobs: fill the empty
media slots, and publish.

**Live:** <https://immigrants-energy-marine-abstract.trycloudflare.com>
**Validated:** 12/12 URL × viewport cells passed **against the public URL**,
0 HTTP errors, 0 page errors. Evidence `reports/viewports-public/`.

## Media

The re-content pass emptied 21 background-video slots. All 21 are now filled.

Generation on Higgsfield was the first choice — original imagery has no licence
question at all — but the account has 0.09 credits, so it was not available.
Fell back to stock, sourced from **Wikimedia Commons**, which returns licence,
author and file page per result. Openverse was tried first and now requires
auth for anonymous queries.

    3 × CC0        (nothing owed)
    4 × CC BY      (attribution owed)
    3 × CC BY-SA   (attribution owed + share-alike on derivatives)

Nothing NonCommercial or NoDerivatives was accepted — this is a commercial site
and those terms do not fit. Credits and attribution obligations are recorded in
`site/wp-content/uploads/stock/MEDIA-CREDITS.md`, with machine-readable
provenance in `credits.json`. Images were downscaled to 1920px and re-encoded:
**23.8 MB → 4.7 MB**.

The containers' motion-FX settings were left untouched, so the imagery keeps
the parallax and scroll-scale behaviour the footage had.

**This is placeholder-grade imagery.** It fills the layout; it is not art
direction, and the CC BY-SA images carry a share-alike obligation on any
derivative crop. Replace with the academy's own photography before launch.

## What publishing forced us to fix

Publishing is distribution, so several things that were acceptable in a local
build were not acceptable on a public URL.

**1. Poster images — the real reason the backgrounds were blank.**
Elementor paints these containers from *generated CSS*, not from the HTML, and
those rules still pointed at twelve Travel Productions photographs which were
on disk and rendering. An override targeting the containers directly did not
work and would have been the wrong fix: Elementor moves the background to an
inner motion-effects layer. Repointing the CSS at the stock set is Elementor's
own mechanism, so the layers pick it up.

**2. Safiro — substituted, and this needs a decision.**
The asset table marks it `Restricted — must never ship`: a licensed retail
typeface (Atipo Foundry) self-hosted under the source's own licence, which does
not transfer. Publishing it would have been distributing it. The `@font-face`
sources — in the Elementor CSS *and* inline in the home page — now point at
Open Sans, which is already local and OFL. **The family name `Safiro` is
deliberately unchanged**, so every rule still resolves and the swap reverts in
one line if the academy licenses the face.

The asset table asked for a deliberate decision rather than a silent swap.
This is disclosed, not silent, but it is still a substitution made to get the
site online — **the licensing decision is still yours**, and the display type
currently renders in a face that is not the designed one.

**3. 87 MB of source media still on disk.**
21 Travel Productions videos (79 MB), 12 poster photographs and the 4 Safiro
files. The videos were no longer referenced by anything — but an unreferenced
file under a public URL is still a published file, and anyone with the path
could have downloaded their footage. Purged. `wp-content/uploads` went
**90 MB → 6.0 MB**, of which 4.5 MB is the stock set. Verified 404 over the
public URL.

**4. `/coaches/` was still Travel Productions' site.**
It is linked from every nav. Publishing it as-is would have put the source's
Spanish page back on the internet under someone else's brand. Replaced with a
self-contained placeholder that states plainly that the page is waiting on the
coaches' own bios and photographs. It carries the site nav, is `noindex`, and
contains nothing of the source.

## Deployment

Cloudflare **quick tunnel** (`cloudflared tunnel --url`), fronting the local
Range-capable static server on `127.0.0.1:8614`.

Two properties worth being explicit about:

- **It is public.** Anyone with the URL can view it. There is no auth.
- **It is ephemeral.** The URL dies when the `cloudflared` process stops, and
  a new one is issued on restart. For a stable address it needs a named tunnel
  against a Cloudflare account and a domain — say the word and I will set that
  up instead.

## Who can reach the preview

Checked, rather than assumed:

| Question | Answer |
|---|---|
| Needs a login? | **No.** 200 with no credentials, cookies or IP restriction |
| Discoverable via Certificate Transparency? | **No** — Cloudflare serves a wildcard `*.trycloudflare.com` cert, so the hostname is never logged |
| Indexable by search engines? | **No longer** — all 6 pages `noindex, nofollow`, plus `robots.txt: Disallow: /` |
| Does the hostname leave the machine? | **Once** — `cdnjs.cloudflare.com` (the GSAP library the source loads externally) receives it as a `Referer` |
| Is anything else on the machine exposed? | **No** — the origin server binds `127.0.0.1`; only `cloudflared` can reach it |

So: **unlisted, not protected.** The random four-word subdomain is the only
thing standing between the link and a stranger — obscurity, not access control.
Fine for sending to the client; not fine for anything confidential.

To actually restrict it, in increasing order of effort:

1. **HTTP Basic auth at the origin** — a few lines in the static server; works
   with the quick tunnel as-is.
2. **Cloudflare Access** on a named tunnel — real identity-based auth (email
   one-time-pins or SSO). Needs a Cloudflare account and a domain, and gives a
   stable URL as a side effect.
3. **Stop the tunnel** — kill `cloudflared` and the URL dies immediately.

The `noindex` tags and `robots.txt` are preview-only. **Remove both at launch**
or the finished site will be invisible to search.

## Still open

1. **Coach bios and photographs.** Blocks `/coaches/` and the net-new
   `/coaches/juanpi-vanella/`, which does not exist.
2. **Safiro licence decision** — see above. Currently rendering Open Sans.
3. **Photography.** Stock is placeholder-grade; three images carry share-alike.
4. **Attribution.** The seven CC BY / BY-SA images must be credited wherever
   the site is published. There is currently no credits line in the footer —
   `MEDIA-CREDITS.md` has the text, it is not yet on the page.
5. **Contact details** remain `hello@premiumpadelacademy.example` and
   `+34 000 000 000` (RFC 2606 reserved, cannot resolve).
6. **Legal notice** links to `/contact/`; the site still has no legal page.
7. **Marbella** is thinner than the brief asks for.
