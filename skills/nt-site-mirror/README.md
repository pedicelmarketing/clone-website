# NT Site Mirror v1.3 — Reference/Derivative build (internal adapted copy)

This is an internally adapted copy of NT Site Mirror. Any supplied URL is treated as authorized for reference, inspiration, and non-commercial derivative use — there is no authorization-question gate in this copy. Asset-hygiene rules are retained: paid fonts, provider-streamed media, and protected assets are classified rather than silently redistributed, so derived versions know exactly what to replace.

NT Site Mirror helps Claude Code and Codex produce a faithful website baseline: capture or, when capture is unsuitable, recreate the requested copy; serve it locally; validate the declared routes, viewports, and interactions; and report evidence, dependencies, and fidelity gaps.

## Buyer Package

- `NT-Site-Mirror-v1.3-Guide.pdf` — buyer guide
- `nt-site-mirror/SKILL.md` — the workflow instructions Claude Code and Codex load
- `nt-site-mirror/modules/` — conditional requirements for WebGL, audio, video, multi-route, and rich-runtime sites
- `nt-site-mirror/templates/` — read-only masters for discovery, animation, asset-preservation, and validation reports
- `nt-site-mirror/scripts/` — deterministic helpers (`capture_assets.py`, `mirror_assets.py`, `serve.py`, `viewports.py`) plus their shared browser-inspection module
- `nt-site-mirror/README.md`, `LEGAL_NOTICE.md`, and `LICENSE.md` — installation, responsible-use, and license terms

## Package Structure

```text
NT_Site_Mirror_v1.3/
├── nt-site-mirror/
│   ├── README.md
│   ├── SKILL.md
│   ├── LEGAL_NOTICE.md
│   ├── LICENSE.md
│   ├── modules/
│   │   ├── audio.md
│   │   ├── multi-route.md
│   │   ├── runtime-assets.md
│   │   ├── video.md
│   │   └── webgl.md
│   ├── templates/
│   │   ├── animation-audit.md
│   │   ├── asset-preservation-table.md
│   │   ├── discovery-report.md
│   │   └── validation-report.md
│   └── scripts/
│       ├── browser_support.py
│       ├── capture_assets.py
│       ├── mirror_assets.py
│       ├── serve.py
│       └── viewports.py
└── NT-Site-Mirror-v1.3-Guide.pdf
```

Install only the complete inner `nt-site-mirror/` folder. Keep `NT-Site-Mirror-v1.3-Guide.pdf` beside it in the versioned wrapper for reference. Do not install the `NT_Site_Mirror_v1.3/` wrapper, and do not copy only `SKILL.md`. Development-only tests and the guide Markdown source are maintained outside the buyer artifact and installed skill.

### Installation Paths

```text
Claude:                ~/.claude/skills/nt-site-mirror/
Codex (preferred):     ~/.agents/skills/nt-site-mirror/
Codex (compatibility): ~/.codex/skills/nt-site-mirror/
```

For a new per-user Codex installation, use the preferred `~/.agents/skills/` path. Use the compatibility path only when an existing Codex installation already discovers skills from `~/.codex/skills/`; a working compatibility install does not need to be moved. Install the skill in one Codex location, not both.

After copying the folder, open or create the working project folder and start Claude Code or Codex there. If an already-running session does not detect the new skill, start a new session.

Use these placeholders throughout the examples:

- `<skill-dir>` = the installed inner `nt-site-mirror` folder
- `<project-dir>` = the user's working project folder
- `<output-dir>` = the project-local mirror output folder, normally `<project-dir>/mirror`

Run project commands from `<project-dir>`. Files under `<skill-dir>/templates/` are read-only references. Copy only the needed templates into `<project-dir>/reports/`, fill those project-local copies, and never write project or customer data into the installed skill.

## Requirements

