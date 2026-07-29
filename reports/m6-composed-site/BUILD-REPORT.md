# Build report (plan-driven)

Project slug: `pedicel-marketing-redesign-smoke`
Brand name: **Pedicel Marketing** — _derived from project_slug 'pedicel-marketing-redesign-smoke' (suffixes stripped)_
Generated: 2026-07-24T21:55:00Z brief → composed by compose_site.py v1.1 from `design-plan.json`
Outdir: `reports/m6-composed-site`

---

## Layout thesis (from design-plan.json)

- **Statement:** The Pedicel Marketing redesign will emphasize the brand's core belief in 'uniqueness' and 'customised' strategies through a clean, editorial layout that subtly guides the user towards discovery, reflecting the 'confessional-educational' voice.
- **Audience:** Small to medium-sized business owners and marketing decision-makers seeking a strategic, personalized approach to branding and inbound marketing.
- **Job to be done:** To build trust and clearly articulate Pedicel Marketing's unique value proposition, differentiating them from generic agencies, and encouraging visitors to inquire about their services.
- **Why this, not generic:** This design avoids typical marketing agency tropes by foregoing stock imagery, emphasizing a distinct, warm educational tone, and leveraging a dynamic yet professional layout structure. The brand's primary gold color is used for emphasis rather than overwhelming the design, and the overall flow is designed for methodical information absorption, not quick, flashy impressions.

## Signature element (from design-plan.json)

- **Name:** Golden Ratio Growth Curve
- **Description:** A subtle, animated graphical element based on the golden ratio spiral, rendered in the brand's primary gold color (#efad2b). It expands slightly on hover or scroll, appearing as an overlay or background element in key sections.
- **Why it fits the brand:** The 'Pedicel' name refers to a flower stem, implying growth and organic structure. The golden ratio represents natural perfection and growth, aligning with Pedicel's focus on helping brands 'find their uniqueness' and achieve 'limitless' potential through customized strategies. The gold color ties directly to the brand's primary visual identity.
- **Implementation note (rendered in HTML+CSS as a real device):**
  Implement as an SVG graphic for scalability and subtle animation (CSS transitions or Lottie). It should appear lightly in the hero section, as a divider in the 'Our Approach' section, and subtly behind the CTA, never distracting but always reinforcing the 'growth' and 'customised' narrative. Its organic form counteracts generic, hard-edged design.

The signature element is emitted in HTML as `<span class="signature-dot" aria-hidden="true">`
and styled in `styles.css` under the `.signature-dot` selector. It uses
`var(--color-primary)` so it picks up whatever the synthesized token system
declares as the brand's primary color (the design plan calls for the literal
gold #efad2b; the token system reserves the same hex for `--color-primary`).
It appears inline as the period ending the thesis headline, beside numbered
curriculum rows and process steps, and trailing the CTA button.

## Motion vocabulary (from design-plan.json)

- **Register:** `balanced`
- **Rationale:** A 'balanced' register aligns with the brand's 'confessional-educational' voice – professional and informative, but not overly flashy. Subtle animations enhance engagement without disrupting the thoughtful learning experience, reflecting the customized and considered nature of their services.
- **Effects:**
  - subtle scroll-triggered reveals (fade-in, slide-up for content blocks)
  - gentle hover states on interactive elements (buttons, service cards)
  - signature element's expansion/pulsing on scroll-in

The plan's register drives `styles.css` via `_motion_css_for_register()` —
`restrained` ⇒ 320ms fade-in only; `balanced` ⇒ 420ms fade + 6px lift;
`cinematic` ⇒ 640ms fade + 16px slide with cubic-bezier easing. No parallax,
no marquee, no auto-play regardless of register. All variants honor
`@media (prefers-reduced-motion: reduce)`.

## Sections emitted (plan-driven)

