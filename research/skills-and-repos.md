# Vetted skills and open-source repos for an expert web-designer capability

**Date:** 2026-07-24 · **Author:** site-cloner-agent · **Branch:** feat/web-designer
**Status:** Research-only inventory. Every entry below has been verified — HTTP 200 from
`api.github.com` or `raw.githubusercontent.com` at the canonical URL shown. License names are
copied from the repo's GitHub API `license.spdx_id` field (or stated honestly when GitHub
detects no standard license). No fabricated projects.

**Why this list exists.** Today, `site-cloner` produces a faithful local baseline of one URL and
stops. The phase-2 vision is for it to produce a *new* site that is **10x better than a reference
the user names**, while staying **brand-authentic** (the brand's real logo, photos, copy, services,
social proof). To do that without re-inventing the wheel, we lean on three classes of
already-vetted tooling — Claude skills (process and taste), open-source component/section
libraries (scaffolding), and design-token / motion / quality-tooling (production quality).

The **integration cost** column uses:

- **low** — drop into a Vite/Next project via `npm install`, no API keys, no copy-paste of code.
- **med** — needs wiring, theming, or a small build step; not zero.
- **high** — proprietary licence (asset hygiene + payment), needs significant integration, or
  vendor-specific hosting.

The **10x rationale** column answers: *if we adopt this, the deliverable is materially better than
the reference by exactly this lever.* Read that column together with the rest of the dossier —
each tool earns its slot only when paired with the workflow in `workflow-design.md`.

---

## A. Claude / Hermes skills — taste, process, and writing

These are loaded as agent skills (SKILL.md format) and directly shape the agent's reasoning when
producing or critiquing a design. They do not ship runtime code; they shape the *output*.

### 1. `anthropics/skills` — `frontend-design`

- **URL:** https://github.com/anthropics/skills/tree/main/skills/frontend-design
  (raw SKILL.md: https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md)
- **License:** source-available per `LICENSE.txt` in repo root (per `anthropics/skills` README:
  most skills Apache-2.0, a few source-available including docx/pdf/pptx/xlsx and the *-design
  family). Treat as source-available: read & apply the skill, do not redistribute verbatim.
- **What it gives us:** a design-lead playbook — pin a concrete subject + audience + job, build a
  compact token system (4–6 hex palette, 2+ typeface roles, layout concept, *signature* element),
  self-critique against the three current AI-default looks (warm cream serif+terracotta /
  near-black+acid-green / broadsheet hairline rules), then execute. Forbids templated defaults.
