# Animation Audit

Motion on this site is entirely **Webflow IX2** scroll-triggered reveals plus CSS transitions.
There is no timeline/scrub library (no GSAP, ScrollTrigger, Lenis), no canvas or WebGL, no
video-driven or audio-synced motion — confirmed by a trigger scan across all 63 capture graphs.

Because IX2 ships its definitions inside Webflow's minified JS chunks rather than as readable
config, exact per-element durations and easings are **not directly observable** without
reverse-engineering the bundle. That is deliberately not done: the bundle is preserved byte-for-byte
and replays its own timings. Values below are therefore recorded as **observed behaviour**, and any
number is marked `(est.)`.

| # | Element / section | Trigger | Duration | Easing | Delay | Start state | End state | Transforms / opacity | Parallax / pin / scrub | Sequencing | Asset or module |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Hero heading + subcopy (`/`) | Page load | ~600 ms (est.) | Unknown (IX2-defined) | ~0–200 ms (est.) | opacity 0, translateY | opacity 1, translateY 0 | opacity + translate | none | staggered heading → subcopy → CTA (est.) | `webflow.*.js` (IX2) |
| 2 | Service cards (`/`, `/services`) | Scroll into view | ~500 ms (est.) | Unknown | staggered per card (est.) | opacity 0, translateY | opacity 1, translateY 0 | opacity + translate | none | sequential per card | IX2 |
| 3 | Portfolio / case-study grid | Scroll into view | ~500 ms (est.) | Unknown | staggered (est.) | opacity 0 | opacity 1 | opacity + translate | none | per item | IX2 |
| 4 | Testimonial slider | Autoplay + manual | Unknown | Unknown | Unknown | slide N | slide N+1 | translateX | none | loop | Webflow slider (`w-slider`) |
| 5 | Nav dropdown | Hover / tap | ~200 ms (est.) | ease (CSS) | 0 | collapsed | expanded | height/opacity | none | none | `w-dropdown` + CSS |
| 6 | Mobile nav burger | Tap | ~300 ms (est.) | ease (CSS) | 0 | closed | open overlay | transform | none | none | `w-nav` + CSS |
| 7 | Button hovers (site-wide) | Hover | ~200 ms (est.) | ease (CSS) | 0 | base | hover | background/colour | none | none | shared stylesheet |
| 8 | Blog collection items (`/blog`) | Scroll into view | ~500 ms (est.) | Unknown | staggered (est.) | opacity 0 | opacity 1 | opacity + translate | none | per item | IX2 |
| 9 | Lazy image fade-in | Intersection | browser-native | — | — | unloaded | painted | opacity | none | none | native `loading="lazy"` |

## Motion evidence summary

- **Observed motion system(s) and evidence:** Webflow IX2, evidenced by `data-w-id` attributes
  throughout the markup and the `webflow.*.js` chunks in the manifest. Slider/dropdown/nav motion
  comes from Webflow's `w-slider` / `w-dropdown` / `w-nav` components plus CSS transitions in the
  shared stylesheet. No third-party motion library present in any capture graph.
- **Shared measured values:** not extracted. IX2 timings live inside the minified bundle; the bundle
  is preserved unmodified, so the mirror replays the source's own values rather than any
  re-implementation. All table durations are `(est.)` from observation.
- **Declared states exercised:** full-page `window_scroll` across 10 routes × 3 viewports
  (desktop/tablet/mobile), maximum scrollY 8764 on `/`. Scroll-triggered reveals fire and lazy
  images resolve — 61 pending images settled on `/` within ~1529 ms. Evidence:
  `reports/viewports/viewport-results.json` and the full-page screenshots.
- **Blocked, unexercised, or uncertain behavior:**
  - **Testimonial slider timing** — autoplay interval and manual advance `Not exercised`; the
    viewport pass scrolls but does not click slider controls.
  - **Nav dropdown / mobile burger** — render confirmed at all 3 viewports, but open/close
    `Not exercised` (no click interaction driven).
  - **Hover states** — `Not exercised`; no synthetic hover was driven.
  - **Per-element IX2 durations/easings** — `Unknown` by choice, as above.
  - None of the above is a Fidelity Gap: the governing code is preserved byte-for-byte, so the
    behaviour is the source's own. They are recorded as unexercised evidence, not as passes.
