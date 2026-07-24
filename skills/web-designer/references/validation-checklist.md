# Validation checklist — the 8 gates

This is the condensed checklist the design-pass deliverable is validated against. Per
`research/workflow-design.md` §4, the validation step runs after the redesign is built.
Each gate has a pass criterion, a tool, and an evidence basis.

**M1 scope:** the four scripts (`extract_tokens.py`, `inventory_copy.py`,
`inventory_components.py`, `infer_breakpoints.py`) implement the *reference* side of
the validation. The 8 gates here are the *deliverable* side — they will be wired into
the validation pass in M4. The M1 deliverable does not claim any of these gates pass;
it only contributes the evidence (the reference brief) that the gates will be compared
against.

**Honesty constraint:** the same `Observed visually` / `Interaction-tested` /
`DOM+assets confirmed` / `HTTP-200 only` / `Not exercised` discipline used by
`nt-site-mirror` applies here. A gate can only be marked `Pass` if the evidence basis
supports it.

---

## Gate 1 — Boot

**Pass criterion:** the site serves locally through one documented command
(`pnpm dev`, `next dev`, `vite`, `nuxt dev`, etc.) and reaches a usable terminal state.

**Tool:** the operator's own project command (not a web-designer script — the gate
verifies the project's setup).

**Evidence basis:** `Observed visually` (the operator sees the site load) /
`HTTP-200 only` (the gate accepts at least a 200 on `/`).

**Failure mode:** the site throws on first load, the SPA entry is missing, or the
local server can't start. Document as a `Fidelity Gap` and stop the validation.

---

## Gate 2 — Dependency

**Pass criterion:** no unresolved console errors, no failed local 4xx, every external
asset classified per the `nt-site-mirror` asset table (Original / Local Copy / Embed /
Kept External / User-Supplied Baseline Asset / Recreated / Approximated / Blocked /
Unknown).

**Tool:** Playwright + a console/network recorder (similar to `nt-site-mirror`'s
`capture_assets.py` — same JSON shape, just verifying the *new* site renders the
same way).

**Evidence basis:** `DOM+assets confirmed` (the page returned clean for every route).

**Failure mode:** the new site tries to load the reference's CDN-hosted font, the
reference's hero image, or the reference's API endpoint. The asset table must classify
each one and the classification must be honored (paid fonts substituted, etc.).

---

## Gate 3 — Accessibility (axe)

**Pass criterion:** `dequelabs/axe-core` run on every in-scope route via
`@axe-core/playwright`. **0 serious or critical violations.**

**Tool:** `axe-core` + Playwright. The audit script is not yet implemented in M1; it
arrives in M4.

**Evidence basis:** `DOM+assets confirmed` (axe runs against the rendered DOM).

**Failure mode:** missing alt text, missing form labels, insufficient color contrast,
keyboard traps, etc. Each must be fixed before the gate passes.

---

## Gate 4 — Performance (Lighthouse)

**Pass criterion:** `GoogleChrome/lighthouse` on every route at mobile (390×844) and
desktop (1440×900). **Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95, SEO
≥ 95.**

**Tool:** `lighthouse` (CLI) and `@lhci/cli` for CI integration.

**Evidence basis:** `DOM+assets confirmed` (Lighthouse measures the rendered DOM).

**Failure mode:** unoptimized images, render-blocking JS, missing meta tags, missing
sourcemaps, etc. The 10x against the reference is typically visible here — the
reference's old design system often scores 50-60.

---

## Gate 5 — Site-wide audit (unlighthouse)

**Pass criterion:** `harlan-zw/unlighthouse` over every in-scope route. The result
matrix is included in `validation-report.md` so the operator can see at-a-glance which
routes pass which Lighthouse audits.

**Tool:** `unlighthouse` (CLI).

**Evidence basis:** `DOM+assets confirmed`.

**Failure mode:** the same as gate 4, surfaced route-by-route. Some routes may fail
intentionally (e.g. the 404 page) — those are documented as out of scope.

---

## Gate 6 — Responsive (viewports)

**Pass criterion:** `viewports.py` (from `nt-site-mirror`) at 320, 768, 1024, 1440 on
at least 3 routes. Layout must remain usable (no horizontal overflow, no overlap, no
truncated content).

**Tool:** `nt-site-mirror/scripts/viewports.py`. Source-paired validation against the
reference (subtracts source-side errors from the count).

**Evidence basis:** `DOM+assets confirmed` (the script captures the rendered DOM at
multiple widths).

**Failure mode:** the new site uses a min-width that breaks the 320px budget, or
omits a media query the reference had. Compare against the breakpoints detected by
`infer_breakpoints.py` for the reference, and verify the new site covers the same
subset.

---

## Gate 7 — Motion

**Pass criterion:** for any route with motion, capture a short webm and visually
verify the vocabulary matches the **brand brief** (not the reference). Restrained
brand → no flashy effects. Cinematic brand → Motion + Lenis + maybe GSAP.

**Tool:** `nt-site-mirror/scripts/motion_audit.py` (the Gemini video vision backend).
For the deliverable (not the reference), compare against the brand brief's
"preferred motion vocabulary" rather than against the reference.

**Evidence basis:** `Observed visually` (the operator reviews the comparison).

**Failure mode:** the new site uses motion that contradicts the brief (e.g. a
playful brand brief produces a static site, or a restrained brand brief produces a
parallax-heavy site). Document and re-iterate.

---

## Gate 8 — Source-paired (10x)

**Pass criterion:** if the deliverable is compared directly to the reference, render
both side-by-side and confirm the new site is *measurably* better (the "10x" is a
metaphor, not a metric).

**Tool:** `motion_audit.py` for motion parity; manual side-by-side for visual;
Lighthouse-vs-Lighthouse for performance; axe-vs-axe for accessibility.

**Evidence basis:** `Observed visually` / `Interaction-tested` / `DOM+assets
confirmed` — name the basis per comparison.

**Failure mode:** the new site regresses on a metric the reference was strong on
(e.g. new site gets 70 Performance, reference got 90). Document the regression and
re-iterate.

---

## Overall validation verdict

The deliverable's tier is determined by how many gates pass *and* the evidence basis
of each pass:

- **First-render** — every required gate passes trivially; the deliverable renders in
  a browser without lag.
- **Validated (declared scope)** — at least 6 of 8 gates pass with `DOM+assets
  confirmed` evidence; the remaining 2 are either `Not exercised` or `Accepted
  exception`.
- **Offline-validated** — the deliverable renders, but the validation evidence is
  `HTTP-200 only` (no live Playwright run recorded).
- **Partial** — fewer than 6 gates pass, or any gate fails on a critical evidence
  basis (e.g. axe shows serious violations).

**Never** present a lower tier as a higher tier. **Never** describe a Partial as
Validated just because the visual evidence is encouraging.

---

## Cross-references

- `nt-site-mirror/SKILL.md` — the phase-1 skill this checklist mirrors.
- `nt-site-mirror/scripts/viewports.py` — the gate-6 tool.
- `nt-site-mirror/scripts/motion_audit.py` — the gate-7 tool.
- `research/workflow-design.md` §4 — the canonical source of this checklist.
- `templates/validation-report.md` (M4+) — the report template that fills these gates.
