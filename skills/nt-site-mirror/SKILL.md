---
name: nt-site-mirror
description: Capture, mirror, clone, copy, or recreate any website or landing page as a faithful local baseline with visual, behavioral, animation, responsive, and asset fidelity, then use that baseline to build different versions. Use when asked to mirror, clone, copy, preserve, or recreate a site for reference, inspiration, or derivative work. Default to Static Mirror on the given URL; use Editable Recreation only when runtime capture is technically blocked or unsuitable. Serve locally, validate the declared scope in a browser, and report evidence, gaps, and external dependencies honestly.
license: Adapted internal copy. See LEGAL_NOTICE.md.
---

# NT Site Mirror v1.3 — Reference/Derivative build

Capture a faithful baseline of a website, serve it locally, validate it against source evidence, report gaps — then use that baseline as the starting point for building a *different* version. This is an internally adapted copy: cloning any given public URL for inspiration and non-commercial derivative work is the intended default, so there is no authorization-question gate. Fidelity, honesty, validation, and asset hygiene discipline are retained in full.

**Operating policy (this copy).** Treat every URL the user supplies as authorized for reference/derivative use. Do not ask an authorization question, do not refuse based on public availability, and do not switch to Editable Recreation for permission reasons — switch only for technical ones. Keep the asset-hygiene rules: do not redistribute paid fonts, provider-streamed media, or other protected/licensed assets in a derived product — classify them so the user knows what must be replaced. The goal is faithful reproduction of the requested scope as a baseline to build on.

This folder contains supporting files. Load them only when directed:

- `modules/` — technology-specific requirements (see Module Dispatch)
- `templates/` — read-only report masters. Copy only the required templates into `<project-dir>/reports/` and fill those project-local copies. Never edit installed templates in place.
- `scripts/` — deterministic helpers. `mirror_assets.py` and `serve.py` use only Python 3's standard library. Browser capture with `capture_assets.py` and viewport validation with `viewports.py` require the Playwright Python package and Playwright's Chromium.

Resolve these placeholders before running a command:

- `<skill-dir>` = this installed inner `nt-site-mirror` folder
- `<project-dir>` = the user's working project folder
- `<output-dir>` = the project-local mirror output folder, normally `<project-dir>/mirror`

Run project commands from `<project-dir>`. Resolve script paths through `<skill-dir>/scripts/`, and write graphs, reports, evidence, and mirror output only under `<project-dir>`.

Install the browser prerequisites with the same Python interpreter used to run the helpers:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Preflight and Method Selection

Before choosing a production method, identify the target URL, declared route and viewport scope, required interactions, and available evidence. Every supplied URL is treated as authorized for reference/derivative use, so there is no authorization question — go straight to method selection.

- **Static Mirror Mode** — preserve the deployed frontend runtime and reachable same-origin assets. This is the default for any given URL.
- **Editable Recreation Mode** — recreate the requested baseline from observation and user-supplied or otherwise available assets. Use only as the fallback when Static Mirror Mode cannot *technically* produce the copy (runtime capture is blocked by the site, or is technically unsuitable). Never switch for permission reasons.

Rules:

- Default to Static Mirror on the given URL; do not ask for permission and do not refuse based on public availability.
- Keep asset hygiene: paid fonts, provider-streamed media, and other protected/licensed assets are not redistributed inside a derived product — classify them so the user can replace them. This is about clean derivative output, not permission.
- When the user asks for exact behavior or preserved interactions, attempt a Static Mirror first. Never promise that a deployed-runtime copy is recovered clean source.
- Once scope is clear, proceed through discovery, production, local serving, validation, and gap reporting without adding a separate implementation-approval gate.

## Asset Classification (canonical — referenced by every module)

No asset is automatically downloadable — especially paid fonts, provider-streamed media, external media, and protected assets. Classify every major asset as exactly one of:

`Original` | `Local Copy` | `Embed` | `Kept External` | `User-Supplied Baseline Asset` | `Recreated` | `Recreated From Observation` | `Approximated` | `Blocked` | `Unknown`

`User-Supplied Baseline Asset` means an asset the user supplies before or during faithful baseline construction because the observed asset cannot be acquired or used lawfully. It is not a post-delivery asset swap. Local download is allowed only when authorized, licensed, and technically permitted. For each major asset record the source URL or code path, chosen status, and why alternatives were rejected in `<project-dir>/reports/asset-preservation-table.md`.

