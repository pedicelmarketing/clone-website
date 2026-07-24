---
name: web-designer
description: Build a brand-authentic website that is measurably better than a named reference site, using the brand's own assets and a research-agent-produced brand brief. Trigger when the operator gives three inputs: (1) the brand's own site URL, (2) a reference site URL, and (3) at least one of the brand's social profiles or a Dropbox folder of brand assets. Do NOT trigger for single-URL faithful mirror tasks — that is the nt-site-mirror skill's job. Do NOT trigger for color-token / copy inventory / component inventory / breakpoint inference on a single URL — those are isolated scripts under this skill and can be invoked directly without the full 5-step workflow.
license: Adapted internal copy. See LEGAL_NOTICE.md.
---

# Web Designer — 5-step brand-authentic redesign workflow

This skill takes three inputs (brand site + reference site + brand social/asset folder) and
produces a new site that is brand-authentic (real copy, real photos, real services) and
measurably better than the reference (the reference's *craft* without copying its *code*).

It is the **phase-2** sibling of `nt-site-mirror`. That skill produces a *faithful baseline*
of a single URL; this skill produces a *new* site that is informed by a reference but lives
in the brand's world. The two skills share the same tooling philosophy: observation is the
floor, structure is the goal, and a missing feature is a Fidelity Gap, never a Pass.

**This M1 copy is process-only.** The four scripts under `scripts/` (`extract_tokens.py`,
`inventory_copy.py`, `inventory_components.py`, `infer_breakpoints.py`) are the
reference-understanding passes that step 1 needs. The brand-brief handoff (step 2), token
synthesis (step 3), design pass (step 4), and validation gates (step 5) are not yet
implemented — they arrive in M2+. Each script can be invoked in isolation; the 5-step
process below describes how the *workflow* will compose them once M2-M5 land.

---

## Honesty rules (apply to every step)

The same discipline as `nt-site-mirror` applies here. Every claim must be backed by observed
evidence.

- **Observation is the floor.** Every structural fact, every token, every component, every
  breakpoint, every copy block must come from a real observation. Fabricating a section
  list you did not observe, a palette you did not extract, or a testimonial you did not
  find is a Fidelity Gap.
- **Pass / Partial / Blocked.** State the tier the evidence supports. Do not claim a
  higher tier. A script that exits nonzero is a blocker, not a partial — fix the script
  or fix the input, then re-run.
- **Asset hygiene.** The same classification table as `nt-site-mirror` (Original / Local
  Copy / Embed / Kept External / User-Supplied Baseline Asset / Recreated / Approximated /
  Blocked / Unknown) applies to extracted tokens, captured fonts, and inventoried
  components. The reference's source code is *not* extracted — only its observable
  *behavior* (tokens, structure, copy, motion) is.
- **Each script reports its own evidence basis.** Every output JSON includes a
  `meta.evidence_basis` field: `Observed visually` / `Interaction-tested` /
  `DOM+assets confirmed` / `HTTP-200 only` / `Not exercised`. A "Pass" backed only by
  HTTP 200s must say so.
- **Builder-hosted / telemetry-heavy sites emit benign errors.** Wix, Squarespace, and
  Webflow targets will produce console errors and blocked sub-resources from their own
  runtime — these are present on the live source too, so they are not mirror defects.
  When any of these scripts run against such a target, the script must record the access
  state honestly (`Observed under challenge`, `Blocked by bot mitigation`, etc.) and emit
  whatever data it could still extract, rather than exiting silently.
- **No silent fallbacks.** If a script cannot extract a token class (e.g. no CSS custom
  properties at `:root`), it writes an empty array for that class and notes the reason
  in the output's `meta.notes` — it does not invent counts or fake values.

## The 5-step process

### Step 1 — Understand the reference

Owner: **site-cloner agent itself**, with the `nt-site-mirror` skill + the four M1 scripts
under this skill.

Substeps:
1. `capture_assets.py <reference_url> -o reports/reference/asset-graph.json` — existing
   `nt-site-mirror` script; produces the runtime asset graph.
2. `extract_tokens.py <reference_url> -o reports/reference/tokens/` — this skill; emits
   `tokens/color.json`, `tokens/typography.json`, `tokens/spacing.json`,
   `tokens/radius.json`, `tokens/shadow.json` per `understand-the-reference.md` §2.
3. `inventory_copy.py <reference_url> -o reports/reference/copy.json` — this skill;
   emits the copy inventory with section/role/source_url labels per §3.
4. `inventory_components.py <reference_url> -o reports/reference/components.json` — this
   skill; emits the component instance map per §4.
5. `infer_breakpoints.py <reference_url> -o reports/reference/breakpoints.json` — this
   skill; sweeps widths 320..1920 and emits the responsive breakpoint map per §5.
6. `motion_audit.py --source-url <reference_url> --local-url <reference_url> --record-only
   --out reports/reference/motion --seconds 12` — reuse existing `nt-site-mirror` tool,
   *record-only* mode, to produce a webm of the reference's motion vocabulary.
7. Concatenate into `reports/reference/REPORT.md` using `templates/reference-REPORT.md`.

**Honesty constraint:** if any substep is blocked (e.g. reference is a Wix site with
session-coupled root document — see `nt-site-mirror`'s builder-runtime guidance), document
the block and fall back to observation-only. Do not invent a section list you did not
observe.

**Stop and report** if any substep is blocked. The reference brief is the input to every
later step; an incomplete brief produces an incomplete redesign.

### Step 2 — Understand the brand (research-agent handoff)

Owner: **`research-agent` profile** (M2+).

Site-cloner posts a structured brief to the `#research` channel (the research-agent home)
describing the brand site, the reference, the operator's design brief, and the deliverable
schema. Research-agent returns `reports/brand/brand-brief.json` (machine-readable) +
`reports/brand/brand-brief.md` (1-page human summary).

Site-cloner validates the JSON against `scripts/brand_brief_schema.json` (M2+). Reject
with a clear message if it does not conform.

**Stop and report** if research-agent returns partial / blocked content. Do not invent
brand facts (testimonials, services, photos) to fill in gaps; record the gap in the
validation report and ask the operator.

### Step 3 — Synthesize the token system

Owner: **site-cloner agent itself** (M3+).

Build a single token system that fuses the brand's real palette (from
`brand-brief.palette_from_logo`) with the reference's typographic discipline (from
`reports/reference/tokens/`). Persist via Style Dictionary →
`tokens/dist/tokens.css` + `tailwind.config.ts`. The reference's tokens are *not* copied
holistically — they suggest the *scale* the designer cared about; the brand's palette
overrides the *colors*.

