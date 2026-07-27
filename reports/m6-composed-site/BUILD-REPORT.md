# Build report (plan-driven)

Project slug: `pedicel-marketing-redesign-smoke`
Brand name: **Pedicel Marketing** — _derived from project_slug 'pedicel-marketing-redesign-smoke' (suffixes stripped)_
Generated: 2026-07-24T21:55:00Z brief → composed by compose_site.py v1.1 from `design-plan.json`
Outdir: `reports/m6-composed-site`

---

## Layout thesis (from design-plan.json)

- **Statement:** Pedicel sells the act of making a brand legible to itself. The redesign should read like a quiet classroom: one thesis at the top, a slow reveal of services as chapters, and a single recurring mark — the gold dot above the 'i' — used as a wayfinding device that doubles as a visual syllabus of the agency's beliefs.
- **Audience:** Founder-led SMB owners (≈10–80 employees) who already have a product and a vague brand, but no shared language for it; they need a partner who will teach them what their own brand already is, not a vendor pitching disruption.
- **Job to be done:** Convert a skeptical founder reading the home page for 45 seconds into a booked discovery call, by demonstrating — not claiming — that Pedicel extracts a uniqueness the visitor couldn't articulate themselves.
- **Why this, not generic:** Generic agency sites lead with a centered hero, three icon-cards, a 'services' grid, a testimonials carousel, and a 'let's talk' footer — the exact template the brief's brand_donts forbid (no impact tropes, no purple gradients, no challenger copy, no stock photography). Instead, this redesign leads with a one-sentence confession of belief, then progresses as a numbered curriculum so the visitor is taught the agency's process before being sold on its outputs. The gold dot above the 'i' (Pedicel's only saturated brand color, literally the dot of the brand mark) is reused throughout as an inline marker, a bullet, a step number, and a cursor accent — turning one logo detail into the page's signature.

## Signature element (from design-plan.json)

- **Name:** the gold dot
- **Description:** A single oversized circle in #efad2b — the literal fill of the dot above the 'i' in the Pedicel wordmark — reused as a wayfinding marker throughout the page: as the period that ends the thesis headline, as a numbered list bullet, as a step counter, as the cursor accent on the CTA button, and as the only color used at scale.
- **Why it fits the brand:** Pedicel's logo declares exactly two fills: alice-blue for the wordmark glyphs and #efad2b gold for the dot. The dot is the brand's only saturated color and the literal punctuation of its name (the dot on the 'i'). Reusing it across the page turns a logo detail into the page's structural system — which matches the brand's own positioning that 'uniqueness' lives in details most agencies ignore.
- **Implementation note (rendered in HTML+CSS as a real device):**
  Render the dot as a CSS pseudo-element with a 0.6em diameter, color #efad2b, border-radius 9999px (the only place the design system uses a fully circular radius — every other corner stays sharp, per 'no uniform rounded corners'). Use it inline at the end of the thesis sentence; vertically centered beside numbered list items; and as a 0.4em trailing element inside the CTA button so the button reads 'book a call →' where the arrow is the gold dot. Never use it as a background fill behind text.

The signature element is emitted in HTML as `<span class="signature-dot" aria-hidden="true">`
and styled in `styles.css` under the `.signature-dot` selector. It uses
`var(--color-primary)` so it picks up whatever the synthesized token system
declares as the brand's primary color (the design plan calls for the literal
gold #efad2b; the token system reserves the same hex for `--color-primary`).
It appears inline as the period ending the thesis headline, beside numbered
curriculum rows and process steps, and trailing the CTA button.

## Motion vocabulary (from design-plan.json)

- **Register:** `restrained`
- **Rationale:** The brand voice is 'confessional-educational' — quiet and teacher-like. Cinematic motion would contradict that register. Restrained, on-paint reveals respect the reader's pace and keep the page feeling like an essay rather than a launch site. The single kinetic flourish is the dot scaling into place, because the dot is the signature and it deserves one moment of attention.
- **Effects:**
  - thesis headline fades in once, 320ms, on first viewport entry
  - numbered list items reveal one row at a time as they cross 20% into the viewport, 240ms stagger, no bounce
  - gold dot scales from 0.6em to its final size on first paint of each section, 180ms ease-out
  - CTA button has a 1px underline that draws left-to-right on hover over 200ms
  - no parallax, no marquee, no auto-playing video, no scroll-jacking