## Core Fidelity Rules

- Fidelity — visual, behavioral, animation, responsive, asset — is the primary objective.
- Produce only the faithful baseline. Do not redesign, modernize, simplify, invent layouts, replace animations, change branding, or change media selection.
- Never silently replace, disable, freeze, remove, or downgrade a major source feature. Treat visible motion, media, and audio as fidelity assets.
- Prefer observable evidence over assumption. Never invent files, components, routes, libraries, or assets; mark anything unverified as Unknown.
- Record discovery findings before acquisition or recreation. Do not write implementation code during Discovery.
- Editable Recreation Mode: build one section at a time, never the whole site in one pass.

## Honesty Rules

- **Fidelity Gap Rule** — if an in-scope visible or audible source feature is absent, frozen, disabled, broken, replaced, or substantially downgraded in the result: document a `Fidelity Gap`, state the affected scope and evidence, and do not mark that system Pass. User acknowledgement changes the status to `Accepted Exception`, not Pass.
- **Approval Gate** — when a major feature requires approximation: fill the Asset Preservation Table, explain the fidelity impact, present the options (Preserve / Extract / Recreate / Approximate), and wait for user approval before implementing the approximation. In Static Mirror Mode, attempt preservation BEFORE asking to approximate — never ask to approximate WebGL/canvas effects before attempting authorized preservation.
- **Completion Integrity** — compiling is not validation. Claim only the tier supported by the declared routes, viewports, interactions, and evidence actually exercised. If that coverage does not pass, report `Partial`, separating Passed / Blocked / Approximated / Not Exercised / Out of Scope. Never describe an approximation as a recreation or extrapolate a narrow check into a whole-site claim.
- **Fidelity Escalation** — when a feature cannot be recreated with high confidence: stop that feature, name the blocking technology, state what evidence or access is missing, list the available paths, and continue unrelated sections. Never silently approximate.
- **Verification-Method Honesty** — every per-system verdict states its basis: `Observed visually` / `Interaction-tested` / `DOM+assets confirmed` / `HTTP-200 only` / `Not exercised`. "Assets verified" and "behavior verified" are different claims; a Pass backed only by HTTP 200s must say so.

## Evidence Priority

1. User-provided screen recordings
2. User-provided screenshots
3. Live website
4. Source inspection

Higher priority wins; call out conflicts in Risks. Separate all findings into **Facts** (observed), **Assumptions** (unverified), **Unknowns** (need investigation).

## Shared Discovery

Copy the required report masters into `<project-dir>/reports/` before filling them.

1. Fill the project-local `discovery-report.md` with the declared Scope Classification (`Hero Only` | `Homepage` | `Landing Page` | `Multi-Route Site` | `Portfolio Site` | `Application`), evidence sources, link and route inventory, source-module inventory in source order, asset inventory, and Module Trigger Scan. Measure typography, color, spacing, and breakpoints only to the depth needed to capture or recreate the declared scope faithfully.
2. Fill the project-local `animation-audit.md` only when meaningful motion exists. Record observed behavior and label estimated timings as estimates.
3. Fill the project-local `asset-preservation-table.md` for major assets and all blocked, external, approximated, or recreated assets.
4. Select Static Mirror Mode or the Editable Recreation fallback from the preflight evidence. Record why the chosen method is lawful and suitable.

## Static Mirror Workflow

This is the default workflow for any supplied URL. No stated authorization is required in this copy.

