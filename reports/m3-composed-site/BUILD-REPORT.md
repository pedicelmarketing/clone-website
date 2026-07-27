# Build report

Project slug: `pedicel-marketing-redesign-smoke`
Brand name: **Pedicel Marketing** — _derived from project_slug 'pedicel-marketing-redesign-smoke' (suffixes stripped)_
Generated: 2026-07-24T21:55:00Z brief → composed by compose_site.py v1.0
Outdir: `reports/m3-composed-site`

---

## Sections emitted

| Section | Emitted | Why | Brief fields that fed it |
|---------|---------|-----|--------------------------|
| Hero (`#hero`) | yes | emitted: voice_and_tone.example_lines[0] used as headline | `voice_and_tone.example_lines`, `voice_and_tone.register` |
| About (`#about`) | yes | emitted: voice_and_tone.notes used as about copy | `voice_and_tone.notes`, `voice_and_tone.register` |
| Services (`#services`) | yes | emitted: service_facts[] used as service cards | `service_facts[]` |
| Brand assets & social (`#social-photos`) | yes | emitted: real_photo_inventory[] used as asset list | `real_photo_inventory[]`, `social_highlights.linkedin[]`, `social_highlights.instagram[]` |
| Contact / CTA (`#contact`) | yes | emitted: always included (every site needs a contact section); CTA copy derived from voice register + favorite_words | `voice_and_tone.register`, `voice_and_tone.favorite_words` |

## Sections skipped (data absent in brief)

| Section | Skipped | Why | Brief fields that would have fed it |
|---------|---------|-----|------------------------------------|
| Testimonials (`#testimonials`) | yes | skipped: brief.testimonials[] was empty (no quotes recoverable) | `testimonials[]` |

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
- **Copied to site as:** `reports/m3-composed-site/tokens.css`
- **Token JSON:** `reports/m3-token-synthesis/tokens/dist/tailwind-tokens.json`
- **Audit:** PASS — all 23 expected token vars are declared in tokens.css

The page CSS links `tokens.css` and references token CSS variables for every
color, spacing value, radius, and shadow. No raw hex colors are emitted in
`styles.css`:

```
PASS — no raw hex literals in styles.css (every color is a token)
```



## Reference brief
No `--reference-report` directory was provided; the site was composed from the brand brief + synthesized tokens alone.

## Accessibility decisions

- **Semantic landmarks:** `<header role="banner">`, `<nav>`, `<main>`,
  `<section aria-labelledby>`, `<footer role="contentinfo">`.
- **Headings:** one `<h1>` (in the hero), logical nesting, no skipped levels.
- **Skip link:** `.skip-link` is the first focusable element; visible only on focus.
- **Alt text:** every `<img>` uses `real_photo_inventory[].subject` as `alt`.
- **Form labels:** every `<input>` and `<textarea>` has a `<label>` with a
  matching `for` attribute.
- **Focus styles:** `:focus-visible` on every interactive element.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` disables the
  CSS-only fade/slide-up reveals.
- **Color contrast:** see "Contrast decision" above.

## Motion decisions

- Default: CSS-only `fade-slide-up` reveal on each section (360ms ease-out).
- Honors `prefers-reduced-motion: reduce` — animation duration drops to ~0ms.
- No JavaScript animation libraries (matches the brand brief's `register`
  `"confessional-educational"` if it contained that word, or any register whose
  profile is restrained). Heavier libraries are an M3+ option, not a default.

## Limitations carried forward from the brand brief

The brief's own `limitations[]` array is reproduced verbatim below. Every entry
below is a research-side limitation that the site honors by *not* inventing
content; nothing in the emitted page invents quotes, photos, services, or
stats.

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

It is **not yet M4-Validated**: the 8-gate validation (accessibility, performance,
site-wide audit, responsive, motion, source-paired) is M4 scope and is exercised
by `references/validation-checklist.md` once M4 lands.
