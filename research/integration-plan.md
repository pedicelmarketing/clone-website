# Integration plan — implementation status

**Date:** 2026-07-24 · **Author:** site-cloner-agent · **Branch:** feat/web-designer
**Status:** **IMPLEMENTED.** M1–M5 are complete on this branch. The original research and
architecture notes below remain useful context; the milestone table in §5 is the authoritative
implementation status.

The research above (the other three files in `research/`) is the input. This file is the
"how do we ship it" answer.

---

## §1 — What we're adding (and what we're not touching)

### Adding

1. A **new skill** at
   `~/.hermes/profiles/site-cloner/skills/web-designer/SKILL.md` (and supporting
   `scripts/`, `references/`, `assets/` subfolders).
2. **Three new helper scripts** under `skills/web-designer/scripts/`:
   `extract_tokens.py`, `inventory_copy.py`, `inventory_components.py`,
   `infer_breakpoints.py`. (Four total — `understand-the-reference.md` §2/3/4/5.)
3. A **new section in `SOUL.md`** that documents the three-input workflow
   (brand + reference + social) and the research-agent handoff.
4. A **new Discord cross-channel rule** so site-cloner knows to post structured briefs to
   `#research` and read `reports/brand/brand-brief.json` back.
5. **Vendored reference material** under `skills/web-designer/references/` — token recipes,
   motion-vocabulary-to-library mapping, brand-brief JSON schema, validation checklist.
6. **Vendored snippets** under `skills/web-designer/assets/` — Style Dictionary config
   skeleton, Tailwind preset, the `frontend-design` skill's anti-slop rules.

### Not touching (kept as-is)

- `skills/nt-site-mirror/` — the existing phase-1 skill. Unchanged. The new web-designer
  skill *uses* it (via its scripts), but does not modify its code.
- `skills/nt-site-mirror/scripts/motion_audit.py` — reused as-is per
  `understand-the-reference.md` §6.
- `bin/`, `cron/`, `memories/`, `plugins/` of the site-cloner profile — left alone.
- The research-agent profile (`~/.hermes/profiles/research-agent/`) — we define the
  *contract* we expect from it; we do not modify its code. Any changes to the research-agent
  profile must come from its own operator.

---

## §2 — Skill structure for `web-designer`

```
skills/web-designer/
├── SKILL.md                              ← trigger + 5-step process + handoff + honesty rules
├── scripts/
│   ├── extract_tokens.py                 ← color/typography/spacing/radius/shadow from a URL
│   ├── inventory_copy.py                 ← every text node, tagged by section + role
│   ├── inventory_components.py           ← component instance map
│   ├── infer_breakpoints.py              ← Playwright sweep across widths
│   └── brand_brief_schema.json           ← the research-agent return contract
├── references/
│   ├── token-extraction-recipes.md       ← the per-class recipes from understand-the-reference §2
│   ├── motion-vocabulary-to-library.md   ← mapping from motion verbs to libraries
│   ├── brand-brief-contract.md           ← the JSON schema + worked example
│   ├── validation-checklist.md           ← the 8 gates from workflow-design §4
│   └── anti-ai-slop.md                   ← vendored from anthropics/skills/frontend-design
├── assets/
│   ├── tailwind-preset.cjs               ← opinionated preset (theme tokens, type scale, etc.)
│   ├── style-dictionary.config.cjs       ← base config for token build
│   ├── motion-recipes/
│   │   ├── aos-reveal.json               ← AOS data-aos values per section role
│   │   ├── motion-orchestrated.tsx       ← Motion page-load orchestrator
│   │   └── gsap-scrolltrigger.ts         ← only when justified
│   └── shadcn-registry.json              ← which shadcn components map to which reference patterns
└── templates/
    ├── reference-REPORT.md               ← the §7 concatenation template
    ├── brand-brief.md                    ← the human-readable summary template
    └── validation-report.md              ← the 8-gate report template (different from nt-site-mirror's)
```

### Trigger condition (in SKILL.md frontmatter)

```
description: |
  Build a brand-authentic website that is 10x better than a named reference site, using the
  brand's real assets and the research-agent profile's brand brief. Trigger when the operator
  gives three inputs: (1) the brand's own site URL, (2) a reference site URL, and (3) at
  least one of the brand's social profiles or a Dropbox folder of brand assets. Do NOT trigger
  for single-URL mirror tasks — that is the nt-site-mirror skill's job.
```

### Top-level process (the SKILL.md body, in 5 numbered steps)

1. **Run the reference-understanding pipeline** (per `understand-the-reference.md`).
   Persist to `reports/reference/`. Stop and report if any substep is blocked.
