# Runtime Asset Graph Module

Triggers: dynamic imports, lazy-loaded chunks, runtime-loaded assets (video, audio, shaders, GLB/GLTF, textures), Draco dependencies, provider-loaded embeds, assets that appear only after scroll, hover, click, route transition, media playback, intro/start screens, game/app interaction, or other obvious runtime triggers.

Do not assume the initially loaded page contains all required assets.

## Discovery additions

- Run `scripts/capture_assets.py <url>` to capture the network-level asset graph including scroll-triggered loads. Use its JSON output as evidence in the Discovery report.
- Declare the route and interaction coverage before capture. Beyond first load and scroll, exercise the in-scope hover, click, route transition, media playback, intro/start, game/app, and other runtime triggers that may reveal additional assets.
- From the capture and from authorized source inspection, identify: dynamic imports, lazy chunks, runtime-loaded media and models, decoder/shader/texture dependencies, and the interaction/scroll/route/media triggers that load them.
- Scan downloaded JS/CSS bundles for runtime asset references and loaders, including `import(`, `new Worker`, `new URL(`, `import.meta.url`, and `fetch(`. Look for `.wasm`, `.glb`, `.gltf`, `.ktx`, `.ktx2`, `.hdr`, `.exr`, `.drc`, `.bin`, `.mp3`, `.ogg`, `.woff`, and `.woff2`.
- Source repos, source maps, exposed build artifacts, and manifests may be used only in authorized contexts and only for route/asset verification and completeness checks, not to reconstruct or copy proprietary source code.
- Record source URLs or evidenced code paths and list blocked, unresolved, or unexercised dependencies in Risks. Do not claim that the graph is exhaustive beyond the declared trigger coverage.

## Baseline construction

### Static Mirror

Resolve confirmed, authorized runtime asset URLs against the original source origin and feed them into `scripts/mirror_assets.py --extra-urls <file>`. The same authorization, provider, license, and Asset Classification gates apply. Limit accommodations to acquisition, routing, or serving behavior required for local operation, and record their provenance.

### Editable Recreation fallback

Use the observed asset graph to reproduce the requested behavior when Static Mirror is unsuitable. It is evidence for the faithful copy, not permission to reconstruct proprietary source. Record any dependency that cannot be lawfully used or faithfully recreated as a gap.

## Validation additions

Exercise the declared interactions and scroll states that load runtime assets. Verify that the critical chunks, models, textures, audio, video, and fonts required by that coverage load, and list every remaining external, blocked, unresolved, or unexercised dependency.

During local validation with `scripts/serve.py`, treat 404 log lines as missing-local-asset evidence. For each missing local path, resolve it against the original source origin and download it with `scripts/mirror_assets.py --extra-urls <file>` if authorized, or classify it as blocked, kept external, unknown, or another applicable Asset Classification. Re-run the declared coverage and report any unresolved critical path.

Document every blocked dependency as a `Fidelity Gap`, `Unknown`, or approved baseline approximation.
