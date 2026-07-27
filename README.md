# Clone Website

This repository contains the site's faithful phase-1 mirrors and the phase-2 web-designer
workflow. Phase 1 preserves a supplied site as a local baseline; phase 2 uses a brand site,
a reference site, and the brand's own research/assets to compose a different site.

## Existing mirrors (phase 1)

The mirror folders are the original baseline artifacts. Do not treat the phase-2 composer as a
replacement for them or edit a mirror as part of reference understanding.

- `barcoopbevy/` — captured frontend and asset manifest.
- `burritomadre/` — multi-route WordPress/Elementor mirror.
- `krati-lodha/` — Vite/SPA mirror.
- `pedicelmarketing/` — Webflow mirror.
- `examples/riki-coach/` — editable-recreation example.

Each completed static mirror keeps its machine-authoritative `mirror-manifest.json` next to the
captured files. For a new single-URL baseline, use `skills/nt-site-mirror/SKILL.md`; the phase-2
workflow below is a redesign workflow, not a mirror or a rebrand of an existing mirror.

## Web designer (phase 2)

Use this workflow when the operator supplies all three inputs:

1. the brand's own site URL;
2. a reference site URL, used for structural/typographic/motion understanding rather than visual
   identity; and
3. brand social handles and/or a folder of real brand assets.

The workflow is deliberately evidence-first:

```text
reference-understanding
  extract_tokens.py + inventory_copy.py + inventory_components.py + infer_breakpoints.py
        ↓
research-agent (structured handoff)
        ↓
brand-brief.json → validate_brand_brief.py
        ↓
synthesize_tokens.py
        ↓
compose_site.py
        ↓
validate_site.py (8 gates)
```

This produces a new, brand-authentic static site. It does not copy the reference site's source
code, invent brand facts, or silently substitute stock imagery.

### Prerequisites and which interpreter does what

Run the commands from the repository root.

- Browser/reference-understanding scripts use the already-installed Playwright/Chromium
  interpreter at `/home/openclaw/.venvs/nt-mirror/bin/python` (the same location as
  `~/.venvs/nt-mirror/bin/python` on the host):
  `capture_assets.py`, `extract_tokens.py`, `inventory_copy.py`, `inventory_components.py`,
  `infer_breakpoints.py`, and the record-only `motion_audit.py` pass.
- The remaining pipeline scripts are Python standard-library tools and run with `python3`:
  `validate_brand_brief.py`, `synthesize_tokens.py`, and `compose_site.py`.
- `validate_site.py` also runs with `python3`, but its browser-backed gates need the Playwright
  venv and its axe/Lighthouse gates need Node.js with `node`/`npx` available. The harness invokes
  axe-core and Lighthouse through `npx`; it owns the local HTTP server lifecycle and never uses
  `file://` validation.
- Step 2 is an inter-profile handoff: `research-agent` produces the brief. The transport is the
  wired research-agent channel/gateway, not an ad-hoc scraper in this repository. The request
  shape is documented in `research/workflow-design.md` §2.1.

Check the browser interpreter and Node tools before a run:

```sh
cd /home/openclaw/Coding/clone-website-wt/feat-web-designer
~/.venvs/nt-mirror/bin/python -c 'import playwright; print("Playwright available")'
node --version
npx --version
```

### Copy-pasteable pipeline walkthrough

The following is a safe scratch rebuild using the committed Pedicel/Linear example inputs. It
writes regenerated outputs under `/tmp`, leaving the checked-in evidence untouched.

#### 1. Understand the reference

The four reference-understanding scripts are independent, deterministic observations of the
reference URL. They write JSON that later steps consume.

```sh
cd /home/openclaw/Coding/clone-website-wt/feat-web-designer

PYBROWSER="$HOME/.venvs/nt-mirror/bin/python"
REF_URL="https://linear.app"
REF_DIR="/tmp/web-designer-reference"
rm -rf "$REF_DIR"
mkdir -p "$REF_DIR/tokens"

"$PYBROWSER" skills/nt-site-mirror/scripts/capture_assets.py \
  "$REF_URL" -o "$REF_DIR/asset-graph.json"
"$PYBROWSER" skills/web-designer/scripts/extract_tokens.py \
  "$REF_URL" -o "$REF_DIR/tokens/"
"$PYBROWSER" skills/web-designer/scripts/inventory_copy.py \
  "$REF_URL" -o "$REF_DIR/copy.json"
"$PYBROWSER" skills/web-designer/scripts/inventory_components.py \
  "$REF_URL" -o "$REF_DIR/components.json"
"$PYBROWSER" skills/web-designer/scripts/infer_breakpoints.py \
  "$REF_URL" -o "$REF_DIR/breakpoints.json"
```

For a reference with meaningful motion, record (do not compare to a mirror at this stage):

```sh
"$PYBROWSER" skills/nt-site-mirror/scripts/motion_audit.py \
  --source-url "$REF_URL" --local-url "$REF_URL" --record-only \
  --out "$REF_DIR/motion" --seconds 12
```

Copy `skills/web-designer/templates/reference-REPORT.md` to
`$REF_DIR/REPORT.md` and fill it from the JSON outputs. A blocked or incomplete observation is
reported as a limitation; it is never filled with guessed sections, copy, or tokens.

The equivalent committed reference-understanding outputs used for this example are:

```text
reports/validation/linear-app/tokens/
reports/validation/linear-app/copy.json
reports/validation/linear-app/components.json
reports/validation/linear-app/breakpoints.json
```

