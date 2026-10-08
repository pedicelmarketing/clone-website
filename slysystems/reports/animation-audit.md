# Animation Audit — sly.systems homepage

> Animation evidence was inferred from the captured CSS bundle (50 `@keyframes`,
> 7 `transition:` declarations), the JS bundle (64 GSAP references), and the
> captured element/scroll behavior. Timings and curve choices are estimates
> because the JS bundle is minified and individual timelines are not named.

| # | Element / section | Trigger | Duration | Easing | Delay | Start state | End state | Transforms / opacity | Parallax / pin / scrub | Sequencing | Asset or module |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Hero "SLY" letter transitions | Page load + scroll (likely GSAP timeline) | ~1.2 s per letter (est.) | power2.out (est., GSAP-default family) | 0–0.4 s staggered (est.) | letters hidden behind per-letter video mask | Each letter is replaced by a brand video that autoplays the letter glyph | Per-letter translate/clip or video frame swap | None | Sequential left→right | Per-letter `.mp4` from `media.base44.com/videos/public/.../0X-hero-letter-{S,L,Y}-*.mp4` (kept external) |
| 2 | Hero CTA "The best opportunities are engineered, not found." | Scroll-driven reveal (likely IntersectionObserver + GSAP) | ~0.8 s (est.) | power3.out (est.) | 0.1 s after viewport entry | translateY(40px) + opacity 0 | translateY(0) + opacity 1 | translate + opacity | None | Triggers on scroll into view | Inline text + GSAP |
| 3 | Newsletter email-capture form (header overlay) | Persistent | — | — | — | visible | visible | — | None | — | Inline `<form>` |
| 4 | "Four moves" service card row | Scroll into view | ~0.6 s per card (est.) | power2.out (est.) | 80 ms staggered per card (est.) | translateY(60px) + opacity 0 | translateY(0) + opacity 1 | translate + opacity | None | Sequential stagger | GSAP staggered timeline |
| 5 | "Pick your world" tab picker + case-study swap | Tab click | ~0.4 s crossfade (est.) | linear | on tab change | Case study A visible | Case study B visible | likely opacity + content swap | None | Tab click → handler swaps video + copy | GSAP + DOM update |
| 6 | Case-study tile video | Tile enters viewport | autoplay loop | n/a | on visibility | muted, paused | muted, playing | n/a | None | IntersectionObserver-gated | Case-study `.mp4` from `media.base44.com/.../{FlipBot_WEB, GEMFLOW-hero-8s, DosPinos-hero-8s, One44-hero-7s, scansly, VUEintro01_WEB, bailar-sly-showcase, …}.mp4` |
| 7 | Audio embed (SoundCloud) | Iframe load | n/a | n/a | n/a | iframe loaded, `auto_play=false` | not played by default | n/a | None | Provider-driven | SoundCloud embed — `audio.md` hygiene |
| 8 | "In the news" logo wall | Scroll into view | ~0.5 s per logo (est.) | power1.out (est.) | 60 ms staggered (est.) | scale(0.9) + opacity 0 | scale(1) + opacity 1 | scale + opacity | None | Sequential stagger | GSAP |
| 9 | Header sticky + opacity-on-scroll | Scroll past hero | ~0.3 s (est.) | linear | scroll-driven | transparent on hero | dark with backdrop-blur | background-color + backdrop-filter | None | scroll position listener | CSS transitions (Tailwind + custom) |

## Motion evidence summary

- Observed motion system(s) and evidence:
  - GSAP (64 references in the captured JS bundle — `gsap` appears as a token).
  - Tailwind utility classes + custom CSS animations: 50 `@keyframes` blocks, 7 declared `transition:` rules in the CSS bundle.
  - The JS bundle's React module is present alongside GSAP — typical pattern is GSAP used for hero/in-view timelines while React handles DOM diffing.
- Shared measured values (durations, easings, thresholds): durations and easings are estimates inferred from GSAP power-easing naming patterns and the absence of exposed timeline debugging in production builds. End-of-fade entrance style is consistent across rows 1–8.
- Declared states exercised: standard capture scroll + load. Not exercised: tab-clicks on "Pick your world", sound toggle on the SoundCloud embed, scroll past footer.
- Blocked, unexercised, or uncertain behavior:
  - Hover states on the four-moves cards (likely JS-driven) — unexercised.
  - Tab swap in "Pick your world" — unexercised; based on DOM presence it almost certainly animates a video + copy crossfade.
  - The SoundCloud iframe is provider-driven and unobservable locally without network.
  - Motion-dev badge (`api.motion.dev/score/badge`) is third-party; SVG-only, no motion.
