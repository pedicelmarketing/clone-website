# Understanding a reference site before redesigning

**Date:** 2026-07-24 · **Author:** site-cloner-agent · **Branch:** feat/web-designer
**Status:** Research-only methodology. No code is changed by this document; the integration
plan lives in `integration-plan.md`.

**Why this matters.** Phase 1 of the pipeline produces a faithful baseline of a single URL —
that already covers ~50% of the reference-understanding work. To produce a *10x* redesign that
inherits the structural craft without copying the proprietary code, we need a structured pass
over the reference that extracts **tokens** (design decisions, the small set), **inventory**
(components and copy, the long list), and **motion** (the part screenshots can't see). This
document maps each technique to a concrete tool or method and shows where it plugs into the
existing `nt-site-mirror` skill.

The general principle: **observation is the floor, structure is the goal.** Every technique
below produces either a structured artifact (JSON, CSS variables, a motion verdict) or an
inventory (a list of components, a list of breakpoints). What we never produce is the
reference's *code* — that is the difference between a redesign and a copy.

---

## 1. Section / DOM segmentation — "what sections does this site actually have?"

**Technique.** Walk the DOM in source order, group nodes into named sections by visual + semantic
clues (top-level `<section>`, `<header>`, `<footer>`; landmark roles; headings; data-attributes;
Astro/Next `data-section` patterns; `id`/`aria-labelledby`). Output a section list with the
elements it owns, the in-viewport order, and any background color/image per section.

**Tool / method.**
- Primary: `skills/nt-site-mirror/scripts/capture_assets.py <url> -o <graph.json>` already
  produces a schema-1.3 runtime asset graph. The graph's `metadata_states` and node layout
  reveal section boundaries (hero vs. mid vs. footer commonly have distinct background-image
  / font stacks).
- Augment with a single Playwright evaluation inside the captured session:
  ```js
  Array.from(document.querySelectorAll('main > *, body > section, body > header, body > footer'))
    .map(el => ({tag: el.tagName, id: el.id, role: el.getAttribute('role'),
                 bg: getComputedStyle(el).backgroundColor,
                 rect: el.getBoundingClientRect().toJSON()}))
  ```
  Save to `reports/reference/sections.json`.
- For SPAs that lazy-render, scroll the page with the same script `motion_audit.py` uses (10
  smooth-scroll steps, `per_step_ms ≈ seconds * 1000 / 10`) and re-collect sections at each
  step to catch reveal-only blocks.

**Output.** `reports/reference/sections.json` — ordered list of `{index, tag, id, role,
bg, height, child_count, headings[]}`.

**What it unlocks for the redesign.** A reference site typically has 6–12 sections (hero,
social proof, features, pricing, testimonials, CTA, footer, sometimes case studies, team,
FAQ). Knowing the *list* means the redesign doesn't accidentally drop one ("the reference has a
press logos strip on the homepage — does the new site need one?"). The *count* and *ordering*
is the structural skeleton we copy; the visual treatment is what we differentiate.

---

## 2. Design-token extraction — color, type scale, spacing, radius, shadow

**Technique.** Read the design tokens the reference *actually uses*, not what its spec says.
Three sources in priority order:
1. CSS custom properties at `:root` (or any `:where(html, body)` rule).
2. Tailwind config if present (look for the CDN bundle `https://cdn.tailwindcss.com` and `tailwind.config = {...}`).
3. Computed styles on representative elements (use `getComputedStyle` to recover the *applied*
   values when variables are unavailable).

**Per token class — the concrete extraction recipe:**

### 2a. Color
- Collect all `--*` custom properties at `:root`. Group by hue/value (`--color-primary-*`,
  `--color-gray-100`, etc.).
- Compute a frequency map: which `--color-*` properties are referenced by the largest number
  of elements? Those are the *primary* tokens.
- Run `lokesh/color-thief` (entry 12 in `skills-and-repos.md`) on the hero image / logo to
  *cross-check* that the token palette is internally consistent with the brand imagery. If
  the logo's dominant color isn't in the top-3 tokens, the reference site is broken here.
- Output: `tokens/color.json` with `{primary, secondary, accent, neutrals[]}` arrays.

### 2b. Type scale
- Extract `font-family`, `font-size`, `font-weight`, `line-height`, `letter-spacing` from:
  - `<h1>`, `<h2>`, `<h3>`, `<h4>`, `<p>`, `<small>` (or one representative of each).
  - Any `display-*` class.
- Compute ratios: `h1 / p` is the type scale ratio. Reference sites commonly land on the
  *modular scale* — 1.250 (major third), 1.333 (perfect fourth), 1.414 (augmented fourth),
  1.5 (perfect fifth), 1.618 (golden).
- Capture the font *stack*, not just the name — `Inter, system-ui, sans-serif` tells us the
  fallback chain the designer wanted.
- **Asset-hygiene:** Google Fonts and Adobe Fonts are widely licensed for use but *not* for
  redistribution in a deliverable. Record which fonts are loaded from where; we re-license or
  substitute in phase 2.
- Output: `tokens/typography.json` with `{family_display, family_body, family_mono,
  scale_ratio, sizes: [{step, px, rem, role}]}`.

### 2c. Spacing
- Extract `padding`, `margin`, and especially `gap` from a sample of section/grid containers.
- Compute the *base unit* — common values: 4, 6, 8, 10, 12 px. Detect by GCD of the observed
  values.
- Output: `tokens/spacing.json` with `{base_unit_px, scale: [n1, n2, n3, …]}`.

### 2d. Radius
- Extract `border-radius` from buttons, cards, inputs, images. Common scales: 0 (sharp /
  broadsheet), 4, 6, 8, 12, 16, 9999 (pill).
- Output: `tokens/radius.json` with `{scale: [0, 4, 8, 12, 16, 9999], defaults_by_role: {…}}`.

### 2e. Shadow
- Extract `box-shadow` from cards, popovers, modals, sticky headers. Record elevation levels.
- Output: `tokens/shadow.json` with `{elevations: [{level, value, used_by}]}`.

**Tool / method.** All of the above is one Playwright evaluation per token class, plus
`color-thief` for the cross-check. Persist to `tokens/*.json`. Then pipe each through
`style-dictionary/style-dictionary` (entry 17 in `skills-and-repos.md`) to emit CSS variables
*and* a Tailwind config — so the redesign project's `tailwind.config.ts` already extends with
the reference's scale, ready to be themed with the brand's real palette.

**What it unlocks for the redesign.** Token systems are the single most-leverage 10x move.
When the redesign project has `text-3xl` → `2.25rem`, `rounded-xl` → `0.875rem`,
`bg-primary-600` → `#1A2B3C`, every section can use the same vocabulary and *look like one
designed it*. Without tokens, every section reinvents the card padding.

---

## 3. Content / copy inventory

**Technique.** Capture every text block on the page — headings, body, button labels, microcopy
(error messages, empty states), footer legal — and tag it with its role.

**Tool / method.** Playwright pass:
```js
Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, button, a, label, small, span'))
  .map(el => el.textContent.trim())
  .filter(Boolean)
```
- Also capture `alt=""` and `aria-label=""` for image / icon-only elements.
- Bucket by an XPath pattern: top-level section children get `s1.p1`, `s1.h2`, etc. — survives
  edits during the redesign phase.

**Output.** `reports/reference/copy.json` — `[{section, role, text, source_url}]`.

**What it unlocks for the redesign.** A reference site has *voice*; an LLM-generated redesign
without voice reads like a brochure. The copy inventory lets us:
- Run `humanizer` (entry 6) on every block — strip AI-isms, sharpen verbs.
- Detect the *register* (formal, conversational, playful, terse) and match it.
- Spot copy the reference got *wrong* (vague CTAs like "Learn more" when "Get the case study"
  would convert better) — the 10x is the *better copy*, not the same copy with new colors.

---

## 4. Component inventory

**Technique.** Detect reusable components by structural and stylistic similarity — the same
"card" repeated 6 times is a component; six different cards are not. Inventory every component
instance with its variant.

**Tool / method.**
- Primary: DOM-level detection. Group elements by `(tag, role, classes-prefix, child-structure)`.
  Threshold: ≥ 3 near-duplicates across the page = a component.
- Augment: heuristic detection by class prefix. `Card_*`, `Button_*`, `c-card-*` all signal
  component classes. Build a frequency table of class-prefix clusters.
- For SPAs (React/Vue/Svelte), peek at the bundle's component names if the source map is
  available — *only* to validate the inventory, never to copy source code (per the
  `nt-site-mirror` asset-hygiene rules).
- Visual inventory: render the page at 1440×900, scroll-screenshot every viewport, manually
  mark each unique component.

**Output.** `reports/reference/components.json` — `[{name, instances: [{section, variant}],
average_height_px, has_hover_state, has_animation}]`.

**What it unlocks for the redesign.** The reference site has ~10–20 unique components. We
match them with `shadcn-ui/ui` primitives (entry 7) — Dialog → shadcn `<Dialog>`, Pricing card →
shadcn `<Card>` + custom layout, etc. The 10x is replacing each bespoke component with the
accessible, theme-able shadcn equivalent, then *visually differentiating* through tokens
(palette, type, radius) rather than re-coding the components.

---

## 5. Responsive-breakpoint inference

**Technique.** Identify the breakpoint values the reference *actually* uses by detecting
where layout shifts happen.

**Tool / method.**
- Open Playwright at widths 320, 360, 414, 480, 640, 768, 900, 1024, 1200, 1440, 1920.
- At each width, capture `getBoundingClientRect()` on the main grid / flex containers and any
  element with `display: none`.
- A breakpoint exists where (a) container widths change non-linearly, or (b) an element goes
  from `display: none` to `display: block` (or vice versa).
- Cross-check: the breakpoints are usually exact multiples of the base unit
  (`tokens/spacing.json.base_unit_px * N`).

**Output.** `reports/reference/breakpoints.json` — `[{min_width_px, label,
changes: [{element, before, after}]}]`.

**What it unlocks for the redesign.** Knowing whether the reference is `mobile-first` (default
rules, `@media (min-width:)` overrides) or `desktop-first` (`max-width:` overrides) tells us
how to write the new CSS — and surfaces non-obvious things like a hidden-from-mobile CTA
banner that exists only at large widths. We do not copy the *values*; we copy the *strategy*.

---

## 6. Motion analysis — the part screenshots cannot see

**This is the single most important technique in the document.** A site can look static in a
screenshot and feel completely different in a browser — entrance animations, scroll-linked
parallax, hover micro-interactions, carousel auto-advance, background video loops. The
`nt-site-mirror` skill already has the tool for this:

### 6a. The existing tool — `skills/nt-site-mirror/scripts/motion_audit.py`

- **Reads two URLs** (`--source-url <ref>`, `--local-url <mirror>`) and **records a scripted
  scroll pass over each** as a webm video using Playwright's built-in `record_video_dir`. Same
  10-step smooth-scroll script for both, so the videos are directly comparable.
- **Uploads both videos to Gemini** (model defaults to `gemini-2.0-flash`, overridable) using
  `google-generativeai`. Gemini has *native video vision* — frame-only image vision (LLaVA,
  GPT-4V) cannot see motion; Gemini can reason about temporal change.
- **Prompts Gemini** to compare and report under five headings: entrance/load animations,
  scroll choreography, continuous motion, missing/broken motion in the mirror, verdict
  (`Motion faithful` | `Partial motion` | `Motion lost`).
- **Outputs** `reports/motion/animation-audit-gemini.md` with the verdict folded in.

### 6b. How to plug it into the redesign workflow

In *phase 1* (today, faithful baseline), `motion_audit.py` is used to validate that the mirror
preserves the source's motion. In *phase 2* (redesign), we repurpose it differently:

- **Capture the reference's motion** as a reference video: `motion_audit.py --source-url <ref>
  --local-url <same ref> --record-only --out reports/reference/motion`. This gives us a single
  webm file of how the reference *actually moves*.
- **Manually annotate** (or have Gemini describe) the motion *vocabulary*: which elements
  fade-in, which slide, which parallax, what easing, what duration. Persist as
  `reports/reference/motion-inventory.json` with `{selector, trigger, transform, duration_ms,
  easing, delay_ms, notes}`.
- **Map vocabulary → libraries** (entry 13–16 from `skills-and-repos.md`):
  - Fade-up reveals on scroll → `michalsnik/aos` (low-friction, 50 sites use this pattern).
  - Orchestrated timeline (header → hero → body → CTA) → `motiondivision/motion` with
    `useScroll` + `useTransform`.
  - Pinned sections with sequenced reveals → `greensock/GSAP` ScrollTrigger (this is the
    one case where GSAP is justified).
  - Smooth-scroll baseline → `darkroomengineering/lenis`.
- **For the redesigned site**, **don't run `motion_audit.py` against the reference again** —
  the audit is for mirror fidelity, not design comparison. Instead, render the redesigned site
  and *visually compare* (or screen-record side-by-side) to confirm the new motion vocabulary
  matches the brand spec (restrained? playful? cinematic?) rather than the reference's.

### 6c. When to skip motion analysis

- The reference is a fully-static page (no transitions, no scroll reveals, no carousels). The
  `motion_audit.py --record-only` capture will still produce a video, but the Gemini verdict
  will be `Motion faithful` trivially. Skip the analysis in this case.
- The reference uses heavy WebGL/canvas (Three.js, R3F, shader scenes) — motion analysis
  applies but the *asset* (the 3D model, the shader) is what to inspect, not just the
  choreography. See `skills/nt-site-mirror/modules/webgl.md`.
- The brand brief explicitly says "static, content-driven" (e.g. a long-form essay site). In
  this case the *10x move is restraint* — no motion at all.

**What it unlocks for the redesign.** Motion is where most "looks like a tutorial site"
deliverables fail. A reference site's motion vocabulary is its *signature* (Stripe's
document-style reveals, Linear's choreographed page-load, Vercel's snappy hover states). We
*describe* that vocabulary and *reimplement* it on the new site using Motion + Lenis by
default, GSAP for the cinematic cases. Skipping this step is how you ship a redesign that
*looks* like the reference but *feels* like a wireframe.

---

## 7. The combined artifact — `reports/reference/REPORT.md`

Once all six passes above have run, concatenate the structured outputs into a single
human-readable brief:

```markdown
# Reference site brief — <ref>

## Structural skeleton
- 9 sections, in order: hero, social-proof, feature-grid, testimonial, pricing, faq, cta, footer.
- Mobile-first (default rules, 4 min-width breakpoints: 640, 768, 1024, 1280).

## Token system
- Palette: 11 colors, primary #1A2B3C, accent #F4A261.
- Type: display "Söhne Breit", body "Inter", 1.250 modular scale (major third).
- Spacing base 8 px, scale [4, 8, 12, 16, 24, 32, 48, 64, 96].
- Radius scale [0, 4, 8, 12, 9999]; cards = 12, buttons = 8, pills = 9999.
- Shadow elevations: 0/1/2 (subtle / card / popover).

## Components
- Card (8 instances), PricingCard (3), Testimonial (5), FAQ accordion (1), Hero with media (1).
- All Cards share a 12-radius, shadow-1, hover-state-shadow-2 pattern.

## Copy voice
- Conversational, sentence case, action-led CTAs ("Get the case study", not "Learn more").
- 8 AI-isms to strip on rewrite: "delve into", "in today's", "tapestry of", …

## Motion vocabulary
- Page load: header fades in 200 ms ease-out, hero text slides up 600 ms cubic-bezier,
  hero image parallax 1.2× scroll speed.
- Scroll reveals: most sections fade-up at 0.8 viewport, 600 ms.
- No carousel; no auto-advance; no background video.
- Recommended stack: Motion + Lenis + AOS (no GSAP needed — vocabulary is restrained).
```

This is what the design phase consumes. The reference's *visual* identity is discarded; its
*structure, voice, and motion vocabulary* are the inputs.

---

## Mapping back to `nt-site-mirror`

| Reference technique | Tool in the existing skill | Status |
|---------------------|----------------------------|--------|
| Section / DOM segmentation | `capture_assets.py` graph + small Playwright evaluation | **already partly there** — extend with section-segmentation pass |
| Design-token extraction | not yet — write a new `scripts/extract_tokens.py` | **add in integration phase** |
| Copy inventory | not yet — write a small Playwright eval script | **add in integration phase** |
| Component inventory | partly via `capture_assets.py`'s asset graph (images, fonts); not for layout components | **add a layout-component inventory pass** |
| Responsive-breakpoint inference | not yet — write a `scripts/infer_breakpoints.py` | **add in integration phase** |
| Motion analysis | `motion_audit.py` already exists | **reuse as-is** |

The skill needs three new scripts and one enriched graph section. See
`integration-plan.md` § "Phased milestones" for the sequencing.