1. Run `python3 "<skill-dir>/scripts/capture_assets.py" "<url>" -o "<project-dir>/reports/<route>.asset-graph.json"` for every in-scope route and exercise the declared interactions that can reveal runtime assets. The schema-1.3 graph must record navigation status/final URL, redirects, access evidence, request method and classification, required same-origin static GETs within the exercised coverage, metadata states, scroll mechanism, and service-worker/cache evidence. Add `--allow-origin` only for an explicitly authorized top-level redirect origin.
2. Run `python3 "<skill-dir>/scripts/mirror_assets.py" "<project-dir>/reports/<route>.asset-graph.json" --out "<output-dir>" --authorized "<user-stated context>"` to acquire authorized assets through the schema-1.3 manifest pipeline. Add more project-local graph paths when the scope has multiple routes. Use a fresh output directory unless `--resume` is explicit, and add `--allow-host` only for an expressly authorized external host. Stop and report if the script returns nonzero; do not print or perform normal completion steps after a required failure.
3. On success, serve through the emitted `python3 "<output-dir>/serve-local.py"` launcher, or run `python3 "<skill-dir>/scripts/serve.py" "<output-dir>" --contract "<output-dir>/serve-contract.json"`; never validate through `file://`. SPA fallback stays off unless a true SPA has been confirmed and the serving contract names its safe entry.
4. Run Deep Static Mirror Discovery, resolve or classify every mirror-introduced missing dependency, and repeat capture and validation only when a named risk signal requires it and only until the stop condition is met. Run `python3 "<skill-dir>/scripts/viewports.py" "<local-url>" --out "<project-dir>/reports/viewports"` for the declared URL × viewport matrix; each required result must record status, final URL, access evidence, scroll mechanism, and service-worker mode.
5. Permit only minimal construction-time accommodations required for the faithful baseline to boot or operate locally, such as local path/origin resolution, route configuration, serving shims, or a deterministic telemetry no-op. Record shipped generated files in `generated_artifacts` and `construction_provenance`; record changes to captured/project files in `local_modifications`. Every accommodation entry declares `phase: construction`, an explicit `actor`, its file, reason, before/after description when applicable, and validation evidence. Preserve a pristine downloaded copy and make the accommodation reproducible. An empty `local_modifications` list means no modifications were declared; it is not proof of byte identity.
6. Do not use accommodations to change copy, branding, layout, media selection, content, or intended product behavior. If local operation would require broad source or bundle changes, report the limitation and use Editable Recreation only if it can faithfully produce the requested baseline.

For `Multi-Route Site`, `Portfolio Site`, or `Application` scope, capture each in-scope reachable route separately, preserve each route's HTML/path, and do not overwrite route-specific HTML unless evidence confirms a true SPA shell. A homepage-only capture supports only a homepage claim.

## Editable Recreation Workflow

Use Editable Recreation only after documenting why Static Mirror Mode cannot *technically* produce the requested copy (capture blocked by the site, or technically unsuitable).

1. Recreate from source observation, user-provided evidence, and user-supplied baseline assets or other approved assets. Do not copy proprietary deployed source or protected assets.
2. Reproduce the declared baseline in source order, one section at a time. Compare typography, spacing, layout, responsive behavior, motion, media, and interactions against evidence before moving to the next section.
3. Follow an existing repository's conventions and architecture. For a new project, choose the smallest suitable stack; do not add a framework or motion library without a fidelity requirement.
4. Apply Fidelity Escalation to blocked features and keep unrelated in-scope sections moving. Do not reinterpret the design to hide a gap.
5. Serve the recreation locally through its documented project command and validate the same declared route, viewport, and interaction coverage used for the source.

## Shared Validation and Delivery

1. Fill the project-local `validation-report.md`.
2. Run `python3 "<skill-dir>/scripts/viewports.py" "<local-url>" --out "<project-dir>/reports/viewports"` where applicable at the declared target viewports and exercise in-scope scroll, hover, transitions, loading states, navigation, and every active module's relevant checks. Where appropriate, include source and local URLs in one invocation while keeping each URL's context and results separately recorded. Validate only declared viewports unless a detected named risk signal requires another viewport.
3. Do not run a browser pass whose coverage is a strict subset of an already completed pass. One browser run may satisfy multiple workflow steps when it records all required evidence. Retain screenshots only when each supports a distinct visual, interaction, or fidelity claim.
4. State each verdict as `Pass for declared evidence`, `Partial`, `Fidelity Gap`, `Accepted exception`, `Blocked`, `Not exercised`, or `Out of scope`, and include its verification method. Acknowledge the difference between visual observation, interaction testing, DOM/assets confirmation, and HTTP-only evidence.
5. Report the exact local serve command, web root, port, required accommodations, external dependencies, and the acceptance tier supported by the evidence. For hashes, counts, routes, retries, and serving facts, reference the machine-authoritative manifests and structured JSON instead of manually duplicating those values.

