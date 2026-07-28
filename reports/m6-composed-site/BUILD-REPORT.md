# Build report (plan-driven)

Project slug: `pedicel-marketing-redesign-smoke`
Brand name: **Pedicel Marketing** — _derived from project_slug 'pedicel-marketing-redesign-smoke' (suffixes stripped)_
Generated: 2026-07-24T21:55:00Z brief → composed by compose_site.py v1.1 from `design-plan.json`
Outdir: `reports/m6-composed-site`

---

## Layout thesis (from design-plan.json)

- **Statement:** A confessional-teacher's workbook: the page reads like a quiet lesson on what makes a brand unique, with the gold 'i' dot from the logo acting as a moving highlighter that travels down the page to mark every lesson and every sentence that lands.
- **Audience:** Small-to-mid business owners evaluating an inbound marketing and branding partner; people who distrust hype and want a calm, opinionated teacher to walk them through what 'customised' actually means.
- **Job to be done:** Convert skeptical first-time visitors into qualified discovery-call bookings by proving the agency's point of view in the page itself — not in a 'why us' block.
- **Why this, not generic:** Stock agency templates lead with a centered hero, a three-icon service grid, and a 'trusted by' wall. The brand's own voice ('All brands are unique, they just haven't shown it to the world yet' / 'Limitless.' / 'customised from top to bottom') is a teacher's voice, not a competitor's. The layout must therefore behave like a margin-noted textbook, not a pitch deck. The gold dot is a literal carryover from the logo's most distinctive feature (the dot above the 'i' in 'Pedicel') and is the only saturated color the brand actually owns — using it as a navigational marker is more honest than burying it in a button.

## Signature element (from design-plan.json)

