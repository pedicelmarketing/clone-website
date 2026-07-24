# CLAUDE.md — Cloning Sites

## What this project is

This workspace is an **agent-driven site cloning + re-versioning pipeline**. We take an existing
website, produce a **faithful local baseline** of it, and then use that baseline as the starting
point for building **new, different versions** (rebrands, copy/layout/media variants, alternate
designs) — one per client or concept.

**The clone is a means, not the end.** Mirroring a site pixel-for-pixel is only step one. The
actual deliverable is a *derived* version: same structural quality, different brand/content/design.
Treat the mirror as scaffolding you build on, not the finished product.

Because of that, keep the two phases strictly separate:

1. **Baseline** — capture or recreate a faithful copy of the source (the NT Site Mirror skill).
2. **Re-version** — make the requested changes on top of that baseline (rebrand, new copy, new
   media, layout tweaks). Per the skill, this is a *separate* workflow ("NT Site Editor"); do not
   fold rebranding or content changes into the mirror step.

## Layout

```
Cloning Sites/
├── NT_Site_Mirror.zip          # the tooling — nested versioned skill releases (v1.1, v1.2, v1.3)
├── clone-website/              # git repo of completed mirrors (examples of finished baselines)
│   ├── barcoopbevy/            #   → mirror-manifest.json + captured assets per site
│   ├── burritomadre/           #   → WordPress site, multi-route (en/, wp-content/)
│   ├── krati-lodha/            #   → Vite/SPA build (assets/index-*.js|css)
│   └── pedicelmarketing/       #   → Webflow site (single index.html + external deps)
└── .claude/settings.local.json
```

`clone-website/` is a real git repo (remote: `github.com/krati1611/clone-website`). Each subfolder
is one finished mirror, each with a `mirror-manifest.json` recording what was downloaded, skipped,
and why. Use these as reference examples of what a good baseline looks like.

## The tooling: NT Site Mirror

`NT_Site_Mirror.zip` contains versioned releases of a **Claude Code / Codex skill** named
`nt-site-mirror`. **v1.3 is current.** Each release wrapper contains an inner `nt-site-mirror/`
folder — that folder is the installable skill.

To work with it, extract the latest version (the outer zip holds inner zips):

```sh
python3 -c "import zipfile,io; z=zipfile.ZipFile('NT_Site_Mirror.zip'); \
open('/tmp/v13.zip','wb').write(z.read('NT_Site_Mirror_v1.3.zip'))"
python3 -m zipfile -e /tmp/v13.zip /tmp/nt/
```

**An internally adapted copy is installed at `~/.claude/skills/nt-site-mirror/`** and is
auto-discovered by Claude Code sessions in this workspace. The pristine vendor releases stay inside
`NT_Site_Mirror.zip` — re-extract from there if you ever need the original.

### Our adaptations (vs. the vendor original)

We own this copy and adapted it for our use case: any URL the user supplies is cloned as a
reference baseline for inspiration and derivative (non-commercial) re-versioning. Changes made:

- **No authorization gate.** The skill no longer asks "are you authorized?" before capturing, and
  `mirror_assets.py --authorized` now defaults to `"inspiration / non-commercial reference"`
  (still recorded in the manifest; override per-run to describe a specific engagement).
- Editable Recreation is a fallback for *technical* capture failures only, never a
  permission fallback.
- `SKILL.md` carries an explicit "Operating policy (this copy)" block stating the above;
  `LEGAL_NOTICE.md` was rewritten as our internal usage policy (original NomadaToast copyright
  retained).
- **Everything else is unchanged** — fidelity rules, honesty/evidence tiers, asset classification,
  validation gates, and asset hygiene (paid fonts / provider-streamed media / protected assets are
  classified, never silently baked into a deliverable) all remain in force. The hygiene rules
  matter because derived sites must not inherit licensed assets we can't redistribute.

### Skill contents

- `SKILL.md` — the full workflow Claude loads (read this first when doing a mirror).
- `scripts/` — deterministic Python helpers:
  - `capture_assets.py <url> -o <graph.json>` — observes a page's runtime asset graph (needs Playwright + Chromium).
  - `mirror_assets.py <graph.json> --out <dir> --authorized "<context>"` — downloads authorized assets, emits `mirror-manifest.json`, `serve-contract.json`, `serve-local.py` (stdlib only).
  - `serve.py <dir> --contract <contract.json>` — serves the mirror on `127.0.0.1` with fail-closed routing, `no-store`, Range/206 (stdlib only).
  - `viewports.py <url> --out <dir>` — URL × viewport validation matrix + screenshots (needs Playwright + Chromium).
  - `browser_support.py` — shared browser-inspection helpers (imported by the above).