**Token discipline:** every new color in a component must reference a token variable. No
ad-hoc hex codes in component files.

### Step 4 — Compose the new site

Owner: **site-cloner agent itself** (M3+).

Per `workflow-design.md` §3, this is the actual creative work: section composition, motion
design, copy pass, signature element, *iterate with screenshots*. Push the 10x not by
re-coding the reference but by replacing each reference component with the
accessible, theme-able shadcn equivalent, then visually differentiating through tokens.

### Step 5 — Validate against the 8 gates

Owner: **site-cloner agent itself** (M4+).

Per `workflow-design.md` §4 and `references/validation-checklist.md`: boot, dependency,
accessibility (axe), performance (Lighthouse ≥ 90), site-wide audit (unlighthouse),
responsive (viewports), motion, source-paired. Each gate states its evidence basis;
failure → `Partial` / `Fidelity Gap` per the acceptance tiers.

---

## Asset classification (canonical — referenced by every step)

The same table as `nt-site-mirror`, applied to *extracted* tokens / *captured* fonts:

| Status | Meaning (in the web-designer context) |
|--------|--------------------------------------|
| `Original` | (not used here — web-designer builds a *new* site, not a mirror) |
| `Local Copy` | A token / font / component that the new site reproduces from the reference's extracted values |
| `Embed` | A third-party widget kept in the new deliverable (e.g. Cal.com embed) |
| `Kept External` | A reference asset kept external in the redesign (e.g. a font CDN URL) |
| `User-Supplied Baseline Asset` | A brand-provided asset (logo, photo) — the source of truth for the brand's palette |
| `Recreated` | A component rebuilt from observation (we observed it, then re-coded it in shadcn) |
| `Recreated From Observation` | Same as Recreated; preferred wording when the recreation is explicitly visual |
| `Approximated` | A reference token / component where the extracted value was incomplete (e.g. only 3 of 4 weights available) |
| `Blocked` | An extractor couldn't capture the asset (CSP, XHR, etc.) |
| `Unknown` | Default when extraction is not yet exercised |