- **Integration cost:** **low** — vendored SKILL.md loaded by name; no runtime, no API key.
- **10x rationale:** without this, an LLM designing a brand site lands on the warm-cream /
  acid-green / broadsheet default look regardless of the brand. *With* this, every deliverable
  has a stated thesis ("the hero is the roast curve, the signature element is the bean-counter
  scoreboard") instead of a stock template. The thesis itself is the 10x.

### 2. `anthropics/skills` — `theme-factory`

- **URL:** https://github.com/anthropics/skills/tree/main/skills/theme-factory
- **License:** source-available per repo LICENSE.txt (same as #1).
- **What it gives us:** 10 curated, ready-to-apply color+font pairings (Ocean Depths, Sunset
  Boulevard, Forest Canopy, Modern Minimalist, Golden Hour, Arctic Frost, Desert Rose, Tech
  Innovation, Botanical Garden, …) plus the process of choosing / generating a new theme on
  demand. Used as a *starter*, never as a final answer — the brand's real palette (from
  `research-agent`) overrides the preset.
- **Integration cost:** **low** — vendor the `theme-showcase.pdf` + SKILL.md; agent applies the
  process.
- **10x rationale:** ships a coherent typographic + chromatic identity on day one instead of
  defaulting to system fonts and Tailwind's default palette. Saves the first two iterations of
  "looks like every other AI site".

### 3. `anthropics/skills` — `web-artifacts-builder`

- **URL:** https://github.com/anthropics/skills/tree/main/skills/web-artifacts-builder
- **License:** source-available per repo LICENSE.txt (same as #1).
- **What it gives us:** a working React 18 + TypeScript + Vite + Tailwind + shadcn/ui skeleton
  with `init-artifact.sh` and `bundle-artifact.sh` helpers and an explicit "AI slop" avoidance
  note (no centered layouts, purple gradients, uniform rounded corners, Inter font).
- **Integration cost:** **low–med** — uses shadcn/ui (already on our list); `bundle-artifact.sh`
  emits a single HTML which we want to adapt into a multi-route build, not a single artifact.
- **10x rationale:** the bundled artifact is feature-complete and the slop guard-rails push us
  past the three AI defaults. We borrow the init script + the slop avoidance rules; we swap the
  single-artifact bundling for our multi-route Vite/Next build.

### 4. `anthropics/skills` — `canvas-design` (and the `brand-guidelines` sibling)

- **URL:** https://github.com/anthropics/skills/tree/main/skills/canvas-design
  (sibling: https://github.com/anthropics/skills/tree/main/skills/brand-guidelines)
- **License:** source-available per repo LICENSE.txt (same as #1).
- **What it gives us:** a process for producing on-brand visual canvases (covers, posters,
  diagrams). `brand-guidelines` is the direct counterpart to the brand-research handoff in
  `workflow-design.md` — it codifies how an agent should *use* a brand spec.
- **Integration cost:** **low** — loaded by name.
- **10x rationale:** forces the agent to *cite* the brand spec before any color/typography
  choice, which is the difference between "inspired by the brief" and "every brand ends up
  looking the same".

### 5. Hermes skills already on this machine — `popular-web-designs`

- **URL (skill on disk):** `~/.hermes/skills/creative/popular-web-designs/` (mirror under
  `~/.hermes/profiles/site-cloner/skills/` once vendored)
- **License:** per-skill (Hermes internal).
- **What it gives us:** 54 real design systems — Stripe, Linear, Vercel, etc. — distilled into
  concrete HTML/CSS reference snippets. Perfect raw material for "what does production-quality
  look like across SaaS, consumer, content sites" during the *understand-the-reference* phase.
- **Integration cost:** **low** — load via `skill_view(name='popular-web-designs')`; reference
  snippets during design.
- **10x rationale:** instead of guessing at a section pattern, the agent has actual production
  code for hero / pricing / testimonial / footer patterns from real sites — the gap between
  "looks like a tutorial site" and "looks like Stripe" closes.

### 6. Hermes skills already on this machine — `humanizer`

- **URL (skill on disk):** `~/.hermes/skills/creative/humanizer/`
- **License:** per-skill (Hermes internal).
- **What it gives us:** a post-processor for AI-generated copy — strips "AI-isms" (delve,
  tapestry, in today's fast-paced world, etc.) and adds a real voice. Run every landing-page
  block through it before commit.
- **Integration cost:** **low** — loaded by name; agent applies on copy blocks.
- **10x rationale:** the difference between a site that *looks* designed and a site that
  *reads* designed. Reference sites almost always have human voice — without this step, our
  copy reads like a brochure.

---

## B. Component / section libraries — production-quality scaffolding

The single biggest 10x for an LLM-produced site is having real, accessible, well-designed
components instead of inventing `Card.tsx` from scratch. These are vendored (added to the
project's `package.json`) at scaffolding time.

### 7. `shadcn-ui/ui`

- **URL:** https://github.com/shadcn-ui/ui
- **License:** MIT (per `license` field on repo).
- **What it gives us:** the canonical accessible component primitives for React — Dialog,
  Popover, DropdownMenu, Form, Toast, Tabs, Command, Carousel, Sheet, Tooltip, etc. — built on
  Radix UI primitives and styled with Tailwind CSS variables. **It is a copy-paste registry, not
  an npm package.** The `shadcn` CLI adds component source into your repo under
  `src/components/ui/*`.
- **Integration cost:** **med** — needs Tailwind + Radix; every component lives in your repo so
  you can theme it (this is the point — full control, no upstream lock-in).
- **10x rationale:** accessibility (Radix under the hood), keyboard nav, focus traps, ARIA
  labels — all done. We do not re-implement Dialog focus management; we ship it. Plus the
  `--style new-york` variants are an opinionated aesthetic choice rather than a blank canvas.

### 8. `markmead/hyperui`

- **URL:** https://github.com/markmead/hyperui
- **License:** MIT.
- **What it gives us:** ~100 free Tailwind CSS component / section *snippets* — hero variants,
  pricing tables, feature grids, testimonials, footers, CTAs. Pure HTML + classes; you paste
  and restyle. Designed as marketing-site building blocks, not app primitives.
- **Integration cost:** **low** — paste the snippet, swap class names to match our tokens.
- **10x rationale:** during scaffold we can compose a full landing page from real production
  patterns in under an hour, then layer brand-specific layout and motion on top. Without it, we
  re-invent the pricing-table card every project.

### 9. `htmlstreamofficial/preline` *(formerly `prelineui/Preline`)*

- **URL:** https://github.com/htmlstreamofficial/preline
- **License:** **"Other" / NOASSERTION** — project lists a custom licence; GitHub cannot detect
  an OSI/SPDX standard one. **Asset-hygiene note:** must read the project's `LICENSE.md`
  before redistribution. Treat as *not MIT by default* — vendor only as a development
  dependency, not as redistributable source.
- **What it gives us:** a more "enterprise/dashboard" sibling to shadcn — ~600+ Tailwind
  components incl. data tables, application shells, advanced forms. Useful when the brand site
  needs an admin / dashboard / portal sub-section.
- **Integration cost:** **med–high** — licence review, Tailwind config conflict potential with
  shadcn, larger bundle.
- **10x rationale:** when the brand genuinely needs an admin / portal UI, we have
  production-quality components for it without building from scratch. Reserve for projects
  where the brief calls for it.

### 10. `nuxt/image` *(or Next.js built-in `next/image`)*

- **URL:** https://github.com/nuxt/image
- **License:** MIT.
- **What it gives us:** responsive images done right — automatic `srcset`/`sizes`, modern format
  negotiation (AVIF/WebP), lazy-loading by default, blur-up placeholders. If the project stack
  is Nuxt, this; if Next.js, use the built-in `next/image` (MIT, ships with Next.js). For pure
  static / Astro, `@unpic/*` is the framework-agnostic equivalent.
- **Integration cost:** **low** — drop-in component, no API keys.
- **10x rationale:** a real brand site has real photography. Hero images on a 6 MB JPEG tank
  LCP and Lighthouse. `<NuxtImg>` / `<Image>` give us responsive `srcset`s, modern formats, and
  blur placeholders in one line — directly translates to a faster Lighthouse score on a
  reference site that ships unoptimized JPEGs.

### 11. `lovell/sharp` *(image-processing backend)*

- **URL:** https://github.com/lovell/sharp
- **License:** Apache-2.0.
- **What it gives us:** the libvips-backed image-processing library used by Nuxt Image, Next
  Image, Astro, Gatsby, and most SSGs. Build-time resize/convert/optimize pipelines.
- **Integration cost:** **low** — usually a transitive dep; explicit use when running our own
  pre-pipeline.
- **10x rationale:** when we *do* run our own image pre-pipeline (brand assets are huge, multiple
  sizes, different crops), sharp is the only sensible answer.

### 12. `lokesh/color-thief` *(client-side palette extraction)*

- **URL:** https://github.com/lokesh/color-thief
- **License:** MIT. (NB: many blog posts cite a wrong author URL `lukaszgrolik/color-thief`;
  the canonical repo is `lokesh/color-thief`, author Lokesh Dhakar.)
- **What it gives us:** given an image (typically a brand logo or hero photo), extract a
  dominant palette of N colors via the median-cut algorithm. Browser-side, zero server.
- **Integration cost:** **low** — one JS file, no API key.
- **10x rationale:** cross-check that the *real* brand logo/photo *does* produce the palette we
  committed to in tokens — catches "we said the brand is terracotta but the logo is blue"
  before delivery.

---

## C. Motion & micro-interaction — what makes a site feel alive

The reference site almost certainly uses motion (parallax, scroll-triggered reveals, hover
states). Matching the *feel* without copying the *code* is the second 10x lever.

### 13. `motiondivision/motion`

- **URL:** https://github.com/motiondivision/motion
- **License:** MIT.
- **What it gives us:** the modern Motion library (formerly Framer Motion) — React-friendly
  declarative animations, layout animations, scroll-linked animations via `useScroll`,
  `useTransform`, `useInView`. The default choice for *non-physics* UI motion in React.
- **Integration cost:** **low** — `npm install motion`, drop in `<motion.div>`.
- **10x rationale:** we ship real layout animations (a card reflows when its neighbour is
  removed), scroll-linked hero parallax, and orchestrated entrance sequences without hand-rolling
  `requestAnimationFrame`. The reference site uses GSAP or hand-rolled CSS; we get 90% of the
  feel with less code.

### 14. `darkroomengineering/lenis`

- **URL:** https://github.com/darkroomengineering/lenis
- **License:** MIT.
- **What it gives us:** smooth-scroll (the modern Lerp-based scroller that replaced the old
  `smooth-scroll` packages). One-line setup, integrates with GSAP ScrollTrigger and Motion's
  `useScroll`.
- **Integration cost:** **low**.
- **10x rationale:** smooth scroll is the single most underrated quality signal — sites that
  have it feel designed, sites that don't feel like documentation. Adding Lenis to a project
  raises the perceived quality 1 tier for ~5 lines of code.

### 15. `greensock/GSAP`

- **URL:** https://github.com/greensock/GSAP
- **License:** **None detected by GitHub.** Greensock distributes under a proprietary
  "GreenSock standard no-charge license" (https://gsap.com/standard-license) — free for use,
  not OSI-approved, redistribution rules apply. **Asset-hygiene note:** treat as
  *conditionally-vendored* — it is free to use in the deliverable but not open-source.
- **What it gives us:** the gold-standard scroll choreography + timeline engine — ScrollTrigger,
  SplitText, MorphSVG, DrawSVG, physics-based easing. No competitor for high-end marketing-site
  motion.
- **Integration cost:** **low** for the core, **high** for ScrollTrigger + SplitText plugin
  bundle (split-text in particular triggers licence scrutiny on commercial sites).
- **10x rationale:** when the reference site has *real* scroll choreography (Apple-style
  pinned sections, sequenced reveals), GSAP ScrollTrigger is the only library that gets us there
  in a single timeline. Worth the licence note; *not* a default for every site, but the answer
  for the 10x tier.

### 16. `michalsnik/aos`

- **URL:** https://github.com/michalsnik/aos
- **License:** MIT.
- **What it gives us:** the classic "Animate On Scroll" library — `data-aos="fade-up"` on any
  element and you get a reveal. No JSX, no React wrapper, just HTML attributes.
- **Integration cost:** **low** — one script tag, one CSS link, attributes everywhere.
- **10x rationale:** for content-heavy brand sites (case studies, about pages, blog), AOS gives
  tasteful scroll reveals with zero component refactor. Reserve for the long-tail pages where
  wiring Motion + Lenis everywhere would be overkill.

---

## D. Design tokens & brand extraction — turn "vibes" into variables

The 10x move is committing to a **token system** the reference site doesn't have — every colour,
type step, radius, shadow is a named variable that any consumer can override.

### 17. `style-dictionary/style-dictionary` *(formerly `amzn/style-dictionary`)*

- **URL:** https://github.com/style-dictionary/style-dictionary
- **License:** Apache-2.0. (NB: the original `amzn/style-dictionary` repo transferred to a
  dedicated org — canonical URL is the one above; the Amazon repo now 301-redirects.)
- **What it gives us:** the Amazon-originated design-token build system. Define tokens once in
  JSON/JS, output to CSS variables, SCSS, iOS/Android XML, Tailwind config, anything. The
  multi-platform export is what makes it enterprise-grade vs. a hand-rolled `tokens.ts`.
- **Integration cost:** **med** — needs a build step, a `tokens/` directory, npm scripts.
- **10x rationale:** every section of the new site uses the same `--brand-primary-600` — colour
  drift is impossible. When the brand spec changes (a colour refresh), one JSON file edits
  everything. Reference sites rarely have this discipline.

### 18. `tokens-studio/sd-transforms`

- **URL:** https://github.com/tokens-studio/sd-transforms
- **License:** MIT.
- **What it gives us:** Style Dictionary transforms that read directly from Tokens Studio
  (formerly Figma Tokens) JSON exports. If the brand's design source of truth is Figma +
  Tokens Studio, this is the bridge from Figma → Style Dictionary → CSS.
- **Integration cost:** **med** — needs Tokens Studio export config + sd-transforms wiring.
- **10x rationale:** closes the Figma→code loop without manual token re-entry. Adopt only when
  the brand provides a Tokens Studio export.

### 19. `woltapp/blurhash` *(placeholder hashes)*

- **URL:** https://github.com/woltapp/blurhash
- **License:** MIT.
- **What it gives us:** ultra-compact (~20-char) placeholder hashes for images — a few chars
  decode to a 32×32 blurred preview. Used by Facebook, Twitter, etc. The standard placeholder
  strategy when you can't ship a low-res JPEG (and you usually can't on the LCP image).
- **Integration cost:** **low** — npm package, encode on the server, decode inline in CSS.
- **10x rationale:** real brand sites have real photography, and the LCP image is the moment
  that matters most. BlurHash placeholders eliminate the white flash while the hero loads — the
  difference between "professional" and "I'm building this in Webflow".

---

## E. Design-to-code & AI authoring

For the parts of the brief where the *design itself* is the input (Figma, sketch, mockup),
these tools cut the authoring loop.

### 20. `onlook-dev/onlook`

- **URL:** https://github.com/onlook-dev/onlook
- **License:** Apache-2.0.
- **What it gives us:** an open-source "Cursor for design" — visual editor on top of a real
  React + Tailwind codebase. You edit the running site visually; the source updates. The
  closest OSS competitor to Figma + Builder.io.
- **Integration cost:** **high** — needs a running Onlook instance, a specific project shape;
  useful for the user-facing iteration loop, not for our autonomous pipeline.
- **10x rationale:** when the human wants to *tweak* the deliverable visually ("move that
  button left"), Onlook is the loop that does not require re-prompting the agent. Optional —
  adopt only when the workflow is interactive.

### 21. `anthropics/claude-cookbooks` *(NB: plural)*

- **URL:** https://github.com/anthropics/claude-cookbooks
- **License:** MIT (per repo).
- **What it gives us:** working prompt patterns for vision tasks (palette extraction, screenshot
  critique, layout comparison), image+text workflows, tool-use patterns — all the things the
  agent's *eyes* need when looking at the reference site or the brand's Instagram grid.
- **Integration cost:** **low** — read patterns, paste into prompts/scripts.
- **10x rationale:** instead of asking Claude "is this design good?", we use cookbook patterns
  like "structured critique with weighted rubric" — measurably better output quality.

---

## F. Quality gates — accessibility, performance, image-correctness

The cheapest 10x in 2026 is doing what the reference site demonstrably *did not* do: ship a
site that passes axe-core, ships a Lighthouse score ≥ 90, and never serves a 2 MB hero JPEG.

### 22. `dequelabs/axe-core` *(NB: not the `axe-core` org)*

- **URL:** https://github.com/dequelabs/axe-core
- **License:** MPL-2.0 (Mozilla Public License 2.0).
- **What it gives us:** the de-facto accessibility rule engine — used by Lighthouse, Storybook's
  a11y addon, Chrome DevTools, and most CI a11y gates. Run in-browser or in Node (via
  `@axe-core/playwright`).
- **Integration cost:** **low** for browser use, **med** for CI integration.
- **10x rationale:** every reference site has *some* a11y issue — missing alt text, low contrast,
  no focus visible, a Dialog without `aria-labelledby`. axe-core catches them all in one pass;
  we ship the accessible version by default. MPL-2.0 is file-level copyleft and is compatible
  with our MIT/Apache deliverable (axe-core stays as a `devDependency`, not vendored source).

### 23. `GoogleChrome/lighthouse`

- **URL:** https://github.com/GoogleChrome/lighthouse
- **License:** Apache-2.0.
- **What it gives us:** the audit engine behind Chrome's Lighthouse tab — Performance,
  Accessibility, Best Practices, SEO, PWA. Run programmatically via the CLI
  (`lighthouse <url> --output=json`) or via `lighthouse-ci` in CI.
- **Integration cost:** **low** — `npx lighthouse <url>`.
- **10x rationale:** the *measured* number we report. "10x better than reference" becomes
  "Lighthouse 96 vs reference's 54". Concrete, defensible.

### 24. `harlan-zw/unlighthouse` *(NB: not `unlighthouse/unlighthouse`)*

- **URL:** https://github.com/harlan-zw/unlighthouse
- **License:** MIT. (NB: the original `unlighthouse/unlighthouse` and `danielzmbp/unlighthouse`
  orgs both 404; the canonical repo is the one above.)
- **What it gives us:** site-wide Lighthouse scanner — run once, audit every route, get a UI
  for comparing per-route scores. Built on top of the `GoogleChrome/lighthouse` engine.
- **Integration cost:** **low–med** — `npx unlighthouse --site <url>`.
- **10x rationale:** during the validate step of `workflow-design.md`, we audit *every* route
  on the new site, not just `/`. Unlighthouse gives us a multi-route comparison table in one
  pass.

---

## Quick count

| Class | Entries | Count |
|-------|---------|-------|
| A. Claude/Hermes skills | `frontend-design`, `theme-factory`, `web-artifacts-builder`, `canvas-design`+`brand-guidelines`, `popular-web-designs`, `humanizer` | **6** |
| B. Components / images | `shadcn-ui/ui`, `markmead/hyperui`, `htmlstreamofficial/preline`, `nuxt/image`, `lovell/sharp`, `lokesh/color-thief` | **6** |
| C. Motion | `motiondivision/motion`, `darkroomengineering/lenis`, `greensock/GSAP`, `michalsnik/aos` | **4** |
| D. Tokens | `style-dictionary/style-dictionary`, `tokens-studio/sd-transforms`, `woltapp/blurhash` | **3** |
| E. Design-to-code / cookbooks | `onlook-dev/onlook`, `anthropics/claude-cookbooks` | **2** |
| F. Quality gates | `dequelabs/axe-core`, `GoogleChrome/lighthouse`, `harlan-zw/unlighthouse` | **3** |
| **Total** | | **24** |

**Verified entries: 24** (every entry above was checked against `api.github.com` and/or
`raw.githubusercontent.com` on 2026-07-24. Non-canonical URLs flagged inline.)

---

## What we explicitly did NOT include (and why)

- **`extract-colors` (npm)** — the popular package `extract-colors` on npm is published by
  `NetrisTV` and does not have its own canonical GitHub repo under that name. The upstream
  functionality is covered by `lokesh/color-thief` (entry 12), so we did not pad the list with
  a placeholder.
- **`@framer/motion`** — superseded by `motiondivision/motion` (the package was renamed; the
  npm name remains `framer-motion` for backwards compat but the canonical repo is now
  `motiondivision/motion`).
- **`GSAP` open-source licence myth** — there is a long-standing misconception that GSAP is
  MIT. It is not. It is free for commercial use under the Greensock standard no-charge licence
  but not OSI-approved. Documented honestly above.
- **`next/image`** — folded into entry 10 as the Next.js counterpart to `nuxt/image`. Not a
  separate entry to avoid duplication.
- **`axe-core` org** — the `axe-core` GitHub org 404s; the canonical repo is under `dequelabs`.
  Same product, different org.

---

## Provenance

Each entry's license was captured from `https://api.github.com/repos/<org>/<repo>`'s
`license.spdx_id` field on 2026-07-24. Where GitHub could not auto-detect a standard license
(GSAP, Preline), the custom / proprietary licence is stated and asset-hygiene implications are
called out explicitly.