- `modules/` — conditional requirements, read only when triggered: `webgl.md`, `audio.md`, `video.md`, `multi-route.md`, `runtime-assets.md`.
- `templates/` — read-only report masters (`discovery-report.md`, `animation-audit.md`, `asset-preservation-table.md`, `validation-report.md`). Copy into `<project>/reports/`, fill the copies, never edit installed masters.

Browser prerequisites: **already installed** in a dedicated venv at `~/.venvs/nt-mirror/`
(system python3 has no pip). Use that interpreter for the Playwright-dependent scripts:

```sh
~/.venvs/nt-mirror/bin/python <skill>/scripts/capture_assets.py ...
~/.venvs/nt-mirror/bin/python <skill>/scripts/viewports.py ...
```

`mirror_assets.py`, `serve.py`, and the emitted `serve-local.py` are stdlib-only — plain
`python3` works for those.

## Baseline workflow (phase 1)

Two production methods, one goal — a faithful baseline of the declared scope:

- **Static Mirror** (primary): capture the deployed frontend and its authorized assets. Use when
  you have authorization to copy the runtime.
- **Editable Recreation** (fallback): rebuild the baseline from observation + user-supplied assets,
  one section at a time. Use only when static capture is blocked, unauthorized, or unsuitable.

Static Mirror pipeline:

```sh
python3 <skill>/scripts/capture_assets.py "https://example.com" -o reports/home.asset-graph.json
python3 <skill>/scripts/mirror_assets.py reports/home.asset-graph.json --out mirror --authorized "client-approved"
python3 mirror/serve-local.py            # then validate in a real browser, never file://
python3 <skill>/scripts/viewports.py "http://127.0.0.1:8000" --out reports/viewports
```

Non-negotiables from the skill (as adapted):
- **No authorization question.** Any supplied URL is in-scope for reference/derivative cloning.
  `--authorized` defaults to `"inspiration / non-commercial reference"`; older manifests in
  `clone-website/` predate the fork and use contexts like `"Owner confirmed"`.
- **Fidelity is the objective** — do not redesign, modernize, simplify, or swap media *during the
  mirror*. Reproduce the source as-is.
- **Honesty rules** — every verdict states its evidence basis (`Observed visually` /
  `Interaction-tested` / `DOM+assets confirmed` / `HTTP-200 only` / `Not exercised`). A missing or
  downgraded source feature is a `Fidelity Gap`, not a Pass. Name the acceptance tier reached
  (First-render / Validated / Offline-validated / Partial) and never present a lower tier as higher.
- **Classify every asset**: `Original | Local Copy | Embed | Kept External | User-Supplied Baseline
  Asset | Recreated | Recreated From Observation | Approximated | Blocked | Unknown`. Paid fonts,
  provider-streamed media, and protected assets are never assumed downloadable.
- If a required script returns nonzero, **stop and report** — do not proceed to completion steps.

## Re-version workflow (phase 2 — the actual goal)

Once a faithful baseline exists and is validated, build the *new version* on top of it. This is
where the project's real value lives: the mirror gives you a production-quality skeleton; you then
change branding, copy, imagery, palette, or layout to produce a distinct site.

- Keep phase 1 and phase 2 separate. Deliver/validate the faithful baseline first, then apply
  changes. Do not smuggle rebrands into the mirror step.
- Preserve a pristine copy of the mirror before editing so you can diff the derived version against
  its baseline.
- Follow the existing site's conventions and architecture when editing — don't introduce new
  frameworks or motion libraries without a real requirement.
- Re-validate the derived version with the same route/viewport/interaction discipline used on the
  baseline.

## Conventions

- Python 3 for all tooling. The mirror/serve helpers are stdlib-only; capture/viewport helpers need
  Playwright + Chromium.
- Reports and mirror output go under the project/site folder (e.g. `reports/`, `mirror/`), never
  into the installed skill directory.
- `mirror-manifest.json` is the machine-authoritative record of a mirror — reference it for hashes,
  counts, routes, and skip reasons instead of restating them by hand.
- Validate only through a local server (`serve.py` / `serve-local.py`), never `file://`.