The plan's register drives `styles.css` via `_motion_css_for_register()` —
`restrained` ⇒ 320ms fade-in only; `balanced` ⇒ 420ms fade + 6px lift;
`cinematic` ⇒ 640ms fade + 16px slide with cubic-bezier easing. No parallax,
no marquee, no auto-play regardless of register. All variants honor
`@media (prefers-reduced-motion: reduce)`.

## Sections emitted (plan-driven)

| Section | Emphasis | Order | Component (truncated) | Brief fields that fed it |
|---------|----------|-------|-----------------------|--------------------------|
| thesis-statement (`#thesis-statement`) | hero | 1 | single-line thesis headline, left-aligned, anchored top-left, with the gold dot … | `voice_and_tone.example_lines`, `voice_and_tone.favorite_words`, `palette_from_logo.primary` |
| | | | | **Why this section:** Lead with the brand's actual belief in the brand's own sentence-case voice, with no marketing framing above it. |
| | | | | **Rationale:** Pedicel's own tagline is a teacher-like statement of belief, not a value claim. Placing it alone, left-aligned, in display weight, with the logo's gold dot functioning as a sentence-ending mark, makes the page feel like the opening line of an essay rather than a marketing surface. This deliberately breaks the centered-everything hero default. |
| what-we-believe (`#what-we-believe`) | primary | 2 | two-column prose block (left: short numbered premise; right: short numbered prem… | `voice_and_tone.register`, `voice_and_tone.example_lines`, `voice_and_tone.banned_words` |
| | | | | **Why this section:** Explain the agency's worldview in the brand's own 'confessional-educational' register before any service appears. |
| | | | | **Rationale:** Voice notes describe the brand as 'teacher-like' and 'confessional-educational'. Putting the worldview before the service catalog enforces that order — the visitor is taught what Pedicel believes before they are shown what Pedicel sells. Avoiding banned words ('disrupt', 'revolutionary', 'cutting-edge') keeps the prose in the brand's own register. |
| service-curriculum (`#service-curriculum`) | primary | 3 | vertically stacked numbered rows; each row contains a gold-dot chapter number, t… | `service_facts`, `voice_and_tone.favorite_words`, `voice_and_tone.banned_words`, `palette_from_logo.accent` |
| | | | | **Why this section:** List the eight public services from LinkedIn as chapters of a syllabus, not as feature cards. |
| | | | | **Rationale:** The brief's only service inventory is the LinkedIn list (Social Media, Community Management, Branding Strategy, Sale Funnels, SEO, Web Design, Rebranding, Paid Advertising). A vertical 'curriculum' layout reads those as a process instead of a checkbox grid — a deliberate counter to the forbidden 'three-column feature grid with icons'. Pricing is 'not disclosed' so no price line is invented. |
| how-we-work (`#how-we-work`) | secondary | 4 | horizontal 4-step strip on desktop, stacked on mobile; each step is a number (go… | `voice_and_tone.favorite_words`, `voice_and_tone.notes`, `palette_from_logo.primary` |
| | | | | **Why this section:** Show the agency's process as four short numbered steps so the visitor understands delivery before seeing proof. |
| | | | | **Rationale:** Pedicel's positioning is 'customised from top to bottom' and lead-generation-driven. Naming a process addresses the founder's fear of a black-box engagement without inventing methodology specifics the brand hasn't published. Steps are deliberately described as verbs to keep them action-shaped, not jargon-shaped. |
| brand-not-blurb (`#brand-not-blurb`) | secondary | 5 | single framed image of the recovered og:image asset, captioned in the brand's vo… | `real_photo_inventory`, `brand_donts` |
| | | | | **Why this section:** Use the brand's own OG share image as the only large visual in the page, framed as 'how the brand already presents itself' rather than a stock hero. |
| | | | | **Rationale:** The only brand-owned image asset the brief authorizes for non-logo use is the og:image ('pedicelmarketingpreviewwebsite.jpg'). The brand_donts explicitly forbid stock photography of offices and handshakes, and the limitations section notes no real team/client photo is recoverable. Using the brand's own share card is the only honest choice. |
| what-the-dot-means (`#what-the-dot-means`) | secondary | 6 | short two-sentence aside set in body type next to a single oversized gold dot gl… | `palette_from_logo.rationale`, `palette_from_logo.primary`, `voice_and_tone.example_lines` |
| | | | | **Why this section:** Make the signature element explicit: explain that the gold dot above the 'i' in Pedicel is the page's recurring wayfinding mark. |
| | | | | **Rationale:** The signature element is only memorable if it is acknowledged once. A short aside teaches the visitor that the gold dot is intentional, then the rest of the page can use it as a marker without needing to label it again. |
| book-a-call (`#book-a-call`) | primary | 7 | full-width band in the alice-blue secondary surface with one sentence of copy an… | `voice_and_tone.example_lines`, `palette_from_logo.secondary`, `palette_from_logo.accent`, `service_facts` |
| | | | | **Why this section:** Convert with a single sentence and a single button — no form fields, no calendar embed, no 'subscribe to our newsletter'. |
| | | | | **Rationale:** The job-to-be-done is a discovery call. Anything more than a sentence plus a button is friction. The secondary alice-blue surface gives the band a quiet visual break without introducing a new color, and the accent blue (#3898ec) is the brand's actual interactive color from its own CSS, not a forbidden purple. |
| footer-colophon (`#footer-colophon`) | minor | 8 | two-line footer: brand line (logo wordmark + tagline) above a single line of leg… | `real_photo_inventory`, `voice_and_tone.example_lines`, `typography_recommendation.license_notes` |
| | | | | **Why this section:** Close with a small, sentence-case colophon that names the brand, the tagline, and the source of the page's typography — no social-feed embeds, no 'follow us' row. |
| | | | | **Rationale:** No social highlights or testimonials are recoverable (brief limitations). Inventing a 'follow us on LinkedIn/Instagram' row would be invention. The colophon is honest, sentence-case, and acknowledges the typography license constraint rather than hiding it. |

## Sections skipped by the plan (data absent in brief)

The plan's own `skipped_sections[]` is honored verbatim. Each entry names the
brief fields that would have been needed but are absent.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
| `testimonials` | The brief's limitations section explicitly states no testimonials are recoverable from any public surface. Including one would be invention, which is forbidden. | `testimonials` |
| `social-feed` | Both social_highlights.linkedin and social_highlights.instagram are empty by design — LinkedIn is gated and Instagram returns a login wall. A 'follow us' or post-grid section would have to be fabricated. | `social_highlights.linkedin`, `social_highlights.instagram` |
| `case-studies` | No client work imagery or case-study copy is recoverable from any public surface; the only brand-owned image is the OG share card, already used in 'brand-not-blurb'. A case-studies grid would invent clients. | `real_photo_inventory`, `testimonials` |
| `pricing` | Every service_facts entry has price_range 'not disclosed on public surfaces'. Showing tiers or starting prices would invent commercial facts. | `service_facts[].price_range` |
| `team-grid` | No real photograph of a person or team is in real_photo_inventory. The brief's limitations explicitly note the brand exposes no team imagery on its public surface. Headshots would have to be stock, which brand_donts forbid. | `real_photo_inventory` |
| `stats-counter` | Recoverable public numbers are limited to ~3,982 LinkedIn followers and 12 employees (gated). Basing a stats band on a single sourced metric would over-weight it; inventing metrics (campaigns run, leads generated) would be fabrication. | `testimonials`, `social_highlights` |

## Sections skipped at render time (no copy or payload)

The plan listed a section but the renderer could not find any copy block or
brief payload for it, so it was dropped rather than emitted empty. These are
reported here in addition to the plan's own skipped list.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
| _(none)_ | | |

## Design decisions (from design-plan.json)

- **Lead with a one-sentence thesis instead of a value-proposition headline-and-subhead pair.**
  - Alternatives considered: headline + subhead + CTA button trio, headline + benefit bullets, headline + animated tagline reveal
  - Why chosen: The brief's example_lines are short, sentence-case, and belief-shaped ('All brands are unique…', 'Limitless.', 'Our approach is customised from top to bottom.'). A single sentence respects that voice and breaks the centered-hero default. The CTA is moved to its own dedicated section further down the page.
- **Render services as a vertical numbered 'curriculum' rather than a grid of icon cards.**
  - Alternatives considered: three-column feature grid with icons, horizontal scrolling card row, tabbed service switcher
  - Why chosen: The forbidden-defaults list explicitly bans the three-column icon grid. A vertical numbered list reads the eight services as a sequence (which matches the brand's positioning that discovery is a process), keeps every service name exactly as the brand wrote it on LinkedIn, and gives each one room for a one-line teacherly description instead of a vague headline.
- **Use only #efad2b as the accent color and reserve the brand's CSS-blue (#3898ec) for the single CTA button.**
  - Alternatives considered: use both #efad2b and #3898ec interchangeably as accents, introduce a new accent color (purple/teal) to 'modernize', use the Webflow CSS's purple #6a34b3 as an accent
  - Why chosen: The brand_donts explicitly forbid purple, and the brief notes the CSS purple is a Webflow default state, not a brand surface. Treating gold as the only accent preserves the logo's actual color story (one saturated hue, one near-white) and lets the CTA button be the only place a second color appears — which makes the CTA unmissable.
- **Keep all corners sharp except the gold dot, which is the only fully circular element.**
  - Alternatives considered: uniform 8px rounded corners across cards and buttons, pill-shaped buttons with fully rounded ends, 16px corners on cards, 4px on buttons
  - Why chosen: The forbidden-defaults list bans 'uniform rounded corners'. Using a single sharp-cornered system (0px on cards and buttons, 1px dividers) and reserving full rounding for the signature dot reinforces that the dot is special and gives the page one visible moment of softness.
- **Use Switzer for display and Poppins for body, with an explicit license note in the footer colophon.**
  - Alternatives considered: swap to Inter for display to avoid the Switzer commercial-license issue, use Inter for everything, self-host Poppins only and fall back to system sans for display
  - Why chosen: The brief's brand surface already loads Switzer from the Webflow CDN and the typography_recommendation flags the license issue. Matching the brand's own loaded family keeps the redesign visually faithful to Pedicel's current intent, while a one-line colophon credit is the honest way to surface the license constraint instead of hiding it.
- **Hold motion to a single restrained register (on-paint fades, dot scale-in, underline draw) and refuse parallax, marquee, or auto-playing video.**
  - Alternatives considered: cinematic scroll-driven reveals, auto-playing background video in the hero, parallax depth between sections
  - Why chosen: Voice is 'confessional-educational'. Cinematic motion would over-perform the teacher-like register and contradict the brand's own positioning as quiet, customized, inbound. The one kinetic flourish (the dot scaling in) is reserved for the signature element so it earns its moment.
- **Skip testimonials, social feed, case studies, pricing, team grid, and stats entirely instead of fabricating any of them.**
  - Alternatives considered: fabricate plausible-but-unsourced testimonials, embed LinkedIn/Instagram widgets that would render empty, invent starting prices from industry averages
  - Why chosen: Every skipped section has a documented missing_brief_field. The brief's limitations section is explicit that invention is forbidden. Removing six conventional agency-site sections is itself a brand-specific design choice — the page is shorter, quieter, and more honest than a typical agency site, which matches the brand's own positioning.

## Contrast decision

- **Neutral body text token:** `--color-neutral-0` (#0b0c0d)
- **Neutral background token:** `--color-neutral-6` (#ffffff)
- **Neutral measured contrast:** 19.58:1
- **Neutral decision note:** text --color-neutral-0 (#0b0c0d) on background --color-neutral-6 (#ffffff) = 19.58:1, meets WCAG AA body-text threshold (4.5:1)

Brand colors remain unchanged for non-text identity uses. When a brand color is
used as normal-sized text, the composer uses the derived `*-text` token below.

- **Primary used as text:** original `#efad2b` on `#ffffff` measured 1.97:1; derived `#9e6d0c` (darken, 22 lightness steps) measures 4.52:1. Text uses: hero tagline text. Original `--color-primary` remains for non-text uses: skip-link background, decorative brand fills.
- **Accent used as text:** original `#3898ec` on `#ffffff` measured 3.06:1; derived `#1477ce` (darken, 13 lightness steps) measures 4.61:1. Text uses: links, navigation hover text. Original `--color-accent` remains for non-text uses: button backgrounds, focus outlines, borders, decorative fills.

## Token discipline

- **Source of truth:** `reports/m3-token-synthesis/tokens/dist/tokens.css`
- **Copied to site as:** `reports/m6-composed-site/tokens.css`
- **Token JSON:** `reports/m3-token-synthesis/tokens/dist/tailwind-tokens.json`
- **Audit:** PASS — all 23 expected token vars are declared in tokens.css

The page CSS links `tokens.css` and references token CSS variables for every
color, spacing value, radius, and shadow. No raw hex colors are emitted in
`styles.css`:

```
PASS — no raw hex literals in styles.css (every color is a token)
```



## Accessibility decisions

- **Semantic landmarks:** `<header role="banner">`, `<nav>`, `<main>`,
  `<section aria-labelledby>`, `<footer role="contentinfo">`.
- **Headings:** one `<h1>` (in the hero), logical nesting, no skipped levels.
- **Skip link:** `.skip-link` is the first focusable element; visible only on focus.
- **Alt text:** every `<img>` uses `real_photo_inventory[].subject` as `alt`.
- **Focus styles:** `:focus-visible` on every interactive element.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` disables the
  CSS-only plan-driven reveals.
- **Color contrast:** see "Contrast decision" above.

## Limitations carried forward from the brand brief

The brief's own `limitations[]` array is reproduced verbatim below. Every entry
below is a research-side limitation that the site honors by *not* inventing
content; nothing in the emitted page invents quotes, photos, services, or
stats. The plan's `skipped_sections[]` mirrors these where they apply.

- own_site (pedicelmarketing.com) is fully blocked by an OpenResty WAF: HTTP 403 on /, /about, /services, /contact, /sitemap.xml, /robots.txt, /wp-login.php, and /index.html. www.pedicelmarketing.com returns 404. Cloak stealth + CapSolver also returns 403 — this is not a captcha challenge, it is a blanket IP-level block. Palette and typography are therefore derived from the brand's CDN-hosted logo SVG and the Webflow CSS file, not from the live HTML.
- LinkedIn public company page returns 200 but the content is gated behind a cookie banner and an auth wall. The only recoverable content is the page's <meta> tags and the embedded JSON 'description' blob (Pedicel name, tagline, About blurb, ~3,982 followers, 12 employees, industry 'Marketing Services', service list). Post bodies, dates, and engagement metrics are NOT recoverable from the public surface — social_highlights.linkedin is empty by design.
- Instagram (https://www.instagram.com/pedicelmarketing) returns 302 to the login wall; no public grid, captions, or themes are recoverable. social_highlights.instagram is empty by design.
- Supabase POST credentials are not configured in this profile (claude/research-agent), so research_scrapes rows were NOT written; every scrapes_id in this brief is null. The cloak responses and the raw LinkedIn HTML are recoverable from the temporary files used during this run, but they are not durably persisted.
- loggedin/cloak_loggedin fetch path was intentionally not used — the request is a contract smoke test, not a real engagement, and stealth-by-logged-in-account would violate LinkedIn's terms. The brand's actual public surface is the LinkedIn meta-description, which is exhaustively captured in voice_and_tone.example_lines and service_facts.
- No real_photo_inventory entry is a real photograph of a person, team, or client work — the only 'real' images the brand exposes are the logo SVG, the OG/social share image, and the LinkedIn company logo. The brand's actual portfolio imagery is behind the gated site and could not be inspected.
- No testimonials are recoverable from any public surface. Including a testimonial would have been invention.
- palette_from_logo.secondary is the alice-blue that fills the logo wordmark glyphs (#f0f8ff). It is functionally a near-white, not a true secondary brand color; it is included because it is the literal second fill declared in the brand's own SVG. If the redesign team prefers a true secondary color, the Webflow CSS offers #3898ec (the brand's interactive blue) as the next-strongest candidate.
- Reference source (linear.app) was fetched successfully (11,220 chars of markdown) because it is open and not behind any gate. It is a structural reference only; the brand voice and visual decisions in this brief are grounded in Pedicel's own surface, not in Linear.

## Honesty tier

This build is **First-render** by the `nt-site-mirror` honesty tier scale:
- The page renders in any browser.
- Every claim in the page is backed by a brief field listed in "Sections emitted".
- No copy, photo, quote, statistic, or section was invented.
- The plan passed `design_pass.verify_source_fields` before any HTML was written
  (every `source_brief_fields` path resolves to a non-empty value in the brief).

It is **not yet M4-Validated**: the 8-gate validation (accessibility, performance,
site-wide audit, responsive, motion, source-paired) is M4 scope and is exercised
by `validate_site.py` once M4 lands.
