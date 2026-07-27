---
name: web-designer
description: Build a brand-authentic website that is measurably better than a named reference site, using the brand's own assets and a research-agent-produced brand brief. Trigger when the operator gives three inputs: (1) the brand's own site URL, (2) a reference site URL, and (3) at least one of the brand's social profiles or a Dropbox folder of brand assets. Do NOT trigger for single-URL faithful mirror tasks — that is the nt-site-mirror skill's job. Do NOT trigger for color-token / copy inventory / component inventory / breakpoint inference on a single URL — those are isolated scripts under this skill and can be invoked directly without the full 5-step workflow.
license: Adapted internal copy. See LEGAL_NOTICE.md.
---

# Web Designer — 5-step brand-authentic redesign workflow

This skill takes three inputs — the brand's own site, a reference site, and brand social or asset
inputs — and produces a new, brand-authentic site. The reference contributes observable
structure, typography, responsive behavior, and motion vocabulary; it does not contribute copied
source code or visual identity. This is the phase-2 sibling of `nt-site-mirror`: a single-URL
faithful baseline still belongs to that skill.

All five workflow steps are implemented in this repository. The scripts are deterministic where
measurement matters, and every handoff is evidence-bearing:

1. reference understanding (`capture_assets.py`, `extract_tokens.py`, `inventory_copy.py`,
   `inventory_components.py`, `infer_breakpoints.py`, and record-only `motion_audit.py`);
2. brand-brief handoff and schema validation (`research-agent`, `validate_brand_brief.py`);
3. token synthesis (`synthesize_tokens.py`);
4. static design pass / composition (`compose_site.py`);
5. eight-gate validation (`validate_site.py`).

---

## Trigger and inputs

Trigger this skill only when the operator provides all three inputs:

1. the brand's own site URL;
2. a reference site URL, admired for structure/craft/motion rather than visual identity; and
3. at least one brand social handle or a folder of brand assets (logo, photos, copy, or related
   material).

Do not trigger it for a single-URL mirror request. Do not use it to make an isolated token, copy,
component, or breakpoint observation sound like a redesign. The isolated browser scripts may be
invoked directly when that is all the operator requested.

## Honesty rules (apply to every step)

The same evidence discipline as `nt-site-mirror` applies throughout this workflow.

- **Observation is the floor.** Structural facts, tokens, components, breakpoints, copy blocks,
  brand facts, and motion claims must come from an observed artifact or an operator-provided
  input. Do not fabricate a section, palette, testimonial, service, photo, or social post.
- **Pass / Partial / Blocked.** State the tier supported by the evidence. A required script that
  exits nonzero is a blocker: stop, preserve its diagnostic output, and report it. Do not silently
  continue with guessed inputs.
- **Evidence basis is explicit.** Per-system claims use one of `Observed visually`,
  `Interaction-tested`, `DOM+assets confirmed`, `HTTP-200 only`, or `Not exercised`. A result
  backed only by an HTTP response is not a browser-behavior claim.
- **Positive evidence only.** A zero count is a pass only when the runner exited cleanly and
  emitted a parsed result document containing that count. Missing output is `Not exercised`, not
  an inferred pass.
- **Asset hygiene.** Use the canonical statuses `Original | Local Copy | Embed | Kept External |
  User-Supplied Baseline Asset | Recreated | Recreated From Observation | Approximated | Blocked |
  Unknown`. Paid fonts, protected assets, and provider-streamed media remain classified and are
  not silently redistributed.
- **Blocked source = limitation.** If own-site, social, or reference research is blocked, carry
  the limitation into the brief/build/validation report. Empty arrays stay empty. Never replace a
  missing real photo with stock content or invent a testimonial.
- **No silent fallbacks.** Extractors emit empty arrays and notes when a class cannot be observed;
  they do not synthesize values. The composer omits sections whose source data is absent and
  records the reason in `BUILD-REPORT.md`.
- **Fidelity gap rule.** A missing, frozen, disabled, or materially downgraded in-scope feature is
  a `Fidelity Gap`, never a `Pass`. An accepted exception remains an exception.
- **Acceptance tiers.** Use only the tier supported by exercised evidence: `First-render`,
  `Validated (declared scope)`, `Offline-validated`, or `Partial`.

## Runtime prerequisites and interpreter split

Run project commands from the repository root.

