# End-to-end web-designer workflow

**Date:** 2026-07-24 · **Author:** site-cloner-agent · **Branch:** feat/web-designer
**Status:** Research-only design document. Describes a future `web-designer` skill; no code
is written here. See `integration-plan.md` for the phased build-out.

**The thesis.** Phase 1 of the pipeline (today) is a one-URL faithful baseline. Phase 2 (the
goal) is a *three-input* design:

1. **Brand site** — the brand's *own* current site (the source of truth for its voice,
   offering, and existing assets).
2. **Reference site** — a site the user names to emulate (the source of structural craft and
   the vocabulary to *differentiate from*).
3. **Brand social** — LinkedIn, Instagram, X (the source of the brand's *real* imagery,
   tone, and recent activity — the things a stock site never has).

The deliverable is a new site that is **brand-authentic** (real copy, real photos, real
services, real testimonials) and **10x better than the reference** (the reference's *craft*
without copying its *code*).

This document defines the pipeline, the **research-agent handoff** (the critical
inter-profile contract), and one concrete end-to-end example.

---

## The pipeline at a glance

```
                ┌──────────────────────────────┐
                │  INPUTS (from the operator)  │
                │  - brand_site (URL)          │
                │  - reference_site (URL)      │
                │  - brand social handles      │
                │  - brand's own assets (opt)  │
                └──────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │  STEP 1 — UNDERSTAND THE REFERENCE          │
        │  (tools: capture_assets, extract_tokens,    │
        │   motion_audit, see understand-the-         │
        │   reference.md)                            │
        │  output: reports/reference/*               │
        └────────────────────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │  STEP 2 — UNDERSTAND THE BRAND              │
        │  (delegated to research-agent, see §Handoff)│
        │  output: reports/brand/brand-brief.json     │
        └────────────────────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │  STEP 3 — DESIGN (10x, brand-authentic)     │
        │  (web-designer skill: tokens, sections,     │
        │   copy, motion, components)                 │
        │  output: project scaffolding + final site  │
        └────────────────────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │  STEP 4 — VALIDATE (axe, lighthouse,        │
        │   unlighthouse, viewports, motion-audit,    │
        │   copy-humanize pass)                       │
        │  output: validation-report.md              │
        └────────────────────────────────────────────┘
                          │
                          ▼
                ┌──────────────────────────────┐
                │  DELIVERABLE:                │
                │  - new site (built)          │
                │  - Lighthouse ≥ 90           │
                │  - axe-core: 0 violations    │
                │  - brand assets: classified  │
                │    and replaced where needed │
                │  - 10x-vs-reference evidence │
                └──────────────────────────────┘
```

---

## Step 1 — Understand the reference

Owner: **site-cloner agent itself**, with the `nt-site-mirror` skill.

This is *not new*. It is the existing phase-1 pipeline repurposed: instead of producing a
faithful mirror as the deliverable, we use it to produce the **reference brief** (sections,
tokens, components, motion) that step 3 consumes.

Substeps:

1. `capture_assets.py <reference_url> -o reports/reference/asset-graph.json` — runtime asset
   graph (existing).
2. `extract_tokens.py <reference_url> -o reports/reference/tokens/` — new; emits
   `tokens/color.json`, `tokens/typography.json`, `tokens/spacing.json`, `tokens/radius.json`,
   `tokens/shadow.json` per `understand-the-reference.md` §2.
3. `inventory_copy.py <reference_url> -o reports/reference/copy.json` — new; emits the copy
   inventory with section/role/source_url labels.
4. `inventory_components.py <reference_url> -o reports/reference/components.json` — new;
   emits the component instance map.
5. `infer_breakpoints.py <reference_url> -o reports/reference/breakpoints.json` — new; emits
   the responsive breakpoint map.
6. `motion_audit.py --source-url <reference_url> --local-url <reference_url> --record-only
   --out reports/reference/motion --seconds 12` — reuse existing tool, *record-only* mode,
   to produce a webm of the reference's motion vocabulary. (We don't compare to a mirror
   here; we just capture.)
7. Concatenate into `reports/reference/REPORT.md` per `understand-the-reference.md` §7.