- **Name:** The gold 'i'-dot highlighter
- **Description:** A 10px gold circle (#efad2b) that travels down the page as a margin marker beside every lesson number, every chapter being read, and every teacher-margin note in the annotated image essay. It is a literal enlargement of the single saturated pixel of color in the brand's own logo — the dot above the 'i' in 'Pedicel'.
- **Why it fits the brand:** It is the only saturated color the logo actually owns (per palette_from_logo.rationale: 'the only saturated brand color in the logo SVG'). Using it as a moving highlighter, rather than burying it inside a button, treats the logo's most distinctive feature as the page's reading guide. It also visually echoes the brand's own surfacing language of marking the 'unique' thing on every page.
- **Implementation note (rendered in HTML+CSS as a real device):**
  Render once as a fixed-position SVG dot in a single page-level layer; recompute its top offset on scroll using IntersectionObserver against each numbered lesson/chapter node. Animate position with a 280ms cubic-bezier(.2,.7,.2,1) so the movement feels like a marker sliding down a page, not a UI flourish. Never animate opacity, never pulse, never use it inside a button — those uses would turn it into a generic accent.

The signature element is emitted in HTML as `<span class="signature-dot" aria-hidden="true">`
and styled in `styles.css` under the `.signature-dot` selector. It uses
`var(--color-primary)` so it picks up whatever the synthesized token system
declares as the brand's primary color (the design plan calls for the literal
gold #efad2b; the token system reserves the same hex for `--color-primary`).
It appears inline as the period ending the thesis headline, beside numbered
curriculum rows and process steps, and trailing the CTA button.

## Motion vocabulary (from design-plan.json)

- **Register:** `restrained`
- **Rationale:** A confessional-educational voice demands reading-speed motion, not showcase motion. The only 'cinematic' moment is the gold dot's slide, and even that is short enough to feel like a marker, not a transition. No parallax, no scroll-jacking, no video, no spring overshoots — all of those would betray the teacher register.
- **Effects:**
  - Gold dot position interpolation on scroll (280ms, cubic-bezier easing)
  - Lesson/chapter accordion expand via height + opacity (200ms ease-out)
  - Margin-note underlines draw in on viewport entry (1 line, 400ms)
  - Sticky manifesto index highlight swap (no animation, instant)

The plan's register drives `styles.css` via `_motion_css_for_register()` —
`restrained` ⇒ 320ms fade-in only; `balanced` ⇒ 420ms fade + 6px lift;
`cinematic` ⇒ 640ms fade + 16px slide with cubic-bezier easing. No parallax,
no marquee, no auto-play regardless of register. All variants honor
`@media (prefers-reduced-motion: reduce)`.

## Sections emitted (plan-driven)

| Section | Emphasis | Order | Component (truncated) | Brief fields that fed it |
|---------|----------|-------|-----------------------|--------------------------|
| cover (`#cover`) | hero | 0 | Asymmetric editorial cover: left 60% holds a single sentence-case belief stateme… | `voice_and_tone.register`, `voice_and_tone.example_lines`, `voice_and_tone.sentence_case`, `palette_from_logo.primary`, `palette_from_logo.secondary`, `typography_recommendation.display_family` |
| | | | | **Why this section:** Set the teacher-register tone and introduce the signature gold-dot highlighter in its largest, slowest form. |
| | | | | **Rationale:** The brand's strongest recoverable copy is one short sentence ('All brands are unique, they just haven't shown it to the world yet.'). Leading with it at display size, in sentence case, with no chrome around it, is the most on-voice choice. Putting the gold dot on the lesson index makes the signature element discoverable in the first screen without ever being labeled as a logo feature. | Revision rationale: The thesis says the dot must 'mark every lesson and every sentence that lands'; right now it floats in the right gutter with nothing to mark. A lesson number beside it converts decoration into structure and starts the workbook metaphor on the very first screen. | Revision rationale: The brand thesis requires the gold dot to act as a moving highlighter beside every lesson number; without a numbered eyebrow and a connecting rule, the dot is just ornament and the workbook metaphor never starts. | Revision rationale: The right ~55% of 1440px currently holds a single shape; replacing that air with a margin-note + dot makes the signature element legible and gives the desktop layout a real two-column rhythm. | Revision rationale: The brand thesis requires the gold dot to act as a margin highlighter next to lesson markers; right now the dot floats free and the lesson number is buried in the eyebrow at the bottom of the section. | Revision rationale: The current vertical gap between the headline and tagline (roughly 40px) plus the further gap before the dot makes the first screen feel unresolved; tightening the headline-tagline pair creates a single composed block. | Revision rationale: The thesis says the gold dot acts as a moving highlighter beside every lesson number; right now the hero has no lesson number, so the dot has no lesson to mark. Adding 'Lesson 01' and a short gold rule gives the dot a concrete target and converts the hero from a billboard into the first page of a workbook. | Revision rationale: At 1440px the headline ends near x≈560px and ~880px of canvas is unused apart from one ~80px gold circle. A second small element on the right column gives the dot company and turns the right half from dead space into the 'margin' the thesis keeps referencing. | Revision rationale: On mobile the circle currently sits as a second visual block under the copy with the same visual weight as the headline, which contradicts the 'margin marker' role. A smaller dot pinned to the left gutter restores the teacher-margin metaphor at narrow widths. | Revision rationale: The signature element is defined as a 10px margin marker beside lesson numbers — at 13× that size it stops being a highlighter and becomes a decorative sun, breaking the brand_fit and focal_point contracts. | Revision rationale: The thesis calls for a workbook where the dot marks every lesson being read; a chapter index in the right column turns dead canvas into the page's table of contents and gives the dot a structural job to do. |
| manifesto (`#manifesto`) | primary | 1 | Two-column editorial: a narrow left column (28%) holds a sticky numbered index o… | `voice_and_tone.register`, `voice_and_tone.notes`, `voice_and_tone.favorite_words`, `voice_and_tone.banned_words`, `voice_and_tone.avg_sentence_length_words` |
| | | | | **Why this section:** State the agency's teaching philosophy in long-form, using the teacher's margin-note cadence. |
| | | | | **Rationale:** Confessional-educational voice is best shown, not declared. A numbered list of belief-statements, written at the brand's actual ~13-word average sentence length, lets the voice carry the section without resorting to testimonials (which the brief flags as unrecoverable). | Revision rationale: The layout thesis explicitly describes a workbook with margin notes and a traveling highlighter; today the manifesto is a generic centered block. Splitting it into body + margin column activates the workbook metaphor on the first content section after the hero. | Revision rationale: right now the manifesto and the uniqueness-lesson heading use visually identical subhead weight and shape, so the page has no chapter rhythm; a numeral + margin dot makes this section read as a chapter opening rather than a generic blog paragraph. | Revision rationale: Currently 'What we believe' is followed by a single short paragraph, which is exactly the shape the thesis asks the page to avoid — a list and a pull-quote turn it into the teacher-margin note the brand voice promises. | Revision rationale: Two equally-large headlines in a row break the reading rhythm and remove the sense that the hero is the lesson opener. Demoting this h2 and placing the dot here also creates the first 'travel' of the signature element from hero into manifesto, fulfilling the layout thesis. | Revision rationale: Right now the manifesto heading sits ~340px below the hero with no divider, so the user has no signal that a new unit of content has begun; the brand thesis explicitly frames the page as a sequence of lessons and chapters. | Revision rationale: The current layout centers body copy across the full content width, leaving no margin gutter for the signature dot to slide through; a left-anchored narrow column recreates the workbook-margin effect. | Revision rationale: Two consecutive centered headlines with a single body paragraph between them produce a flat rhythm; a margin note gives the section the workbook feel the thesis calls for and gives the dot a real job. | Revision rationale: The signature element is supposed to travel down the page marking every lesson number; without numerals and sub-beliefs there is nothing for it to travel between. This also breaks the 'every section is h2 + p' shape the page currently has. | Revision rationale: Right now the manifesto reads as a continuation of the hero — same background, same alignment, same shape. A background shift turns it into a visible chapter opening, which is what the 'quiet lesson' thesis depends on. |
| uniqueness-lesson (`#uniqueness-lesson`) | primary | 2 | Four-step teaching block laid out as a vertical timeline rather than a horizonta… | `voice_and_tone.example_lines`, `voice_and_tone.favorite_words`, `palette_from_logo.primary`, `palette_from_logo.secondary`, `brand_donts` |
| | | | | **Why this section:** Teach the visitor the agency's core framework (the thing every 'unique' brand has to do) without calling it a framework. |
| | | | | **Rationale:** The brief's first explicit banned default is the three-column feature grid with icons. A vertical numbered timeline is the same information density without the template fingerprint, and it lets the gold dot carry meaning instead of decoration. | Revision rationale: The thesis states the gold dot should travel beside every lesson number. This section is literally called the 'uniqueness lesson' yet has no number and no dot, breaking the brand's own reading-guide metaphor. | Revision rationale: A single paragraph after the hero cannot carry the 'confessional-teacher's workbook' metaphor. Numbered, sentence-case lesson steps give the page rhythm and give the gold dot multiple anchor points to mark as it travels down — the structural payoff the signature element was designed for. | Revision rationale: The brand's signature element is meant to mark 'every sentence that lands', but no section currently has a margin note for the dot to point at; building one here establishes the pattern that can then repeat down the page. | Revision rationale: The thesis describes a moving highlighter that travels between lessons, but a single block of body copy gives the dot nothing to move between; numbered sub-lessons create the reading checkpoints the signature element needs. |
| services-as-chapters (`#services-as-chapters`) | primary | 3 | Expandable chapter list (accordion with persistent chapter numbers). Each chapte… | `service_facts`, `voice_and_tone.register`, `voice_and_tone.formality_score_1to5` |
| | | | | **Why this section:** Present the eight public services as chapters of a customised curriculum rather than a service catalog. |
| | | | | **Rationale:** Service facts are the most complete recoverable factual inventory (eight named services with descriptions). Grouping them as chapters of a curriculum — rather than cards with icons — matches the teacher register and avoids the banned 'three-column feature grid'. | Revision rationale: Currently services-as-chapters reads as a heading plus a single paragraph; the section id literally calls them chapters but they have no chapter form. A numbered list turns the section into the annotated-chapter essay the thesis promises. | Revision rationale: the brand's four-things framing ('The four things every unique brand has already done') only earns its weight if it reads as four distinct chapters; identical card styling without numerals or margin dots will make it feel like another generic 4-column grid. | Revision rationale: Every section currently repeats the same heading + paragraph shape, so the page reads as a flat blog. The thesis says it should read like a workbook of lessons; numbering and chapter framing are the cheapest way to introduce that rhythm without adding imagery. | Revision rationale: A grid of four numbered cells gives the dot four discrete anchor points to travel between, which is what the implementation_note requires; the current single-paragraph layout offers the dot nowhere to go. | Revision rationale: The thesis is built around a workbook that reads top-to-bottom; a multi-column grid breaks that spine. A vertical numbered list with the dot in the margin preserves reading order, gives the dot a consistent left-edge channel to slide down, and lets each chapter read as a 'lesson' rather than a service card. | Revision rationale: The layout thesis describes a single dot moving down the page as a marker; without a sequence of nodes to travel between, the dot is static and the workbook metaphor is reduced to a single accent. | Revision rationale: Equal cards flatten the teacher-workbook thesis into a generic services grid; a chapter-opening pattern with a numeral+dot marker reintroduces the signature element as a reading guide and breaks the section rhythm. | Revision rationale: The signature element is supposed to mark every lesson being read; without lesson numbers beside each service, the dot has nothing to travel between and the chapters don't read as chapters. |
| the-customised-proof (`#the-customised-proof`) | secondary | 4 | Annotated image essay: a single tall image (the brand's own OG share card, used … | `real_photo_inventory`, `voice_and_tone.favorite_words`, `brand_donts`, `limitations` |
| | | | | **Why this section:** Show what 'customised from top to bottom' means in practice, using only the imagery the brand actually exposes. |
| | | | | **Rationale:** The brief explicitly states no real photograph of a person, team, or client work was recoverable. Using the brand's own og:image as the only visual and annotating it teacher-style is honest about what is available while still demonstrating the 'customised' point of view. | Revision rationale: every section currently shares the same white background and the same grey hr divider, which is the strongest signal of a templated layout; one deliberate background break is the single cheapest way to signal bespoke structure. | Revision rationale: The brand's own argument is that its approach is 'customised from top to bottom', yet the section currently makes that claim in a single paragraph. A three-column proof structure embodies the claim in the layout itself and breaks the monotony of the repeating heading + paragraph shape. | Revision rationale: The brief specifies 'every teacher-margin note in the annotated image essay' as a dot use case; without the annotated layout there is no surface for those margin notes to live on. | Revision rationale: the 'proof' section is the one place a workbook reader expects concrete evidence, but as rendered it is the same h2 + paragraph shape as the manifesto, so it carries no extra weight. Splitting it into prose + a dotted checklist gives the section a distinct chapter shape and finally gives the gold dot a second home on the page. | Revision rationale: The signature element description explicitly references 'the annotated image essay' with margin notes; the current layout has no annotated visual and no margin notes, so the signature element has nothing to highlight. |
| lead-generation-cta (`#lead-generation-cta`) | secondary | 5 | Single-sentence CTA block: one short paragraph framed as an invitation to the ne… | `service_facts`, `palette_from_logo.accent`, `voice_and_tone.register`, `voice_and_tone.banned_words` |
| | | | | **Why this section:** Convert the reader into a discovery-call booking without breaking the teacher register. |
| | | | | **Rationale:** The brand's positioning is lead-generation-driven (per service_facts: 'Sale Funnels', 'Paid Advertising'), so the page must end with a clear conversion path. Restricting the accent blue to this single block keeps the gold dot as the dominant accent elsewhere and avoids the 'everything is a button' generic pattern. | Revision rationale: The signature element brief explicitly forbids using the dot inside a button ('those uses would turn it into a generic accent'). A text-link CTA with the dot as the link's starting point keeps the lesson-metaphor intact to the final screen and avoids the agency-default 'Book a call' button pattern. |
| colophon (`#colophon`) | minor | 6 | Single short paragraph plus a small monospaced token table (font families, hex v… | `typography_recommendation.license_notes`, `typography_recommendation.mono_family`, `palette_from_logo.primary`, `palette_from_logo.secondary`, `palette_from_logo.accent`, `palette_from_logo.neutrals`, `brand_donts` |
| | | | | **Why this section:** Disclose fonts, colors, and license notes the brief flagged as sensitive (Switzer commercial use). |
| | | | | **Rationale:** Switzer requires a paid commercial license; the brief explicitly bans vendoring the OTF into production. A colophon that states the substitution rule transparently is both legally safer and on-voice for a brand whose tagline is about uniqueness. |

## Sections skipped by the plan (data absent in brief)

The plan's own `skipped_sections[]` is honored verbatim. Each entry names the
brief fields that would have been needed but are absent.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
| `testimonials` | The brief's limitations section explicitly states no testimonials are recoverable from any public surface and that including one would have been invention. | `testimonials` |
| `case-studies` | No client portfolio imagery or case-study metrics were recoverable; the brand's own site is blocked by a WAF and Instagram is gated. Building a case-studies section would require fabricated clients. | `real_photo_inventory`, `social_highlights.linkedin`, `social_highlights.instagram` |
| `trusted-by-logos` | No client list is recoverable from any public surface. A logo wall would either be empty or invented. | `service_facts`, `real_photo_inventory`, `limitations` |
| `team` | No real photographs of the team are recoverable; only the LinkedIn company logo is available. A team grid would have to use avatars or be omitted. | `real_photo_inventory` |
| `pricing` | Every service_facts entry is marked 'price_range: not disclosed on public surfaces'. A pricing table would be invention. | `service_facts.price_range` |
| `blog-or-thought-leadership` | social_highlights.linkedin and social_highlights.instagram are both empty by design; the LinkedIn public surface is a tagline and about blurb, not a content feed. There is no recoverable body of posts to surface. | `social_highlights.linkedin`, `social_highlights.instagram`, `sources.linkedin.top_posts`, `sources.instagram.grid_themes` |

## Sections skipped at render time (no copy or payload)

The plan listed a section but the renderer could not find any copy block or
brief payload for it, so it was dropped rather than emitted empty. These are
reported here in addition to the plan's own skipped list.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
| _(none)_ | | |

## Design decisions (from design-plan.json)

- **Lead with a single sentence-case belief statement at display size instead of a centered headline + subhead + CTA hero.**
  - Alternatives considered: Centered hero with two CTAs and a stock background photo, Video background with a 10-second manifesto loop, Carousel of three rotating taglines
  - Why chosen: The brand's strongest recoverable voice asset is one short sentence ('All brands are unique…'). A centered-everything hero is an explicit forbidden default and would dilute the teacher register. A single sentence at 64px reads like the first line of a book, which matches the workbook thesis.
- **Use a vertical timeline for the four-step uniqueness lesson instead of a horizontal four-column grid.**
  - Alternatives considered: Four equal cards in a single row with line icons, Tabs across the top with one panel of content, A single long-form essay with inline pull-quotes
  - Why chosen: The three-column feature grid with icons is the first banned default in brand_donts. A vertical timeline preserves the four-part structure the brand needs to teach, lets the gold dot act as the step marker, and reads at scroll-speed instead of glance-speed.
- **Render the eight LinkedIn-listed services as expandable chapters rather than as a grid of service cards with icons.**
  - Alternatives considered: Eight cards with one icon each in a 4×2 grid, A single long-form services page reached from a 'Services' link, Three category buckets (Marketing / Branding / Web) each holding the relevant services
  - Why chosen: service_facts gives eight named services with descriptions and no prices; that is exactly the shape of a chapter list. Cards would force invention of icons and would compete with the gold dot for attention. Categories would lie about the brand's actual flat list.
- **Restrict the Webflow interactive blue (#3898ec) to a single CTA button and use gold (#efad2b) as the dominant accent everywhere else.**
  - Alternatives considered: Use #3898ec as the primary brand color throughout, Use a purple gradient as the primary surface (per the Webflow CSS default), Split accents evenly between gold and blue across the page
  - Why chosen: palette_from_logo.rationale is explicit: gold is the only saturated color in the logo SVG and is the brand's signature. Purple gradients are explicitly banned. A single accent creates a clear visual hierarchy: gold = reading/lesson, blue = the one interactive moment.
- **Include a colophon that names the Switzer commercial-license substitution rule instead of vendoring Switzer OTF files.**
  - Alternatives considered: Self-host Switzer OTF in the production bundle, Silently substitute Inter for Switzer without disclosure, Use only system fonts and skip the display family
  - Why chosen: typography_recommendation.license_notes and brand_donts both flag that the free personal-use Switzer license forbids commercial use. Silent substitution would be dishonest; bundling would be a license violation. A colophon that names the rule is on-voice for a brand whose tagline is about showing what was hidden.
- **Use the brand's own og:image as the single visual in the annotated image essay instead of inventing portfolio imagery.**
  - Alternatives considered: Commission or generate bespoke case-study imagery, Use abstract decorative shapes instead of any photograph, Omit imagery entirely and use type only
  - Why chosen: real_photo_inventory contains no real photographs of people, team, or client work — only the logo SVG, the OG share card, and the LinkedIn company logo. brand_donts bans generic stock photography. The OG card is brand-owned and is the only honest visual the agency can currently expose without invention.
- **Skip testimonials, case studies, a 'trusted by' wall, a team grid, pricing, and a blog feed entirely.**
  - Alternatives considered: Include a single invented client quote labeled 'example', Show placeholder case-study cards marked 'coming soon', Source client logos from the agency's LinkedIn follower list
  - Why chosen: The brief's limitations section is explicit that every one of those sections would have to be invented. The layout thesis explicitly prefers showing the agency's point of view in the page itself over borrowing third-party credibility. The skipped_sections list names each missing brief field so the gap is auditable, not hidden.

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
- _generated_at:_ 2026-07-28T23:19:50Z
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