After delivering the faithful baseline, hand every user-requested change — including rebrands, copy or layout changes, media swaps, asset replacement, source tracing, edit plans, patch logs, and bundle changes — to **NT Site Editor**. Do not merge the two workflows.

## Module Dispatch

During Discovery, run a mandatory trigger scan. Read a module file only when its trigger is detected or reasonably suspected. If a feature is suspected but unverified, mark it Unknown and read the module to investigate — never assume absence. Inactive modules add no requirements.

| Trigger detected or suspected | Read |
| --- | --- |
| WebGL, Three.js, R3F, canvas scenes, GLSL/shaders, 3D, GLB/GLTF, Draco | `modules/webgl.md` |
| Background music, ambient/UI sounds, Web Audio API, mute/volume controls | `modules/audio.md` |
| Video files, provider-hosted/CDN/background/scroll-linked video | `modules/video.md` |
| Multiple routes, detail pages, app screens, shared/nested layouts, CMS collections | `modules/multi-route.md` |
| Dynamic imports, lazy chunks, runtime-loaded assets, late-loading media | `modules/runtime-assets.md` |

## Conditional Rule Activation

The declared-scope evidence gates (see Deep Static Mirror Discovery) always apply to Static Mirror deliveries. The heavier checks below activate only when their signals are detected — a simple static page pays none of them.

- **Rich runtime** — signals: three.js/WebGL/canvas, `.glb`/`.gltf`, Draco, `.wasm`, `.hdr`/`.exr`, scroll-choreography or virtual-scroll libraries, audio/AudioContext, shaders, workers, `blob:` URLs, root-absolute build assets. Activates deep behavioral validation: exercise entry gates, wheel/scroll-driven sections, WebGL render state, and audio toggles, and report which interactions were and were not exercised. If body scrollHeight ≈ viewport height with overflow hidden, native scrolling is dead — drive the page with real wheel events and record the mechanism used. Probe origin media with `curl -r 0-1023`; if the origin answers `206`, local validation and serving must too (`<skill-dir>/scripts/serve.py` does). Worker-initiated fetches are invisible to page-level network logs — absence of observed requests is not absence of involvement.
- **Builder-hosted runtime** — signals: site-builder generator meta tags, builder runtime container IDs, characteristic builder CDN hosts. Determine whether an authorized Static Mirror can preserve the requested baseline; otherwise use the Editable Recreation fallback. Builder runtimes may require query-string-aware resource handling: if one URL path returns different bodies for different query strings, capture every observed in-scope variant and declare the routing need in the serving contract. Unexpected 404s on previously captured paths in later passes can indicate that the live site deployed a new version; verify before attributing corruption.
- **Analytics/tracking** — signals: tag managers, heatmaps, ad/social pixels, and platform-injected first-party analytics at hashed paths. Telemetry failures are not fidelity failures. Do not replay live tracking as part of a local baseline. If a telemetry call blocks local operation, use only a deterministic construction-time no-op and record it in manifest provenance.
- **Construction-time accommodation** — signal: a captured file or local serving configuration must change for the faithful baseline to boot or operate locally. Keep the change minimal and reproducible, preserve the original, append its provenance to `mirror-manifest.json.local_modifications`, and re-run the affected declared-scope evidence gates under the accommodation rule below. Never use this mechanism for user-requested content, brand, media, layout, or behavior changes.

## Static Mirror Mode Specifics