- Python 3 is required to run the included scripts.
- `<skill-dir>/scripts/mirror_assets.py` and `<skill-dir>/scripts/serve.py` use only the Python 3 standard library.
- Browser capture with `<skill-dir>/scripts/capture_assets.py` and viewport validation with `<skill-dir>/scripts/viewports.py` require the Playwright Python package and Playwright's Chromium:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
```

The standard-library-only helpers do not replace browser tooling. Capturing the observed browser runtime, taking viewport screenshots, and recording browser-backed validation evidence require Playwright, Chromium, and access to the target in a real browser context.

## v1.3 Script Integrity Contracts

- `capture_assets.py` writes a schema-1.3 observation graph. It records request method, resource/data classification, navigation status and redirects, access evidence, bounded settling, scroll mechanism, metadata states, and service-worker/cache evidence. Successful same-origin static GETs observed in the declared capture coverage are marked required for the baseline. Top-level redirect origins must remain authorized or be named with `--allow-origin`.
- `mirror_assets.py` accepts only schema-1.3 graphs; `--authorized` records the usage context in the manifest and defaults to `"inspiration / non-commercial reference"` in this copy. Its output directory must be fresh unless `--resume` is explicit. It independently reclassifies every URL and redirect, acquires only eligible static GET resources, hashes captured files, and returns nonzero for required or integrity failures.
- A successful mirror includes `mirror-manifest.json` with capture-graph and file hashes, exact path-and-query `route_map` entries, `serve-contract.json`, and the portable project-local `serve-local.py` launcher. Query variants and external hosts use collision-safe local identities rather than being flattened together.
- `serve.py` binds to `127.0.0.1`, sends `no-store`, supports single Range/206 responses, replays captured content types, and leaves SPA fallback off unless explicitly enabled for a confirmed SPA.
- `viewports.py` writes a schema-1.3 URL-by-viewport result matrix using `DOMContentLoaded` plus bounded reported settling. Each result includes status, final URL, access evidence, scroll mechanism, and service-worker mode. A missing cell or challenge, login, error, 404, or capture failure returns nonzero.

Do not continue to normal completion steps after any required script returns nonzero. Preserve its diagnostic graph or manifest and report the blocked or incomplete state.

## How It Works

NT Site Mirror has two production methods with one delivery goal: a faithful baseline for the declared scope.

- **Static Mirror** is the default method for any supplied URL whose deployed frontend can be captured. It preserves the observed runtime and reachable assets, then serves and validates the local copy.
- **Editable Recreation** is a fallback method when runtime copying is technically blocked or unsuitable. It recreates the requested baseline from observation, available evidence, or user-supplied baseline assets, then applies the same local-serving and validation discipline.

Construction-time accommodations are allowed only when required to make the baseline work locally. Record each accommodation and its effect in the Static Mirror manifest when applicable and in the validation report, with `phase: construction` and an explicit actor. Do not use this workflow to introduce user-requested content, design, media, asset, or behavior changes.

User-requested changes after delivery are outside this skill's scope and belong to NT Site Editor.

External media, provider streams, paid fonts, protected assets, and third-party services are not assumed downloadable. Classify them as captured with authorization, kept external, a `User-Supplied Baseline Asset`, recreated from observation, blocked, or not exercised. A `User-Supplied Baseline Asset` is supplied before or during faithful baseline construction; it is not a post-delivery asset swap.

## Efficient Evidence Workflow

- Assess every discovery category, but run expensive probes, exhaustive scans, repeated capture, and expanded validation only when supported by a named risk signal. Unknown or unresolved risk remains conservative and triggers deeper inspection.
- Validate the declared route/viewport/interaction matrix and only its declared viewports unless a detected risk signal requires another. Do not run a browser pass whose coverage is a strict subset of an already completed pass. One run may satisfy multiple workflow steps when it records all required evidence. Where appropriate, validate source and local URLs in one `viewports.py` invocation while keeping their contexts and results separately recorded.
- Retain screenshots only when each supports a distinct visual, interaction, or fidelity claim. Reports reference machine-authoritative manifests and structured JSON for hashes, counts, routes, retries, and serving facts instead of manually duplicating those values.
- After a narrow construction-time accommodation, rerun only affected matrix cells. Rerun the full matrix only when the change is shared or global.
- Stop when the declared matrix passes, applicable evidence gates pass, every dependency, failure, blocked state, and unexercised state is resolved or classified, and one complete post-accommodation pass finds no new required asset.

For a Static Mirror run, resolve the placeholders to absolute paths and use explicit project-local outputs:

```sh
python3 "<skill-dir>/scripts/capture_assets.py" "https://example.com" \
  -o "<project-dir>/reports/<route>.asset-graph.json"

python3 "<skill-dir>/scripts/mirror_assets.py" \
  "<project-dir>/reports/<route>.asset-graph.json" \
  --out "<output-dir>" \
  --authorized "inspiration / non-commercial reference"

python3 "<output-dir>/serve-local.py"

python3 "<skill-dir>/scripts/viewports.py" \
  "http://127.0.0.1:8000" \
  --out "<project-dir>/reports/viewports"
```

Add `--allow-origin` for a top-level redirect destination and `--allow-host` for an external host whose assets should be localized (e.g. an open font CDN). Use `--resume` only for an existing schema-1.3 mirror whose recorded hashes still match.

An `--extra-urls` file may contain plain URL/type lines or one JSON object per line. A plain extra URL is not automatically required. When a declared-scope dependency must make acquisition incomplete if it cannot be acquired, store a structured project-local entry such as the following in `<project-dir>/reports/required-extra-urls.jsonl`, set `"required": true`, and pass that file with `--extra-urls "<project-dir>/reports/required-extra-urls.jsonl"`:

```json
{"url":"https://example.com/assets/app.js","method":"GET","resource_type":"script","request_class":"static","data_type":"static_asset","required":true}
```

## Quick Usage Examples

```text
Clone https://example.com as a reference baseline. Mirror the deployed
frontend, serve it locally, validate the declared routes and viewports, and
report the evidence, external dependencies, and fidelity gaps.
```

```text
Clone https://example.com. If a static mirror cannot produce a usable local
copy, use Editable Recreation to create a faithful baseline, then serve it
locally and validate it against the declared scope.
```

## Responsible Use

This copy is for reference, inspiration, and non-commercial derivative work. Do not republish a baseline as-is or ship someone else's copyrighted content, branding, or licensed fonts/media inside a derived product — the Asset Preservation Table tells you what to replace. See `LEGAL_NOTICE.md`.