- Browser scripts require Playwright and Chromium through
  `~/.venvs/nt-mirror/bin/python` (on this host: `/home/openclaw/.venvs/nt-mirror/bin/python`).
  This applies to `capture_assets.py`, `extract_tokens.py`, `inventory_copy.py`,
  `inventory_components.py`, `infer_breakpoints.py`, and record-only `motion_audit.py`.
- `validate_brand_brief.py`, `synthesize_tokens.py`, and `compose_site.py` are stdlib-only and run
  with `python3`.
- `validate_site.py` is launched with `python3`. Its browser-backed responsive and axe checks use
  the Playwright venv; axe-core and Lighthouse require `node`/`npx` (the harness invokes them via
  `npx`). If a required runner is unavailable, the affected gate is `Not exercised` and the tier
  is downgraded.
- Step 2 belongs to the separate `research-agent` profile. Send the structured request through
  the configured inter-profile channel/gateway and read the returned files; never write into
  `~/.hermes/profiles/research-agent/` directly.

## The five implemented steps

### Step 1 — Understand the reference

Owner: site-cloner, using the existing `nt-site-mirror` capture helper and this skill's browser
scripts. Persist all outputs under a project-local `reports/reference/` directory.

```sh
PYBROWSER="$HOME/.venvs/nt-mirror/bin/python"
REFERENCE_URL="https://example-reference.test"
REFERENCE_DIR="reports/reference"
mkdir -p "$REFERENCE_DIR/tokens"

"$PYBROWSER" skills/nt-site-mirror/scripts/capture_assets.py \
  "$REFERENCE_URL" -o "$REFERENCE_DIR/asset-graph.json"
"$PYBROWSER" skills/web-designer/scripts/extract_tokens.py \
  "$REFERENCE_URL" -o "$REFERENCE_DIR/tokens/"
"$PYBROWSER" skills/web-designer/scripts/inventory_copy.py \
  "$REFERENCE_URL" -o "$REFERENCE_DIR/copy.json"
"$PYBROWSER" skills/web-designer/scripts/inventory_components.py \
  "$REFERENCE_URL" -o "$REFERENCE_DIR/components.json"
"$PYBROWSER" skills/web-designer/scripts/infer_breakpoints.py \
  "$REFERENCE_URL" -o "$REFERENCE_DIR/breakpoints.json"
```

When the reference has meaningful motion, record it with the existing helper:

```sh
"$PYBROWSER" skills/nt-site-mirror/scripts/motion_audit.py \
  --source-url "$REFERENCE_URL" --local-url "$REFERENCE_URL" --record-only \
  --out "$REFERENCE_DIR/motion" --seconds 12
```

Fill `reports/reference/REPORT.md` from `templates/reference-REPORT.md`. The four web-designer
scripts emit `color.json`, `typography.json`, `spacing.json`, `radius.json`, `shadow.json`,
`copy.json`, `components.json`, and `breakpoints.json` with metadata and an evidence basis.
`capture_assets.py` supplies the runtime asset graph; `motion_audit.py` is record-only here.
Stop and report a blocked substep rather than inventing a reference brief.

### Step 2 — Understand the brand via research-agent

Owner: the `research-agent` profile. Post a request matching `research/workflow-design.md §2.1`:
`task: "brand_research_for_redesign"`, `project_slug`, `brand{name, own_site, social,
assets_provided, design_brief}`, `reference{url, rationale}`, and
a `deliverable{format, save_to, must_include}`. Research-agent returns:

- `reports/brand/brand-brief.json` — machine-readable contract;
- `reports/brand/brand-brief.md` — human-readable summary.

Validate before consuming the brief:

```sh
python3 skills/web-designer/scripts/validate_brand_brief.py \
  reports/brand/brand-brief.json \
  --schema skills/web-designer/scripts/brand_brief_schema.json
```

The command must print `VALID <path>`. If it does not, reject the brief and re-request with the
schema attached. Partial or blocked source declarations in the brief are authoritative; do not
supplement them with guesses or a second uncontracted scrape.

### Step 3 — Synthesize the token system

Owner: site-cloner, using `synthesize_tokens.py`. The validated brand brief owns the palette and
font-family decisions. The reference token directory contributes observed structural scales;
reference colors are intentionally not copied wholesale. The script emits Style-Dictionary-
friendly JSON, canonical CSS, a Tailwind bridge, and provenance.

