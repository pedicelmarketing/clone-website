# Re-content Report — Premium Padel Academy Marbella

Phase 2, copy pass. Runs on top of the validated restructure
(`reports/restructure-validation.md`) and covers the **five routes the approved
architecture document marks "Nothing blocking"**.

## Scope

| Route | Architecture page | Status |
| --- | --- | --- |
| `/` | Home | Re-contented |
| `/coaching/` | How we coach | Re-contented |
| `/programmes/` | Programmes | Re-contented |
| `/marbella/` | Marbella & the club | Re-contented |
| `/contact/` | Contact | Re-contented |
| `/coaches/` | The coaches | **Untouched — blocked** |
| `/coaches/juanpi-vanella/` | Juanpi Vanella | **Does not exist — blocked** |

The two coach pages are blocked on bios and photographs from the coaches
themselves. The architecture document records that Juanpi's entire public
footprint is one line on the club's staff page. Writing those pages without
that material would mean inventing biography, so they were left alone.

Applied by `tools/recontent.py` (`--check` for a dry run). Pre-content HTML is
preserved in `.pre-recontent/`.

The tool is a **one-shot transform, not a repeatable filter**: it maps Spanish
source text to English, so re-running it against already-converted HTML finds
nothing to match and reports the misses. Re-run it from `.pre-recontent/`, which
is deterministic — same input, same output. The whole chain is reproducible from
`travelproductions/mirror-pristine/` via `restructure.py` then `recontent.py`.

## What changed

    113 head edits              language, title, description, Open Graph, canonical
    210 copy replacements       text nodes and whole paragraphs
     26 links retargeted        every dangling internal link
     11 containers cut          Travel Productions case studies + client logo wall
    105 Vimeo widgets removed   21 per route
     21 background videos       cleared to empty
     16 analytics blocks        GA4, GTM prefetch, Search Console token
      9 Luma 3D viewers/legend  the embed and its orphaned control instructions
     46 contact details         source email, phone, social accounts
      5 schema.org graphs       Yoast Organization data naming the source
      5 cursor-handler repairs  see "Source bug repaired" below

## Result

**Acceptance tier: `Validated`.** URL × viewport matrix **10/10 passed** —
5 routes × {desktop 1440×900, mobile}. Evidence
`reports/viewports-recontent/viewport-results.json`.

    cells 10 | passed 10 | screenshots 10
    http_errors 0 | page_errors 0 | required_failures 0

Zero errors of any kind. This is a **higher tier than the baseline reached**
(`Partial`), because the three things holding the baseline back are gone rather
than merely tolerated: the Vimeo embeds that threw 403s off-domain were removed,
the background videos that produced nondeterministic aborts were cleared, and
the source JS bug was repaired.

Dangling internal links: **0**, down from 19.

## Source identity removed

Audited to zero across all five routes: the name "Travel Productions", the
`travelproductions.film` domain, the GA4 property `G-T5Q0TX0MC4`, the Google
Search Console verification token, `player.vimeo.com` embeds, the published
phone number and both email addresses, the Instagram/Vimeo/LinkedIn accounts,
the Luma Labs captures, the favicon and touch icon (the source wordmark), and
the Yoast Organization graph.

Three of these were live rather than cosmetic and are worth naming:

- **Google Analytics.** All five routes shipped the source's GA4 property. A
  deployed derived site would have reported the new client's traffic into
  Travel Productions' account.
- **Search Console token.** Left in place, Travel Productions could have
  verified ownership of the derived domain.
- **Client logo wall and case studies.** Nine client logos and ten case
  studies. A logo wall is a claim about who you have worked for, and it is not
  the academy's claim to make.

## Source bug repaired

`mouseleaveHandler is not defined` threw on every route, in the source and in
the baseline alike. A stray brace closed the enclosing function early, leaving
the declaration one scope below the listener referencing it.

The baseline documented this and deliberately did **not** fix it — repairing a
source bug during a mirror would be a change, and fidelity came first. That
reasoning ends at the mirror. Fixed here on the five in-scope routes.
**`/coaches/` still carries it**, and will until that page is written.

## Open items

1. **Coach material.** Bios and photographs for Riki Padrón and Juanpi Vanella.
   Blocks two of the seven pages.
2. **Media.** Every background video slot is now empty and the pages carry no
   photography. Layout, motion effects and scroll behaviour were left intact so
   replacement footage drops in without rebuilding sections. The site is
   structurally complete and visually unfinished — by design at this stage.
3. **Safiro.** Still the display face. The asset table classifies it
   `Restricted — must never ship`: a licensed retail typeface (Atipo Foundry)
   self-hosted under the source's own licence, which does not transfer. The
   academy must license it or the face must be replaced. Flagged, not swapped —
   the asset table calls for a deliberate decision, not a silent substitution.
4. **Contact details are placeholders.** `hello@premiumpadelacademy.example`
   and `+34 000 000 000`. `.example` is reserved by RFC 2606 and can never
   resolve, so neither can be mistaken for live. Both are greppable.
5. **Legal notice.** The brief dropped `condiciones-legales`, but every footer
   still links "Legal notice", currently pointed at `/contact/`. The site has
   no legal page.
6. **Marbella is thin.** Two paragraphs and five labels against a brief asking
   for climate, season length, getting here, and the club. The source route was
   the lightest of the seven; this page needs more copy than a re-version of it
   can supply.
7. **Social links** point at `#`. The academy's own accounts are not known.