The committed run log at `reports/validation/linear-app/RUN-LOG.txt` records that all four M1
scripts exited 0.

#### 2. Get and validate the brand brief

Send the structured request from `research/workflow-design.md` §2.1 to the wired
`research-agent` profile. Include the brand URL, reference URL/rationale, social handles or
asset paths, and the required deliverable fields. `research-agent` returns both
`brand-brief.json` and `brand-brief.md`.

For the committed worked example, the returned files are:

```text
reports/brand-smoke/brand-brief.json
reports/brand-smoke/brand-brief.md
```

Validate the machine-readable file before any downstream step:

```sh
cd /home/openclaw/Coding/clone-website-wt/feat-web-designer

BRAND_BRIEF="reports/brand-smoke/brand-brief.json"
python3 skills/web-designer/scripts/validate_brand_brief.py \
  "$BRAND_BRIEF" \
  --schema skills/web-designer/scripts/brand_brief_schema.json
```

A valid run prints `VALID <path>`. A non-valid brief is rejected; do not repair it by guessing
brand facts.

#### 3. Synthesize tokens

`synthesize_tokens.py` treats the brand brief's palette and typography as authoritative and uses
the reference token directory for structural scales such as spacing, radius, and shadow.

```sh
cd /home/openclaw/Coding/clone-website-wt/feat-web-designer

REFERENCE_TOKENS="reports/validation/linear-app/tokens"
TOKENS_OUT="/tmp/web-designer-example/tokens"
mkdir -p "$(dirname "$TOKENS_OUT")"

python3 skills/web-designer/scripts/synthesize_tokens.py \
  --brand-brief "$BRAND_BRIEF" \
  --reference-tokens "$REFERENCE_TOKENS" \
  -o "$TOKENS_OUT"
```

The output contains `tokens/json/`, `tokens/dist/tokens.css`,
`tokens/dist/tailwind-tokens.json`, and `tokens/PROVENANCE.md`. The checked-in equivalent is
`reports/m3-token-synthesis/`.

#### 4. Compose the site

`compose_site.py` consumes the validated brief and synthesized tokens and emits a servable
static site. The optional reference report supplies observed copy/component context; it never
licenses or copies reference source code.

```sh
cd /home/openclaw/Coding/clone-website-wt/feat-web-designer

SITE_OUT="/tmp/web-designer-example/site"
python3 skills/web-designer/scripts/compose_site.py \
  --brand-brief "$BRAND_BRIEF" \
  --tokens "$TOKENS_OUT" \
  --reference-report "$REF_DIR" \
  -o "$SITE_OUT"
```

The output contains `index.html`, `tokens.css`, `styles.css`, and `BUILD-REPORT.md`. The checked-in
equivalent is `reports/m3-composed-site/`.

#### 5. Run the 8-gate validation harness

`validate_site.py` starts a local server, exercises the declared route and viewports, runs the
available axe/Lighthouse checks, writes the report, and shuts the server down. It is the final
step; do not claim a tier from a build or an HTTP response alone.

```sh
cd /home/openclaw/Coding/clone-website-wt/feat-web-designer

python3 skills/web-designer/scripts/validate_site.py \
  "$SITE_OUT" -o "/tmp/web-designer-example/validation"
```

To inspect the committed M4 evidence directly (without regenerating it):

```sh
python3 skills/web-designer/scripts/validate_site.py \
  reports/m3-composed-site -o /tmp/web-designer-m4-recheck
```

The default declared viewport widths are `320,768,1024,1440`; use `--routes` and
`--viewports` to expand the declared scope. `--skip-lighthouse` intentionally leaves gates
unexercised and therefore cannot support the same tier as a full run.

### Worked-example result (real measured evidence)

The committed M4 report is the source of truth:

- Report: `reports/m4-validation/validation-report.md`
- Machine-readable results: `reports/m4-validation/gate-results.json`
- Scope: single route `/`, viewports 320, 768, 1024, and 1440.
- Gates: **8/8 PASS**; no gate was `NOT-EXERCISED`.
- axe-core: **0 total violations** in the recorded full run (Gate 3).
- Lighthouse: **100 performance / 100 accessibility / 96 best practices / 100 SEO** (Gate 4).
- Acceptance tier: **`Validated`** for the declared scope.

The report also records the four external references classified as `Kept External` and explains
that gate 8 is the deterministic token-discipline check for this harness. Those are part of the
evidence, not numbers to round away or embellish.

### Honesty and handoff rules

- A blocked source is a documented limitation, never a fabricated brand brief or a stock-photo
  fallback.
- `voice_and_tone.banned_words`, `brand_donts`, empty social arrays, license notes, and research
  limitations are carried forward as constraints.
- A pass must name its evidence basis (`Observed visually`, `Interaction-tested`,
  `DOM+assets confirmed`, `HTTP-200 only`, or `Not exercised`).
- A missing or downgraded feature is a `Fidelity Gap`; the acceptance tier is the one supported by
  the exercised evidence (`First-render`, `Validated`, `Offline-validated`, or `Partial`).
- The phase-2 output is a new site. A single-URL request still goes through
  `skills/nt-site-mirror/` and its mirror manifest/serve contract.

For the full step-by-step contract, limits, and file layout, see
`skills/web-designer/SKILL.md`. The research-agent request/response contract is in
`research/workflow-design.md` §2.1–§2.4.