| Section | Emphasis | Order | Component (truncated) | Brief fields that fed it |
|---------|----------|-------|-----------------------|--------------------------|
| masthead (`#masthead`) | hero | 0 | header | `project_slug`, `voice_and_tone.example_lines[0]` |
| | | | | **Why this section:** Establish brand identity and primary navigation. |
| | | | | **Rationale:** The masthead uses the brand's wordmark and tagline to immediately set the tone, aligning with the brand's core statement of uniqueness. It serves as the persistent identity element. |
| hero (`#hero`) | hero | 1 | hero-banner | `voice_and_tone.favorite_words`, `voice_and_tone.example_lines[2]`, `voice_and_tone.example_lines[3]` |
| | | | | **Why this section:** Immediately engage visitors and communicate the core value proposition. |
| | | | | **Rationale:** A split-hero layout provides a strong visual anchor for the headline and subhead, allowing the brand's core message of 'uniqueness' and 'limitless' to shine without relying on generic imagery. It creates a bold, text-forward introduction. |
| philosophy (`#philosophy`) | primary | 2 | content-block | `voice_and_tone.favorite_words`, `voice_and_tone.notes` |
| | | | | **Why this section:** Explain the brand's core beliefs and approach to marketing. |
| | | | | **Rationale:** The editorial layout is chosen to present the brand's philosophy in a thoughtful, educational manner, reflecting its 'confessional-educational' voice. It allows for deeper engagement with text-based content. |
| services (`#services`) | primary | 3 | service-grid | `voice_and_tone.favorite_words`, `voice_and_tone.example_lines[3]`, `service_facts` |
| | | | | **Why this section:** Showcase the breadth of services offered by Pedicel Marketing. |
| | | | | **Rationale:** A card-grid layout provides a structured and easily digestible overview of the services, allowing users to quickly scan and understand the offerings. Each card can highlight a key service. |
| our-approach (`#our-approach`) | secondary | 4 | feature-list | `voice_and_tone.example_lines[3]`, `brand_donts[3]`, `voice_and_tone.favorite_words`, `voice_and_tone.notes` |
| | | | | **Why this section:** Detail the client-centric and customized process Pedicel Marketing employs. |
| | | | | **Rationale:** The feature-split layout breaks down the approach into alternating, digestible sections, reinforcing the idea of a step-by-step, customized process. Even without images, this layout provides visual rhythm. |
| why-us (`#why-us`) | primary | 5 | testimonial-quote | `voice_and_tone.example_lines[2]`, `voice_and_tone.favorite_words`, `voice_and_tone.notes` |
| | | | | **Why this section:** Reinforce Pedicel's unique selling proposition and commitment. |
| | | | | **Rationale:** A pull-quote layout highlights a powerful statement that encapsulates the brand's ethos and commitment to 'uniqueness', serving as a memorable differentiator. |
| cta-band (`#cta-band`) | primary | 6 | cta-banner | `voice_and_tone.favorite_words` |
| | | | | **Why this section:** Provide a clear and prominent call to action. |
| | | | | **Rationale:** The CTA band uses a distinct layout and emphasis to draw attention, providing a clear pathway for interested visitors to take the next step. |
| colophon (`#colophon`) | minor | 7 | footer | `project_slug` |
| | | | | **Why this section:** Display copyright and legal information. |
| | | | | **Rationale:** Standard practice for legal disclaimers, rendered discreetly in the footer area, as expected for utility content. |

## Sections skipped by the plan (data absent in brief)

The plan's own `skipped_sections[]` is honored verbatim. Each entry names the
brief fields that would have been needed but are absent.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
| `testimonials` | No testimonials were recoverable from any public surface. Inventing them would violate the 'never facts' rule. | `testimonials` |
| `team-photos` | The brand brief explicitly states there are no real photographs of people, teams, or client work available in the inventory. Generic stock photos are forbidden. | `real_photo_inventory` |
| `case-studies-portfolio` | The brand's actual portfolio imagery and detailed case studies are behind a gated site and could not be inspected. No public data available to populate this section. | `limitations[5]` |

## Sections skipped at render time (no copy or payload)