**Honesty constraint:** if any substep is blocked (e.g. reference is a Wix site with
session-coupled root document — see `nt-site-mirror`'s builder-runtime guidance), document
the block and fall back to observation-only. Do not invent a section list you did not observe.

---

## Step 2 — Understand the brand (the research-agent handoff)

Owner: **`research-agent` profile** (via Cloak + Firecrawl + social research).

This is the **most important step in the workflow** and the one that requires a clean
inter-profile contract. The site-cloner agent does *not* scrape the brand site itself; it
delegates to research-agent because:

- research-agent has anti-bot (Cloak) and JS-render (Firecrawl OSS) capabilities.
- research-agent persists everything in `research_scrapes` (Supabase DB) with a `project_tag`,
  so the brand brief is *replayable* across sessions — no re-fetch cost.
- research-agent already has `bin/research_run.py` for multi-source orchestration.
- social sources (LinkedIn, Instagram) have specific scraping constraints that site-cloner's
  Playwright-based pipeline is not optimized for.

### §2.1 — What site-cloner asks for (the request)

When site-cloner invokes research-agent, it posts a structured brief to the
`#research` channel (Discord home of the `research-agent` profile). The brief has this shape:

```json
{
  "task": "brand_research_for_redesign",
  "project_slug": "pedicel-marketing-redesign",
  "brand": {
    "name": "Pedicel Marketing",
    "own_site": "https://pedicelmarketing.com",
    "social": {
      "linkedin": "https://www.linkedin.com/company/pedicel-marketing",
      "instagram": "https://www.instagram.com/pedicelmarketing",
      "twitter": null
    },
    "assets_provided": [
      "/Users/sergio/Dropbox/pedicel-brand/logos/Pedicel_Primary_Logo_CMYK.ai",
      "/Users/sergio/Dropbox/pedicel-brand/photos/team/*.jpg"
    ],
    "design_brief": "Make the site 10x better than https://linear.app — we are a B2B SaaS content marketing agency; professional but warm; primary audience is CMOs of mid-market DTC brands; motion vocabulary should be restrained, not showy; existing site is stock-template."
  },
  "reference": {
    "url": "https://linear.app",
    "rationale": "We admire the choreographed page-load, restrained motion, and the typography hierarchy. We do NOT want to copy the visual identity."
  },
  "deliverable": {
    "format": "brand-brief.json + brand-brief.md",
    "save_to": "reports/brand/",
    "must_include": [
      "voice_and_tone",
      "palette_from_logo",
      "typography_recommendation",
      "real_photo_inventory",
      "service_facts",
      "social_highlights",
      "testimonials",
      "brand_donts"
    ]
  }
}
```

### §2.2 — What research-agent returns (the response)

Research-agent owns the full fetch — site-cloner does not call `cloak_fetch.py` or
`social_research.py` itself. The response is two files:

1. **`reports/brand/brand-brief.json`** — the machine-readable artifact. Schema below.
2. **`reports/brand/brand-brief.md`** — a 1-page human-readable summary that site-cloner reads
   before designing.

The JSON schema (this is the contract; do not deviate):

```json
{
  "schema_version": "1.0",
  "project_slug": "pedicel-marketing-redesign",
  "fetched_at": "2026-07-24T16:30:00Z",
  "research_scrapes_ids": [142, 143, 144, 145, 146, 147],
  "sources": {
    "own_site": {
      "url": "https://pedicelmarketing.com",
      "fetch_backend": "cloak",
      "char_count": 18432,
      "scrapes_id": 142
    },
    "linkedin": {
      "url": "https://www.linkedin.com/company/pedicel-marketing",
      "fetch_backend": "cloak_loggedin | firecrawl | manual_summary",
      "char_count": 8200,
      "scrapes_id": 143,
      "post_count_30d": 18,
      "top_posts": [{"date": "2026-07-12", "engagement": 312, "url": "..."}]
    },
    "instagram": {
      "url": "https://www.instagram.com/pedicelmarketing",
      "fetch_backend": "firecrawl | manual_summary",
      "char_count": 4400,
      "post_count_30d": 12,
      "grid_themes": ["team photos at conferences", "client work snapshots", "tactical marketing tips"],
      "scrapes_id": 144
    },
    "reference": {
      "url": "https://linear.app",
      "fetch_backend": "firecrawl",
      "char_count": 21000,
      "scrapes_id": 145
    }
  },
  "voice_and_tone": {
    "register": "conversational-professional",
    "sentence_case": true,
    "favorite_words": ["without", "behind", "real", "specific"],
    "banned_words": ["synergy", "delve", "leverage", "in today's"],
    "formality_score_1to5": 3,
    "avg_sentence_length_words": 14,
    "example_lines": [
      "We build content engines that compound.",
      "Most agencies optimize for impressions. We optimize for pipeline."
    ],
    "notes": "Voice is confident, peer-to-peer (no marketing fluff), explicitly anti-jargon."
  },
  "palette_from_logo": {
    "method": "color-thief on primary logo + brand mood words",
    "primary": "#1F4D3F",
    "secondary": "#F5F1E8",
    "accent": "#E8B14F",
    "neutrals": ["#1A1A1A", "#5C5C5C", "#A8A8A8", "#E5E5E5", "#FAFAFA"],
    "rationale": "Logo's deep evergreen + warm cream backdrop came from the founder's preference; the gold accent is reserved for CTA hover."
  },
  "typography_recommendation": {
    "display_family": "GT Walsheim",
    "body_family": "Inter",
    "mono_family": "JetBrains Mono",
    "license_notes": "GT Walsheim is paid (Grilli Type) — DO NOT vendored; substitute Fraunces or Söhne (MIT-ish) for production. Inter is SIL OFL.",
    "scale_ratio": 1.250,
    "scale_steps": [12, 14, 16, 20, 24, 32, 48, 64]
  },
  "real_photo_inventory": [
    {
      "url": "https://pedicelmarketing.com/wp-content/uploads/team/kristin-headshot-2026.jpg",
      "subject": "Kristin, founder, headshot",
      "license": "brand-owned",
      "use": ["about page", "speaker bio"],
      "scrapes_id": 146
    },
    {
      "url": "https://pedicelmarketing.com/wp-content/uploads/work/acme-case-study-cover.jpg",
      "subject": "Case study hero for Acme client",
      "license": "client-owned, brand-permission-to-display",
      "use": ["case study hero", "homepage carousel"],
      "scrapes_id": 147
    }
  ],
  "service_facts": [
    {"name": "Content Engine", "description": "End-to-end SEO program: strategy, writing, distribution, measurement.", "price_range": "$8k–$15k/mo"},
    {"name": "Fractional CMO", "description": "Senior marketing leadership, 1 day/week, embedded with your team.", "price_range": "$6k–$12k/mo"},
    {"name": "Brand Sprint", "description": "2-week positioning + messaging engagement.", "price_range": "$15k flat"}
  ],
  "social_highlights": {
    "linkedin": [
      {"date": "2026-07-12", "excerpt": "Most agencies sell impressions. We sell pipeline.", "engagement": 312},
      {"date": "2026-07-05", "excerpt": "A short post on why we don't do A/B tests at the headline level", "engagement": 187}
    ],
    "instagram": [
      {"date": "2026-07-18", "caption": "Team at Content Marketing World 2026", "image_url": "..."},
      {"date": "2026-07-09", "caption": "New client work drop", "image_url": "..."}
    ]
  },
  "testimonials": [
    {
      "quote": "Pedicel made our content engine predictable. We went from 0 to 40 qualified demos/month in 6 months.",
      "attribution": "Sarah Chen, VP Marketing, Acme Co",
      "source_url": "https://www.linkedin.com/in/sarahchen/details/recommendations",
      "license": "public, attributed",
      "scrapes_id": 147
    }
  ],
  "brand_donts": [
    "No purple gradients",
    "No 'revolutionary' or 'cutting-edge'",
    "No stock photography of generic office scenes",
    "No carousel auto-advance on the homepage hero (slows down the message)"
  ],
  "limitations": [
    "Instagram login-walled: public grid scraped via firecrawl, captions recovered for 12/30 most-recent posts only",
    "LinkedIn session was the throwaway-account Cloak session; volume kept low per skill rules"
  ]
}
```

### §2.3 — How site-cloner ingests the brief

The site-cloner agent reads `reports/brand/brand-brief.json` and treats it as **the single
source of truth** for the brand. Specifically:

- **Tokens** — site-cloner uses the brief's `palette_from_logo` and `typography_recommendation`
  *as the starting point* for its own `tokens/color.json` and `tokens/typography.json`,
  overriding anything the reference's tokens suggested.
- **Copy** — site-cloner uses `voice_and_tone.favorite_words` / `banned_words` as the
  writing constraints for every block in the new site. It runs every generated block through
  `humanizer` (entry 6 of `skills-and-repos.md`) before committing.
- **Imagery** — `real_photo_inventory` provides the actual photo URLs. Site-cloner never
  uses stock; if a real photo is unavailable for a section, it picks a different section
  pattern (not a different photo).
- **Services & testimonials** — these become the actual content of the new site's service
  cards and testimonial strip. The reference site may have a testimonial strip too; we use
  *our client's* quotes, not the reference's.
- **Brand donts** — site-cloner enforces these in the design pass (the `frontend-design`
  skill's anti-AI-slop guard-rails, plus the brief-specific donts).
- **Limitations** — site-cloner does *not* override these; if Instagram only yielded 12
  captions, the new site does not pretend to have a 30-post Instagram feed.

### §2.4 — What if research-agent returns partial / blocked?

Honesty rules from `nt-site-mirror` apply here too. If research-agent reports:

- **own_site blocked** (Cloudflare, login wall) → site-cloner proceeds with a `User-Supplied
  Baseline Asset` note and asks the user for a fresh export. Per the nt-site-mirror asset
  classification table, this is a known status, not a fidelity gap.
- **linkedin_blocked** (no logged-in session) → site-cloner uses whatever public-about-page
  text is available and does *not* fabricate posts or quotes. The `social_highlights.linkedin`
  array is empty, and that's documented.
- **instagram_blocked** (full login wall, no scrape possible) → site-cloner does *not* use
  stock imagery. Site-cloner either asks the user for permission-granted photo URLs, or
  designs a section pattern that doesn't require photography (typography-led, illustration-led).
- **reference_blocked** → site-cloner falls back to observation-only reference analysis
  (smaller evidence base, document the gap).

In every case, site-cloner reports the limitation honestly in the validation report — never
a "Pass" with a hidden gap.

---

## Step 3 — Design (10x, brand-authentic)

Owner: **site-cloner agent** with a new `web-designer` skill (see `integration-plan.md`).

Inputs:
- `reports/reference/REPORT.md` (step 1)
- `reports/brand/brand-brief.json` + `brand-brief.md` (step 2)
- The full skill toolkit from `skills-and-repos.md` (shadcn, Motion, Lenis, AOS, axe,
  Lighthouse, color-thief, Style Dictionary, etc.)

Substeps (loosely ordered, many parallel):

1. **Token synthesis.** Build a *single* token system that fuses the brand's real palette
   (from `brand-brief.palette_from_logo`) with the reference's typographic discipline (from
   `reference/REPORT.md`). Persist via Style Dictionary → `tokens/dist/tokens.css` +
   `tailwind.config.ts`. This is the canonical token source for the project.
2. **Component selection.** Map the reference's component inventory (cards, pricing, etc.)
   to shadcn-ui primitives. Where the reference had a bespoke hero, use the shadcn
   `Hero` pattern (custom composition of `Button`, `AspectRatio`, `Typography`).
3. **Section composition.** Order the sections per the reference (step 1.1) but populate
   each with brand-authentic copy (from `brand-brief.voice_and_tone`) and brand imagery
   (from `real_photo_inventory`). This is where the 10x lands: same structure as the
   reference, totally different content.
4. **Motion design.** Apply the motion vocabulary from `reference/motion-inventory.json`,
   but chosen per the brand brief's register. Restrained brands → AOS + Lenis only.
   Cinematic brands → Motion + Lenis. The 1% that needs ScrollTrigger-pinned choreography →
   GSAP. Document the choice.
5. **Signature element.** Per the `frontend-design` skill (entry 1), pick *one* memorable
   element that embodies the brief — e.g. an animated process diagram, a live metrics
   counter, a stylized scroll-bound timeline. This is the 10x over the reference; the
   reference has a default signature, we add a brand-specific one.
6. **Copy pass.** Run every block through `humanizer`. Apply the brand's
   `favorite_words` / `banned_words`. Replace the reference's CTAs with brand-specific,
   action-led CTAs ("Get the case study" not "Learn more").
7. **Iterate with screenshots.** Self-critique per the `frontend-design` skill's "take one
   accessory off" advice — render at 1440×900 and 375×812, remove whatever doesn't serve
   the brief.

---

## Step 4 — Validate

Owner: **site-cloner agent** + the existing `nt-site-mirror` validation toolkit.

Required gates (all must pass before claiming the deliverable; any failure → `Partial` /
`Fidelity Gap` per the skill's tier definitions):

1. **Boot gate** — site serves locally through one documented command (`pnpm dev`,
   `next dev`, or `vite`, depending on stack).
2. **Dependency gate** — no unresolved console errors, no failed local 4xx, every external
   asset classified per the `nt-site-mirror` asset table (paid fonts substituted, no
   provider-streamed media in the deliverable, etc.).
3. **Accessibility gate** — `dequelabs/axe-core` run on every route via
   `@axe-core/playwright`; **0 serious or critical violations**.
4. **Performance gate** — `GoogleChrome/lighthouse` on every route at mobile + desktop;
   **Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95, SEO ≥ 95**.
5. **Site-wide audit** — `harlan-zw/unlighthouse` over all in-scope routes; report the
   comparison table in `validation-report.md`.
6. **Responsive gate** — `viewports.py` at 320, 768, 1024, 1440 on at least 3 routes.
7. **Motion gate** — for any route with motion, capture a short webm and visually verify
   the vocabulary matches the brand brief (restrained brand → no flashy effects, etc.).
8. **Source-paired gate** — where the redesign is being compared *directly* to the
   reference, render both side-by-side and ensure the redesign is *visibly* 10x (or,
   honestly, "measurably better" — exact 10x is a metaphor, not a metric).

The deliverable report (`validation-report.md`) states each gate's verdict with its
evidence basis (`Observed visually` / `Interaction-tested` / `DOM+assets confirmed` /
`HTTP-200 only` / `Not exercised`) per the `nt-site-mirror` honesty rules.

---

## §5 — Concrete example request + response (end-to-end)

### Operator message (Discord `#design` channel, where site-cloner lives)

> Redesign Pedicel Marketing's site. Brand site: https://pedicelmarketing.com. Reference:
> https://linear.app. Use Kristin and Sarah's photos from Dropbox (I'll DM you). Goal: 10x
> better than Linear for our niche (B2B content marketing agency), brand-authentic, no purple
> gradients, no stock photos. Keep the Linear restraint — no over-the-top motion.

### site-cloner → research-agent (structured handoff)

Cross-post to `#research` (the research-agent home channel):

> Research brief — `pedicel-marketing-redesign`. Brand: Pedicel Marketing (own site +
> LinkedIn + Instagram). Reference: linear.app. Need a `brand-brief.json` per the
> contract: voice, palette from logo, typography rec, real photo inventory, service facts,
> LinkedIn/Instagram highlights, testimonials, brand donts. Brand brief from operator:
> "B2B content marketing agency, professional but warm, primary audience = CMO of mid-market
> DTC, motion restrained, existing site is stock-template." Attached Dropbox paths:
> `~/Dropbox/pedicel-brand/`. Save under `project_tag=pedicel-marketing-redesign`.

### research-agent → site-cloner (response, posted back to `#design`)

```markdown
## Brand brief — Pedicel Marketing · `pedicel-marketing-redesign`

Saved: `reports/brand/brand-brief.json` (8.2 KB) + `brand-brief.md` (1 page).
`research_scrapes` rows: 142–147 under `project_tag=pedicel-marketing-redesign`.

### Voice
Conversational-professional. Confident, peer-to-peer, anti-jargon. Banned: synergy, delve,
leverage, "in today's". Loves "without", "behind", "real", "specific". Sentence case.
~14 words/sentence.

### Palette (from logo)
Primary `#1F4D3F` (deep evergreen), backdrop `#F5F1E8` (warm cream), accent `#E8B14F`
(gold — CTA hover only). 5-step neutral ramp.

### Type
Display: GT Walsheim (paid — substitute Fraunces MIT for prod). Body: Inter (SIL OFL).
Mono: JetBrains Mono. Scale 1.250.

### Real photo inventory (5 photos)
Kristin headshot, Sarah headshot, team at Content Marketing World 2026, Acme case study
hero, podcast studio b-roll. All brand-owned or brand-permission-to-display.

### Services (3)
Content Engine ($8–15k/mo), Fractional CMO ($6–12k/mo), Brand Sprint ($15k flat).

### Social highlights
LinkedIn: top 5 posts last 30 days, 312-engagement piece from 7/12 is the lead.
Instagram: 12 captions recovered (18 posts attempted; 6 behind login wall).

### Testimonials (3)
Sarah Chen / Acme, Mike Rivera / Bolt, Priya Shah / Lumen. All LinkedIn-attributed.

### Brand donts
No purple gradients. No "revolutionary"/"cutting-edge". No stock photography. No hero
carousel auto-advance.

### Limitations
- Instagram 6/24 most-recent posts behind login (not scraped)
- LinkedIn via throwaway Cloak session, kept low volume per skill rules
```

### site-cloner → operator (Discord `#design` response)

> Brand brief is in `reports/brand/`. Now understanding the reference (Linear): running
> `capture_assets`, `extract_tokens`, `motion_audit` against linear.app. Will report the
> reference brief in ~5 min, then start the design pass.

*(... ~5 min later, after the reference brief is produced ...)*

> Reference brief is in `reports/reference/`. Key findings: Linear's motion vocabulary is
> restrained (fade-up reveals, single hero CTA, no carousel) — matches the brand's
> "restrained" preference, so we'll use Motion + Lenis without GSAP. Token scale (1.250,
> 8/16/32/64) is close to brand's preferred 1.250 with steps 12/14/16/20/24/32/48/64 — we'll
> use the brand's because it's tighter.
>
> Starting design pass. Estimated ~25 min for scaffold + components, then validation.

*(... validation done ...)*

> Done. New site at `out/pedicel-marketing-redesign/`. Highlights:
> - 11 sections (Linear's 9 + FAQ + team), order preserved
> - All copy passes `humanizer`; banned-words list = 0 occurrences
> - Lighthouse mobile: 96 / 97 / 100 / 100 (Perf / A11y / BP / SEO)
> - axe-core: 0 serious or critical violations across 3 routes
> - Real photos from brand inventory used in 5 places; 0 stock
> - Reference comparison: home page LCP 1.2s vs Linear's 1.8s; bundle 84 KB gz vs Linear's 142 KB
>
> Tradeoffs / accepted exceptions:
> - One testimonial (Priya / Lumen) is sourced from a 2025 podcast transcript, not LinkedIn —
>   attributed as "as told to the Lumen CMO podcast, 2025".
> - LinkedIn "highlight" pull-quote is from 7/12; we did not pull 7/19 or 7/26 because the
>   Cloak session was rate-limited — single highlight by operator decision.
>
> Run `pnpm dev` to preview locally. Full validation report at `reports/validation-report.md`.

This is the contract. Every claim above is sourced from a real artifact on disk; nothing is
fabricated. If a Lighthouse score is 96, it is 96, not "around 95".

---

## §6 — Why this workflow beats both naive variants

- **Naive variant A:** "Just have the LLM look at the reference and write the new site."
  No brand brief → copy is generic. No token discipline → site looks stock. No motion
  vocabulary → site feels static. No quality gates → axe violations ship to production.
- **Naive variant B:** "Use a no-code tool (Framer, Webflow) to redesign." No
  reproducibility, no Lighthouse 90+, no token system, no observability, no version control,
  no automated validation.

This workflow is *deterministic where it matters* (tokens, components, validation) and
*creative where it matters* (composition, copy, signature element). It costs more setup than
naive A and less money than naive B, and it produces a result that survives scrutiny.