- Pipeline: `python3 "<skill-dir>/scripts/capture_assets.py" "<url>" -o "<project-dir>/reports/<route>.asset-graph.json"` (build a schema-1.3 observed runtime graph from declared interactions, including scroll-triggered loads when exercised) → `python3 "<skill-dir>/scripts/mirror_assets.py" "<project-dir>/reports/<route>.asset-graph.json" --out "<output-dir>" --authorized "<user-stated context>"` (independently authorize and classify eligible static GET resources, store them with collision-safe URL identity, hash them, and emit `mirror-manifest.json`, `serve-contract.json`, and `serve-local.py`) → run `python3 "<output-dir>/serve-local.py"` → validate.
- The mirror script refuses to run without the user's authorization context and never downloads blocked/protected provider assets; openly licensed fonts may be localized only when authorization/licensing allows (via explicit `--allow-host`). Its `skipped` lists feed the Asset Preservation Table — every entry gets a status.
- Use `--allow-host` only for external hosts the user explicitly confirmed are licensed/authorized (e.g. the client's own CDN).
- `mirror-manifest.json` schema 1.3 records hashed capture-graph provenance, pages, exact path-and-query `route_map` entries, full source URL mappings, downloaded hashes, probes, failures, metadata states, authorization contexts, attempts, generated artifacts, and declared construction-time provenance. It preserves `local_modifications` on a verified `--resume`. Route every supplementary or manually declared URL acquisition through the pipeline with `--extra-urls "<project-dir>/reports/extra-urls.jsonl"`, never side channels, so the available audit trail stays coherent. A plain extra URL is not automatically required. When a declared-scope dependency must make acquisition incomplete if it cannot be acquired, use one JSON object per line and set `"required": true`, for example `{"url":"https://example.com/assets/app.js","method":"GET","resource_type":"script","request_class":"static","data_type":"static_asset","required":true}`.
- Do not manually rebuild sections before attempting the mirror. Fall back to Editable Recreation only if mirroring is technically blocked or impossible.
- Keep the mirror minimal: no refactoring, redesign, framework conversion, or generalized source/bundle modification.
- The first-load pipeline above is the floor, not the finish. Do not claim declared-scope validation until Deep Static Mirror Discovery has passed for that scope.

## Deep Static Mirror Discovery (mandatory before a declared-scope validation claim)

First-load network logs are not sufficient evidence for a declared-scope validation claim — especially for WebGL, game-like, Vite/SPA, and lazy-loading sites, where critical assets load only after interaction. Assess every discovery category for the declared routes, viewports, and interactions. Run an expensive probe, exhaustive scan, repeated capture, or expanded validation only when supported by a named risk signal. An Unknown or unresolved risk remains conservative and triggers deeper inspection. Record the assessment for all five categories below even when no deeper work is activated. Authorization, licensing, and Asset Classification rules govern every download in every step.

1. **Source/repo discovery.** Source repos, source maps, exposed build artifacts, and manifests may be inspected for route and asset coverage checks — not for copying proprietary source code or protected assets into a deliverable. Inspect the live page for links to source repos. When a named source/repo or route-coverage risk signal supports deeper inspection, probe these candidate URLs on the origin to verify routes and assets: `/manifest.webmanifest`, `/sitemap.xml`, `/robots.txt`, `/asset-manifest.json`, `/.vite/manifest.json`, `/_next/build-manifest.json`, `/package.json`. Warning: SPA servers often return `200` + `index.html` for missing paths — verify content type and body before treating any probe result as a real manifest or `package.json`. Discovery via a repo, manifest, or source map does not by itself authorize copying any of its contents; the Asset Classification and authorization rules govern every download.
2. **Multi-pass asset capture.** Capture asset references from HTML, CSS, JS bundles, manifest files, browser network logs (`<skill-dir>/scripts/capture_assets.py`), and the declared runtime interactions. Where source maps are available in an authorized context, use them only to verify asset references and route coverage — not to reconstruct or copy proprietary source code. When a named runtime-asset risk signal supports deeper inspection, scan downloaded JS bundles by searching for these concrete patterns: `import(`, `new Worker`, `new URL(`, `import.meta.url`, `fetch(`, and the extensions `.wasm`, `.glb`, `.gltf`, `.ktx`, `.ktx2`, `.hdr`, `.exr`, `.drc`, `.bin`, `.mp3`, `.ogg`, `.woff`, `.woff2`. These surface dynamic imports, lazy chunks, WASM, workers, decoder/transcoder files (e.g. Draco, Basis/KTX2, Meshopt), models, textures, audio, and fonts. Resolve hits against the origin, confirm they exist, and feed confirmed URLs to `python3 "<skill-dir>/scripts/mirror_assets.py" "<project-dir>/reports/<route>.asset-graph.json" --out "<output-dir>" --authorized "<user-stated context>" --extra-urls "<project-dir>/reports/extra-urls.jsonl"` (same authorization and classification gates apply). Never rely only on first-load page requests.
3. **Runtime exploration.** Serve the mirror locally with `python3 "<output-dir>/serve-local.py"` or `python3 "<skill-dir>/scripts/serve.py" "<output-dir>" --contract "<output-dir>/serve-contract.json"`, and drive it in a browser beyond the first render across the declared interaction set: click relevant entry buttons, open in-scope menus and modals, scroll, hover, navigate declared routes, and perform the relevant app/game interactions. During local interaction testing, use the local server's 404 logs as evidence of missing local assets. Resolve missing paths against the original source origin before passing them through the project-local `--extra-urls` inventory, then download subject to classification or record the gap. Repeat until the declared interaction set stops surfacing unresolved mirror-introduced files.
4. **External dependency classification.** Localize openly licensed font providers when authorization and licensing allow, classify them as `Local Copy`, and record any necessary construction-time URL accommodation. Paid or protected font providers remain never-downloadable. Do not replay live analytics or tracking; use a deterministic no-op only when necessary for local operation and record it in manifest provenance. Classify every remaining external request as required, approved fallback, telemetry, blocked, or unresolved.
5. **Validation.** Verify through a local server, never `file://`. Record console errors, failed network requests, missing assets, and references to the original source host. Localize authorized same-origin references only when required for local operation, record the accommodation, or document the dependency. Capture the live error/behavior baseline before mirroring and count only mirror-introduced failures. Run `python3 "<skill-dir>/scripts/viewports.py" "<local-url>" --out "<project-dir>/reports/viewports"` at the declared target sizes and exercise actual interactions for interactive/WebGL/game sites. Report asset count, folder size, missing files, external dependencies, fallbacks, unexercised states, and the **serving contract**: exact serve command, web root, port, why `file://` is unsupported, and every required accommodation. Make every validation claim conditional on this named scope and serving setup.

**Declared-scope evidence gates.** A rendered homepage alone supports only a first-render claim. After a narrow construction-time accommodation, rerun only the affected matrix cells and applicable gates. Rerun the full matrix only when the change is shared or global:

1. **Boot gate** — the mirror boots locally through one documented project command/config, exercised end to end through the same channel the user will use.
2. **Dependency gate** — during the declared route and interaction coverage, no unresolved mirror-introduced local 4xx or page errors remain and every external request is classified. Claim offline validation only after a separate run with external network blocked resolves locally without unexpected external requests.
3. **Experience gate, when applicable** — each in-scope entry gate, preloader, or progress screen is observed reaching its terminal usable state, with the trajectory recorded. A frozen determinate progress indicator is a Fidelity Gap, not a presumed timing artifact.

**Stop condition.** Stop discovery, capture, and validation when all of the following are true:

- the declared route/viewport/interaction matrix passes;
- the applicable evidence gates pass;
- every dependency, failure, blocked state, and unexercised state is resolved or classified; and
- one complete post-accommodation pass finds no new required asset.

## Static Mirror Acceptance Tiers

Name the tier reached in every Static Mirror report; never present a lower tier as a higher one.

- **First-render mirror** — an in-scope page renders locally from first-load capture. Interactions, lazy chunks, and runtime assets remain unverified.
- **Validated static mirror — declared scope** — Deep Static Mirror Discovery and all applicable evidence gates passed for the named routes, viewports, interactions, and serving contract. External dependencies and unexercised states remain explicitly listed.
- **Offline-validated static mirror — declared scope** — the validated static mirror also passed the declared interaction coverage with external network blocked and no unexpected external requests.
- **Partial static mirror** — one or more declared-scope checks are blocked, failed, approximated, or not exercised. List each status and its evidence.

## Editable Recreation Acceptance Tiers

- **Validated recreation — declared scope** — the recreated baseline passed the named routes, viewports, interactions, and local serving checks against source evidence.
- **Partial recreation** — one or more declared-scope features are blocked, approximated, failed, accepted as exceptions, or not exercised.

## Defaults

- Inside an existing repository, follow its conventions and architecture; do not introduce new libraries or frameworks when equivalents exist.
- Response format: Declared Scope → Method and Authorization Basis → Capture or Recreation Result → Validation Evidence → Gaps and External Dependencies → Local Serve Contract. Keep detailed artifacts in `<project-dir>/reports/` and keep the user-facing summary concise.