The plan listed a section but the renderer could not find any copy block or
brief payload for it, so it was dropped rather than emitted empty. These are
reported here in addition to the plan's own skipped list.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
| _(none)_ | | |

## Design decisions (from design-plan.json)

- **Prioritizing text-heavy layouts and content over imagery.**
  - Alternatives considered: Using placeholder stock imagery, Designing sections to strongly suggest imagery without explicitly stating it
  - Why chosen: The `real_photo_inventory` was explicitly empty, and the brief forbade generic stock photography. Focusing on layouts like `editorial`, `feature-split` (as a text split), and `pull-quote` allows the brand's 'confessional-educational' voice and 'uniqueness' message to carry the visual weight, aligning with the brief's strong emphasis on tone and avoiding prohibited visual tropes.
- **Choosing 'balanced' motion vocabulary.**
  - Alternatives considered: Restrained, Cinematic
  - Why chosen: The brand's voice is 'confessional-educational' with 'teacher-like' qualities, which suggests professionalism and clarity over aggressive or overly subtle motion. 'Balanced' allows for subtle, engaging effects that support the content without being distracting, unlike 'cinematic' which might be too flashy, or 'restrained' which might feel too static for a modern web experience.
- **Using distinct and varied layouts for each section.**
  - Alternatives considered: Repeating a few versatile layouts across sections, Using a uniform grid structure for most content
  - Why chosen: The prompt specifically requested varying layouts deliberately, stating that 'a page where most sections share a layout is exactly the templated output we are rejecting'. By using `split-hero`, `editorial`, `card-grid`, `feature-split`, and `pull-quote`, the page maintains visual interest and distinguishes content types, reinforcing the idea of a 'customised' experience rather than a template.

## Contrast decision

- **Neutral body text token:** `--color-neutral-0` (#0b0c0d)
- **Neutral background token:** `--color-neutral-6` (#ffffff)
- **Neutral measured contrast:** 19.58:1
- **Neutral decision note:** text --color-neutral-0 (#0b0c0d) on background --color-neutral-6 (#ffffff) = 19.58:1, meets WCAG AA body-text threshold (4.5:1)

Brand colors remain unchanged for non-text identity uses. When a brand color is
used as normal-sized text, the composer uses the derived `*-text` token below.

- **Primary used as text:** original `#efad2b` on `#ffffff` measured 1.97:1; derived `#9e6d0c` (darken, 22 lightness steps) measures 4.52:1. Text uses: hero tagline text. Original `--color-primary` remains for non-text uses: skip-link background, decorative brand fills.
- **Accent used as text:** original `#3898ec` on `#ffffff` measured 3.06:1; derived `#1477ce` (darken, 13 lightness steps) measures 4.61:1. Text uses: links, navigation hover text. Original `--color-accent` remains for non-text uses: button backgrounds, focus outlines, borders, decorative fills.

## Font substitutions (paid → OFL)

The synthesizer's `font-substitutions.json` sidecar is the authoritative
record of every paid primary family that was rewritten to an OFL/CC-licensed
fallback before being emitted into `tokens.css`. The page never ships a
font the operator hasn't licensed.

- **display:** `?` (?) → `?` (?) — license_notes flagged restricted licensing; substituted 'Switzer' with OFL substitute 'Inter'
- **body:** `?` (?) → `?` (?) — license_notes flag restricted licensing, but the brief explicitly names 'Poppins' as OFL; brand family kept
- **mono:** `?` (?) → `?` (?) — license_notes flag restricted licensing, but the brief explicitly names 'JetBrains Mono' as OFL; brand family kept

- _schema_version:_ 1.0
- _tool_version:_ 1.0
- _generated_at:_ 2026-07-29T19:08:47Z
- _evidence_basis:_ DOM+assets confirmed
- _project_slug:_ pedicel-marketing-redesign-smoke
- _brand_brief:_ /home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/brand-smoke/brand-brief.json
- _reference_tokens:_ /home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/validation/linear-app/tokens

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
