# WebGL / Canvas / 3D Module

Triggers: WebGL, Three.js, React Three Fiber, canvas-rendered scenes, GLSL or shader files, shader-like effects, 3D scenes, GLB/GLTF assets, Draco dependencies, procedural animation systems.

## Discovery additions

- Identify the rendering technology, observable scene-owner artifacts, canvas placement, viewport and camera behavior, renderer configuration where evidenced, textures, models, shaders, masks, postprocessing, interaction handlers, and fallback behavior. Mark inferred or inaccessible details as unknown.
- Map GLB/GLTF, Draco, texture, shader, and runtime dependencies. If any are runtime-loaded, also read `modules/runtime-assets.md`.

## Audit additions

Include every in-scope WebGL/canvas/shader system observed in the Animation Audit: triggers, timing, frame behavior, scroll coupling, opacity, transforms, layering, and interaction states.

## Baseline construction

### Static Mirror

Preserve the authorized deployed runtime and its observed dependencies where technically possible. Limit construction-time accommodations to acquisition, routing, or serving behavior required for the baseline to boot locally; record each accommodation and revalidate the affected experience. Do not treat a presentation or behavior change as a local-serving accommodation.

### Editable Recreation fallback

When preserving the deployed runtime is unsuitable, recreate the observed experience needed for the requested faithful copy. Record any missing procedural behavior or approved approximation as a fidelity gap. Never present a static image as equivalent to an interactive WebGL, canvas, shader, or procedural feature.

## Validation additions

For the declared routes, viewports, and interaction states, verify that the effect renders, moves, responds, resizes, layers correctly, and behaves consistently with the recorded source evidence.

- WebGL/rich-runtime sites often gate the experience behind a staged preloader. For exercised coverage, observe whether the gate reaches its terminal usable state. A progress indicator that stalls is a fidelity gap unless evidence shows that state is expected; report the observation rather than dismissing it as timing.
- Asset 200s are not behavior: validate HDR/GLB/WASM/Draco/Basis pipelines, AudioContext gates, and scroll-scrubbed media through the declared behavioral checks. Record Range/206 behavior for streamed media when it affects local playback.