`User-Supplied Baseline Asset` is the most important status here — it is the *brand*'s
asset, not the *reference*'s. The brand-brief is the pathway that fills this in (M2+).

## Evidence priority

1. Operator-provided brand assets (Dropbox paths, social screenshots)
2. Brand-brief JSON from research-agent
3. Reference brief from step 1 (extracted tokens, copy, components, breakpoints, motion)
4. Live website (the reference)
5. Source inspection (the reference's CSS / DOM)

Higher priority wins. Conflicts go in the validation report's Risks section.

## Conventions

- **File layout.** All reference outputs land under `reports/reference/`. All brand
  outputs (when M2+ lands) under `reports/brand/`. Validation under `reports/validation/`.
- **Output path on stdout.** Each script prints the path(s) it wrote to stdout so a
  parent orchestrator can chain them. Errors go to stderr; exit code is nonzero on
  failure. Strict — the same honesty discipline as `nt-site-mirror`.
- **Python interpreter.** Reference-understanding scripts that need a browser use
  `~/.venvs/nt-mirror/bin/python` (the same Playwright/Chromium interpreter
  `nt-site-mirror` uses). Scripts that don't need a browser use plain `python3`.
- **What we do NOT do.** No rebrand of the reference. No copy of the reference's
  source code. No extraction of the reference's JS bundle. No inference of values that
  were not observed. The reference brief is *descriptive* of the reference, not a
  template for the new site.

## File layout

```
skills/web-designer/
├── SKILL.md                              ← this file (process only, M1 scope)
├── scripts/
│   ├── extract_tokens.py                 ← M1 — color/typography/spacing/radius/shadow
│   ├── inventory_copy.py                 ← M1 — every text node tagged by section + role
│   ├── inventory_components.py           ← M1 — component instance detection
│   ├── infer_breakpoints.py              ← M1 — Playwright width sweep 320..1920
│   └── brand_brief_schema.json           ← M2 — research-agent return contract
├── references/
│   ├── token-extraction-recipes.md       ← M1 — vendored from understand-the-reference §2
│   ├── validation-checklist.md           ← M1 — the 8 gates from workflow-design §4
│   ├── motion-vocabulary-to-library.md   ← M2+ — vendored from workflow-design §3
│   ├── brand-brief-contract.md           ← M2+ — JSON schema + worked example
│   └── anti-ai-slop.md                   ← M3+ — vendored from frontend-design skill
├── templates/
│   ├── reference-REPORT.md               ← M1 — the §7 concatenation template
│   ├── brand-brief.md                    ← M2+ — human-readable summary
│   └── validation-report.md              ← M4+ — the 8-gate report template
└── assets/
    ├── tailwind-preset.cjs               ← M3+ — opinionated preset
    ├── style-dictionary.config.cjs       ← M3+ — base config for token build
    ├── motion-recipes/                   ← M3+ — AOS / Motion / GSAP snippets
    └── shadcn-registry.json              ← M3+ — which shadcn components map to which patterns
```

This M1 commit ships the four scripts plus the M1-scoped references and templates. M2+
files are placeholders (`PACKED_WITH_M2_PLACEHOLDER` content) so the directory tree
matches `integration-plan.md` §2 from day one — they will be filled in their respective
milestones, not as a single batch.
