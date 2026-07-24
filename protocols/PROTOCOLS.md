# Site Cloner Operating Protocols

## Scope and phases

Work proceeds in two distinct phases:

1. **Faithful baseline:** capture a deployed site as a Static Mirror, or technically fall back to an Editable Recreation. Preserve the declared visual, responsive, behavioral, animation, and asset experience without redesigning it.
2. **Re-version:** separately change branding, copy, layout, colors, media, or behavior. Do not mix these changes into baseline production.

Every delivery declares its routes, viewports, interactions, and local serving setup. A homepage-only pass supports only a homepage claim.

## Method decision

**Static Mirror is the default.** Observe the runtime asset graph, acquire eligible assets through the manifest pipeline, serve through HTTP, and validate against the live source. Use **Editable Recreation** only when runtime capture is technically blocked or unsuitable (for example, a session-coupled builder runtime that cannot boot faithfully from a local origin). Never choose recreation merely for convenience or permission assumptions, and never describe deployed bundles as recovered clean source.

## Acceptance tiers

Static Mirror reports name exactly one supported tier:

- **First-render mirror:** an in-scope page renders locally; interactions, lazy assets, and runtime states remain unverified.
- **Validated static mirror — declared scope:** declared routes, viewports, interactions, dependencies, and applicable evidence gates passed.
- **Offline-validated static mirror — declared scope:** validated scope also passes with external networking blocked and no unexpected external requests.
- **Partial static mirror:** one or more declared checks failed, were blocked, approximated, or not exercised.

Editable Recreation reports use **Validated recreation — declared scope** or **Partial recreation** under the same evidence discipline.

## Evidence and fidelity honesty

Every per-system verdict states its evidence basis: **Observed visually**, **Interaction-tested**, **DOM+assets confirmed**, **HTTP-200 only**, or **Not exercised**. Compiling, downloading, or serving is not visual or behavioral validation. Distinguish source-existing telemetry failures from mirror-introduced defects.

The **Fidelity Gap rule** is mandatory: if an in-scope visible or audible source feature is absent, frozen, disabled, broken, replaced, or substantially downgraded, record a Fidelity Gap and do not mark that system Pass. User acceptance changes it to an Accepted Exception, never a Pass. Unknowns and unexercised states remain explicit.

## Asset classification and hygiene

Classify each major asset as one of: `Original`, `Local Copy`, `Embed`, `Kept External`, `User-Supplied Baseline Asset`, `Recreated`, `Recreated From Observation`, `Approximated`, `Blocked`, or `Unknown`. Record its source, status, and rationale in the preservation report and use `mirror-manifest.json` as the machine-authoritative acquisition record.

Paid/protected fonts, provider-streamed media, and other protected or licensed assets are classified but never silently redistributed. Analytics and tracking are not replayed; use only a documented deterministic no-op when local boot requires it.

## Capture and builder-runtime rules

`--force-document` applies only to public top-level documents supplied for reference use. It does not broadly override asset classification. Every forced document URL must be logged in `manifest.forced_document_overrides`, then validated; acquisition alone does not prove the runtime boots locally.

For Wix, Squarespace, Webflow, GTM-heavy, and similar builder/telemetry-heavy sites, run **source-paired viewport validation**: pass both local and live URLs and identify the live URL as the source baseline. Subtract console/network failures already present on the live source so benign source telemetry is not reported as a mirror defect. Any local-only runtime failure, empty skeleton, missing dependency, or broken interaction remains a Fidelity Gap and normally limits the result to Partial.

Always validate through the documented local HTTP server, never `file://`, and report the exact serve command, web root, port, accommodations, external dependencies, gaps, and tier reached.