2. **Send the brand-research brief to research-agent** (per `workflow-design.md` §2).
   Persist the response to `reports/brand/`. Validate the JSON against
   `brand_brief_schema.json`; reject with a clear message if it doesn't conform.
3. **Synthesize the token system** from `reports/brand/palette_from_logo` +
   `reports/reference/tokens/`. Persist via Style Dictionary.
4. **Compose the new site** (per `workflow-design.md` §3 steps 2–7).
5. **Validate** against the 8 gates. Report the tier reached. **Stop and report** if any
   required gate fails — do not claim a higher tier than the evidence supports.

---

## §3 — What gets vendored vs referenced vs downloaded on demand

The `skills-and-repos.md` dossier identified 24 entries. We split them into three groups
based on cost / change-frequency / how much we trust the upstream:

### Vendored under `skills/web-designer/assets/` (committed to this repo)

- **Style Dictionary config skeleton** (`style-dictionary.config.cjs`) — small,
  rarely-changes. Vendor.
- **Tailwind preset** (`tailwind-preset.cjs`) — opinionated defaults for the agent's work.
  Vendor.
- **shadcn registry hint file** (`shadcn-registry.json`) — which shadcn primitives map to
  which reference-section patterns. Vendor.
- **Motion recipe snippets** (AOS / Motion / GSAP) — small, reusable. Vendor.

### Referenced (loaded by name at runtime, not committed)

- **`anthropics/skills/frontend-design`** — load via
  `skill_view(name='frontend-design')` (Hermes auto-resolves the public repo).
- **`anthropics/skills/theme-factory`** — same.
- **`anthropics/skills/web-artifacts-builder`** — same.
- **`anthropics/skills/canvas-design`** + `brand-guidelines` — same.
- **Hermes `popular-web-designs`** — local skill on this machine.
- **Hermes `humanizer`** — local skill on this machine.

### Downloaded on demand (the user runs `pnpm add` or equivalent when scaffolding)

- **shadcn-ui/ui components** — via `npx shadcn@latest add <component>` (CLI copies source
  into the project).
- **`motion`** (Motion, formerly Framer Motion) — npm.
- **`lenis`** — npm.
- **`aos`** — npm.
- **`gsap`** — npm (with the proprietary-licence note documented in the install script).
- **`nuxt/image` or `next/image`** — framework-native.
- **`sharp`** — npm (often transitive).
- **`color-thief`** — npm.
- **`axe-core`** (dev dep), **`@axe-core/playwright`** (dev dep).
- **`lighthouse`** (dev dep), **`@lhci/cli`** (dev dep).
- **`unlighthouse`** (dev dep).
- **`style-dictionary`** (dev dep).
- **`blurhash`** (npm).

### What we do *not* vendor at all

- **GSAP source** — proprietary licence, not redistributable. We *use* it via npm; we do
  not commit a copy.
- **GT Walsheim or any paid font** — brand-side asset, license-bound. Substitute in
  production; document in `brand-brief.typography_recommendation.license_notes`.
- **`onlook-dev/onlook`** — adopt only if the operator wants interactive iteration. Out of
  the autonomous pipeline.

---

## §4 — The research-agent handoff — concrete call site

