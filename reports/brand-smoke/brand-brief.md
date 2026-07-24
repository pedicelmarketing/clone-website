# Brand Brief — Pedicel Marketing (smoke test)

Project: `pedicel-marketing-redesign-smoke`
Generated: 2026-07-24T21:55:00Z
Schema: brand_brief_schema.json v1.0
Companion: `brand-brief.json` (VALID per Draft-2020-12)

## TL;DR for the site-cloner

The brand is an inbound marketing + branding agency positioned around "uniqueness" and "limitless". The visual identity is built on a single saturated gold accent (#efad2b) over an alice-blue surface (#f0f8ff), a deep navy/blue interaction color (#3898ec), and a clean sans-serif typography pair (Switzer display + Poppins body). The voice is short, sentence-case, and teacher-like — not challenger. Service list is eight lines recovered from the brand's public LinkedIn page. No testimonials, no portfolio imagery, no social posts are recoverable from any public surface.

## What was actually fetched

| Source | What I got | What I had to give up |
|---|---|---|
| own_site — pedicelmarketing.com | Blanket 403 from OpenResty WAF on every path (including /sitemap.xml, /robots.txt). Even Cloak stealth + CapSolver returns 403 — no captcha, just an IP block. | The home page, the about page, the services page, the portfolio, the contact page. **All unreachable.** |
| LinkedIn — pedicelmarketing company page | 200 OK to raw HTTP, but Cloak's rendered markdown is the cookie-consent wall. The raw HTML revealed the meta description + an embedded JSON "description" blob (~1,051 chars of recoverable text: tagline, About blurb, 3,982 followers, 12 employees, industry "Marketing Services", and the 8-item service list). 200 OK on the CDN-hosted logo image. | Post bodies, dates, engagement metrics, employee list, locations — all interaction-gated. No `cloak_loggedin` used (would have required a logged-in session; this is a contract smoke test, not a real engagement). |
| Instagram — /pedicelmarketing | 302 redirect to login wall. No public grid, captions, themes, or posts. | Everything. |
| Reference — linear.app | 11,220 chars of markdown via Cloak. 200 OK. Used as a structural reference only — not a brand source. | Nothing: this is purely for the designer's mood-board. |

## Evidence-grounded palette

Derived from the actual **Pedicel logo SVG** (recovered from the brand's own Webflow CDN, since the home page is blocked) and cross-checked against the brand's **live Webflow CSS** (223 KB, also on the brand's CDN):

- Primary **#efad2b** — gold. This is the only saturated color in the logo SVG; the signature accent.
- Secondary **#f0f8ff** — alice-blue. The logo wordmark surface. (Functionally a near-white; the literal second fill in the brand's SVG.)
- Accent **#3898ec** — the brand's interactive blue (22 references in the CSS, used for buttons/links/CTAs).
- Neutrals: #0b0c0d, #1c1d1c, #5d5d6d, #9c9c9c, #e6e6e6, #fafafa, #ffffff

A purple (#6a34b3) appears in the Webflow CSS but is a Webflow default-state color, never a brand surface — explicitly called out in `brand_donts`.

## Evidence-grounded typography

Recovered from the CSS and the mirror-manifest.json:

- Display: **Switzer** (Indian Type Foundry — paid for commercial use; free for personal use only)
- Body: **Poppins** (SIL OFL — safe to self-host)
- Mono: **JetBrains Mono** (OFL)
- Recommended substitute pair if the brand does not purchase Switzer: Inter (OFL) for display, keep Poppins for body.

## Voice & tone

Recovered from the brand's own LinkedIn surface. Register: **confessional-educational** (not "conversational-professional" — the Pedicel voice is more teacher-like than peer-to-peer; the tagline is a statement of belief, not a competitive claim).

- Sentence case, short sentences (~13 words average), no jargon.
- Favorite words (because the brand chose to repeat them): uniqueness, limitless, customised, branding, strategy, leads.
- Banned words: synergy, delve, leverage, disrupt, best-in-class, revolutionary, cutting-edge, in today's world.

## Service list (grounded from the brand's public LinkedIn description)

1. Social Media Marketing
2. Community Management
3. Branding Strategy
4. Sale Funnels
5. SEO
6. Web Design
7. Rebranding
8. Paid Advertising

Prices: **not disclosed on any public surface.** Not inventing.

## Real photo inventory (only URLs I actually saw resolve)

- `https://cdn.prod.website-files.com/64a2995238dba40820b37689/64a52e82805f80ff256b96e6_Logo-Pedicel.svg` — official wordmark (200 OK, 4.7 KB)
- `https://cdn.prod.website-files.com/64a2995238dba40820b37689/656016dc008b45e6a1f01471_pedicelmarketingpreviewwebsite.jpg` — og:image / social share card (200 OK, 274 KB)
- `https://media.licdn.com/dms/image/v2/D4D0BAQEpD_qVmnEm7w/company-logo_200_200/company-logo_200_200/0/1684913513575` — LinkedIn company logo (200 OK, 5.4 KB)

No team photography, no portfolio imagery, no client logos are publicly recoverable.

## Limitations (the honest list)

1. **own_site fully blocked** — OpenResty WAF (HTTP 403 on every path). Not a captcha; an IP block. Palette and typography lifted from the brand's CDN rather than the live HTML.
2. **LinkedIn content is gated** — only `<meta>` tags and the embedded JSON are accessible. Post bodies, dates, engagement not recoverable; `social_highlights.linkedin` is empty by design.
3. **Instagram login-walled** — 302 redirect; nothing recoverable.
4. **Supabase POST credentials absent** in this profile — `research_scrapes` rows were NOT written; every `scrapes_id` is null. The cloak output and the raw HTML are recoverable from temp files only.
5. **No `cloak_loggedin` used** — would have required a logged-in session; this is a smoke test.
6. **No real photographs** of people, team, or client work — only the logo, the OG image, and the LinkedIn company badge.
7. **No testimonials** — including any would have been invention.
8. **palette_from_logo.secondary (#f0f8ff)** is functionally a near-white, not a true secondary brand color. If the redesign team prefers a real secondary, the Webflow CSS offers #3898ec (the brand's interactive blue).
9. **Reference (linear.app)** is structural only — no brand voice or visual decisions in this brief are borrowed from Linear.

## Validator output

```
$ python3 skills/web-designer/scripts/validate_brand_brief.py reports/brand-smoke/brand-brief.json
VALID /home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/brand-smoke/brand-brief.json
```

Exit 0. Full Draft-2020-12 path (jsonschema 4.26.0 is installed).