```sh
python3 skills/web-designer/scripts/synthesize_tokens.py \
  --brand-brief reports/brand/brand-brief.json \
  --reference-tokens reports/reference/tokens \
  -o reports/tokens
```

Required outputs include `reports/tokens/tokens/dist/tokens.css`,
`reports/tokens/tokens/dist/tailwind-tokens.json`, and `reports/tokens/tokens/PROVENANCE.md`.
Every new page color must reference a token variable; paid-font license notes stay in provenance.

### Step 4 — Compose the new site

Owner: site-cloner, using `compose_site.py`. This is a real, executable design pass: it selects
and orders sections from available brand data, uses brand-authentic copy/assets, emits token-driven
HTML/CSS, applies the implemented CSS motion recipe, and writes a build report listing emitted and
skipped sections plus limitations. It revalidates the brief before composing.

```sh
python3 skills/web-designer/scripts/compose_site.py \
  --brand-brief reports/brand/brand-brief.json \
  --tokens reports/tokens \
  --reference-report reports/reference \
  -o reports/site
```

The output is a servable site containing `index.html`, `tokens.css`, `styles.css`, and
`BUILD-REPORT.md`. Missing source data causes an explicit skipped section, not invented content.

### Step 5 — Validate the eight gates

Owner: site-cloner, using `validate_site.py` and its local-server/browser/Node integrations.
The harness validates the declared routes (default `/`) and viewport widths (default
`320,768,1024,1440`) and writes both machine-readable and Markdown evidence.

```sh
python3 skills/web-designer/scripts/validate_site.py \
  reports/site -o reports/validation
```

Available options include `--routes /,/about`, `--viewports 320,768,1024,1440`,
`--timeout 30`, and `--skip-lighthouse`. Do not use `--skip-lighthouse` when claiming a full
validated tier. The eight reported gates are boot, dependency, accessibility (axe), performance
(Lighthouse), site-wide audit, responsive, motion/reduced-motion, and token discipline. Every
verdict carries its evidence basis; any `FAIL` or `NOT-EXERCISED` result prevents a `Validated`
claim.

## Known limits

- The composer emits one single-route static HTML/CSS site. It has no framework build and no
  multi-route composition yet.
- Motion is CSS-only (the emitted restrained fade/slide recipe plus reduced-motion handling); it
  does not implement JavaScript motion libraries or a video-motion recreation pass.
- The design pass does not yet map observed components to shadcn primitives and does not yet run
  a separate signature-element pass. Those are M3 stretch items described in
  `research/workflow-design.md §3`, and are not implemented here.
- Reference understanding can observe multiple routes only when the operator invokes the scripts
  for those routes; the current composer still emits one route.
- Kept-external and blocked/paid assets remain dependencies or documented limitations. They are not
  silently downloaded or replaced.

## Asset classification

Use the canonical table below for every reference, brand, and generated asset:

| Status | Web-designer meaning |
|---|---|
| `Original` | Not a phase-2 deliverable asset; phase 2 creates a new site. |
| `Local Copy` | A permitted local representation of an observed value or asset. |
| `Embed` | A third-party widget intentionally retained. |
| `Kept External` | A classified external URL left outside the output. |
| `User-Supplied Baseline Asset` | A brand-provided logo, photo, or other source-of-truth asset. |
| `Recreated` / `Recreated From Observation` | A new implementation based on observed behavior. |
| `Approximated` | An incomplete observation represented with an explicit limitation. |
| `Blocked` | Capture or acquisition was prevented. |
| `Unknown` | Not exercised or not yet classified. |

## Evidence and delivery checklist

Before reporting a phase-2 result:

- [ ] The three-input trigger was satisfied and the reference scope is declared.
- [ ] Step-1 JSON and the reference report are present, with blocks and unknowns documented.
- [ ] Research-agent returned a schema-valid brief; `validate_brand_brief.py` printed `VALID`.
- [ ] Token provenance identifies brand-authoritative versus reference-structural inputs.
- [ ] `BUILD-REPORT.md` records emitted/skipped sections and carried-forward limitations.
- [ ] `validate_site.py` produced `gate-results.json` and `validation-report.md`.
- [ ] Every gate and external dependency has an evidence basis and honest status.
- [ ] The final acceptance tier matches the actual exercised evidence.

For the handoff contract and unresolved operator decisions, see `research/workflow-design.md` and
`research/integration-plan.md`. For a copy-pasteable worked example and the measured M4 result,
see the repository-root `README.md`.