When `web-designer` skill step 2 runs, the site-cloner agent posts to the `#research`
Discord channel (the research-agent profile's home). The call shape:

```python
# Pseudo-code in the web-designer skill's step 2
import json, requests   # standard libs available everywhere

brief = {
    "task": "brand_research_for_redesign",
    "project_slug": "<our project slug>",
    "brand": {
        "name": operator.brand_name,
        "own_site": operator.brand_site,
        "social": operator.social_handles,
        "assets_provided": operator.dropbox_paths or [],
        "design_brief": operator.brief_text,
    },
    "reference": {"url": operator.reference_url, "rationale": "..."},
    "deliverable": {
        "format": "brand-brief.json + brand-brief.md",
        "save_to": "<workspace>/reports/brand/",
        "must_include": [
            "voice_and_tone", "palette_from_logo", "typography_recommendation",
            "real_photo_inventory", "service_facts", "social_highlights",
            "testimonials", "brand_donts",
        ],
    },
}

# Post to research-agent (channel webhook or gateway API)
response = requests.post(
    "http://127.0.0.1:8648/v1/chat/completions",   # research-agent gateway
    headers={"Authorization": f"Bearer {os.environ['RESEARCH_AGENT_TOKEN']}"},
    json={"channel": "#research", "message": json.dumps(brief)},
)

# Poll research_scrapes table until rows >= len(brief["deliverable"]["must_include"])
# OR timeout (default 30 min)
```

The actual delivery channel may evolve (Discord webhook vs. gateway API); the contract is
the JSON shape and the `reports/brand/brand-brief.json` schema, both of which are stable.

### Cross-profile write guard

Per Hermes's cross-profile rules, the site-cloner agent must NOT write to
`~/.hermes/profiles/research-agent/` directly. Communication is *one-way* (site-cloner →
research-agent via the public Discord channel or gateway). Research-agent writes the
`reports/brand/brand-brief.json` to its own workspace; site-cloner reads from there (or from
a shared filesystem path both profiles can read). See open question §6.5.

---

## §5 — Phased milestones

### Milestone M0 — Research dossier
- ✅ Author the four files in `research/`.
- ✅ Open draft PR for operator review.

### Milestone status summary

| Milestone | Status | Commit(s) |
|---|---|---|
| M1 — Skill scaffold + reference-understanding scripts | ✅ Done | `89bbdbe`, `51f2966` |
| M2 — Brand-brief contract + research-agent integration | ✅ Done | `f92c98d`, `88d546f`, `af26947` |
| M3 — Design pass | ✅ Done | `9debe0f`, `08d68b4` |
| M4 — Validation gate wiring | ✅ Done | `7248c18` |
| M5 — Operator-facing docs + rollout | ✅ Done | this commit |

### Milestone M1 — Skill scaffold + reference-understanding scripts
- ✅ Create `skills/web-designer/SKILL.md` (trigger + 5 steps + honesty rules).
- ✅ Implement `extract_tokens.py`, `inventory_copy.py`, `inventory_components.py`,
  `infer_breakpoints.py` following the recipes in `understand-the-reference.md`.
- ✅ Vendor the assets under `skills/web-designer/assets/`.
- ✅ Validate on 3 reference URLs of varying complexity (a SaaS marketing site, a personal
  portfolio, a content-heavy news site).

### Milestone M2 — Brand-brief contract + research-agent integration
- ✅ Finalize `brand_brief_schema.json` with the research-agent operator.
- ✅ Add the cross-channel posting rule to site-cloner's SOUL.md.
- ✅ Run a smoke test: site-cloner posts a brief, research-agent responds, site-cloner
  validates the JSON shape, both profiles agree on the schema.

### Milestone M3 — Design pass (the actual creative work)
- ✅ Implement step 3 of the web-designer skill (token synthesis + section composition +
  motion design + copy pass).
- ✅ Vendor the motion recipes (CSS-only implementation in the current composer; reference
  material remains under `skills/web-designer/assets/`).
- ✅ Test on the `pedicelmarketing` example from `clone-website/` end-to-end.

### Milestone M4 — Validation gate wiring
- ✅ Wire the 8 gates from `workflow-design.md` §4 into the skill's step 5.
- ✅ Add axe-core/Lighthouse integration to the local validation harness.
- ✅ Validate on the `pedicelmarketing` example; evidence is in `reports/m4-validation/`.

### Milestone M5 — Operator-facing docs + rollout
- ✅ Add a worked example to the project's README.
- ✅ Refresh `skills/web-designer/SKILL.md` from the M1 process stub to the implemented
  five-step workflow, including known limits.
- ✅ Mark M1–M5 status and commit hashes in this plan; §6 remains open for operator input.

---

## §6 — Open questions

These are the decisions we deferred; they need operator input before any code lands.

### §6.1 — Project stack: Next.js, Nuxt, Vite+React, or Astro?

The dossier assumes a modern React-first stack (Tailwind + shadcn + Motion). But the
operator may want Nuxt (Vue), Astro (content-first, islands), or something else. The skill
should be **stack-agnostic at the script level** (Playwright-based reference understanding is
the same regardless of stack) but **stack-specific at the implementation level** (shadcn is
React; Preline has a Vue version; Motion has a Vue wrapper `motion-v`).

**Default if undecided:** **Next.js 15 App Router + Tailwind + shadcn/ui + Motion + Lenis.**
Reason: largest ecosystem, best Lighthouse defaults out of the box, shadcn is React-only.

### §6.2 — GSAP licence comfort

GSAP is free for use but not OSI-approved. If the operator's clients include regulated
industries (finance, healthcare, government), the proprietary licence may be a blocker.
**Default if undecided:** use GSAP *only* when ScrollTrigger-pinned choreography is in the
brief; document the licence in the deliverable's licensing section.

### §6.3 — Brand asset hosting

Where do the brand's real photos live? Three patterns:

- **Dropbox / Drive** — operator pastes paths; site-cloner downloads via `web_fetch` or
  copy-paste.
- **CDN (Cloudinary, Imgix, imgproxy)** — operator provides URL pattern; site-cloner uses
  it directly with `nuxt/image` or `next/image`.
- **Local-first (the brand re-uploads to the project)** — cleanest for asset hygiene but
  highest operator overhead.

**Default if undecided:** **CDN with `imgproxy`** (entry not in the dossier yet — `imgproxy/imgproxy`,
Apache-2.0, would be the host) so brand assets are processed server-side. Falls back to
operator-pasted Dropbox paths when no CDN.

### §6.4 — How prescriptive is the "10x" claim?

"10x better" is a metaphor. The dossier uses the metaphor but the validation step reports
*measurable* differences (Lighthouse 96 vs 54, axe 0 violations, real photos vs stock).
**Question:** is the metaphor enough for the operator, or do we need a specific rubric
("10x = Lighthouse +30, axe -100% critical, motion vocabulary ≥ reference, real assets in
≥ 5 places")? The default is to *report metrics, claim the metaphor*.

### §6.5 — Cross-profile handoff transport

Three options:

- **Discord channel** (`#research` ← site-cloner posts; research-agent reads). Simple,
  visible to humans, but adds latency and human-visible noise.
- **Local HTTP gateway** (`hermes-gateway-research-agent` on port 8648; site-cloner POSTs
  to `/v1/chat/completions`). Machine-to-machine, lowest latency, but couples the two
  profiles at the process level.
- **Shared filesystem** (research-agent writes `reports/brand/brand-brief.json` to a path
  both profiles can read; site-cloner polls). Simple, no coupling, but polling latency.

**Default if undecided:** **local HTTP gateway** (option 2). Reasoning: site-cloner is
already a long-running Hermes agent on `127.0.0.1`; the research-agent gateway exists at
port 8648 per its own context. The contract is the JSON schema, not the transport.

### §6.6 — Brand-brief storage and retention

The `research_scrapes` table in research-agent's Supabase DB is the natural store. The
question is retention: keep forever (default for research), or TTL after the project ships?
**Default if undecided:** **forever** — the brand-brief is the *single most valuable artifact*
in the workflow; we never want to re-derive it. Match research-agent's existing retention.

### §6.7 — Reference sites that are themselves blocked or paywalled

Some "reference" sites the operator names may themselves be blocked (Cloudflare-heavy,
login-walled, geo-fenced). `extract_tokens.py` works on public HTML; it cannot extract from
a page that won't load. **Default if undecided:** if the reference can't be loaded, fall
back to **public design write-ups** (e.g. the site is featured on https://www.siteinspire.com
or https://land-book.com — those write-ups often include a screenshot + palette + type
breakdown) and document the fallback in the reference brief.

### §6.8 — Operator vs fully autonomous

Does the operator want to be in the loop at every creative decision, or does the agent
ship the deliverable and the operator reviews at the end? The default in the dossier is
**autonomous with one mid-flight checkpoint** (post the brand brief + reference brief
back to the operator before starting the design pass, then ship). If the operator wants
continuous approval, the skill needs a `clarify()` integration at every section boundary.

---

## §7 — Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Research-agent returns malformed JSON | med | Strict JSON-schema validation in step 2; reject + re-request with the schema attached |
| Reference site is a Wix/Webflow builder that won't render locally | high (already known) | Use `nt-site-mirror`'s builder-runtime guidance: Editable Recreation of the *reference brief*, then build the new site from scratch |
| Brand has no public social presence | low–med | Use the brand's own site copy + operator-supplied photos; document the empty social_highlights; do *not* fabricate posts |
| GSAP licence issue surfaces late in a project | low | Default = no GSAP; only add when ScrollTrigger is in the brief |
| Operator wants 11pm Friday delivery | certain | Do *not* compromise the 8 validation gates; deliver a `Partial` with an honest list of un-exercised gates instead of a falsely-`Pass`ing site |
| Token system drifts from brand-brief on iteration | med | Treat `tokens/dist/tokens.css` as the single source of truth; lint rule: any new color in a component must reference a token variable |
| Cross-profile gateway is down | low | Fall back to Discord-channel handoff; document the latency |
| Operator forgets to provide brand assets | med | The skill must refuse to start if `assets_provided` is empty *and* no social handles are reachable — explicit error, not silent stock-photo fallback |

---

## §8 — What "done" looks like for this dossier (THIS PR)

This document and the other three in `research/` are the *output* of the research-only task.
They are:

- ✅ 4 markdown files, every claim sourced from a real artifact.
- ✅ 24 verified entries in `skills-and-repos.md` (URL + license for each).
- ✅ Concrete handoff schema + worked example in `workflow-design.md`.
- ✅ Phased milestones M0–M5 in `integration-plan.md`.
- ✅ 8 open questions flagged for operator input before M1 starts.

When the operator approves this PR, the next step is **M1: skill scaffold + reference-
understanding scripts** (per §5 above). Until then, no implementation work begins.