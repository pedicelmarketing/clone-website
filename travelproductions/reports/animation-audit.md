# Animation Audit

Source: `https://travelproductions.film/es/…` (7 declared ES routes)
Evidence basis: source inspection of the captured documents (the GSAP call sites and Elementor motion-FX
`data-settings` are readable verbatim) plus the paired source/local scroll passes in
`reports/viewports-paired-*/`. Values read from code are exact; anything not measured is marked
`(est.)` or `Unknown`.

| # | Element / section | Trigger | Duration | Easing | Delay | Start state | End state | Transforms / opacity | Parallax / pin / scrub | Sequencing | Asset or module |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Every `.elementor-heading-title`** — the site's signature effect. Applied globally: `gsap.utils.toArray('.elementor-heading-title')` then one tween per heading. | Scroll. `ScrollTrigger` `start: 'center 100%'`, `end: 'center 50%'` — the reveal runs from the moment the heading's centre reaches the viewport bottom until it reaches the viewport middle. | Not time-based — **scrub-linked to scroll distance** (half a viewport height of travel). | `ease: 'none'` (linear, as scrub requires) | none | `background-size` at its CSS-declared start (0% width) | `backgroundSize: '100%'` | No transform, no opacity. The heading carries a clipped background; growing its `background-size` wipes colour across the glyphs left-to-right. | **`scrub: true`** — position is bound to scroll, so it reverses when you scroll back up. No pin. | Independent per heading; no shared timeline. | GSAP 3.9.1 + ScrollTrigger (localized under `_external/`) |
| 2 | Portfolio grid container (`.image-grid` parent, `data-id="b24f31d"`) | Scroll | Continuous | Elementor's internal motion-FX curve — `Unknown` | none | Untranslated | Translated on Y | `background_motion_fx_translateY_effect: yes`, `speed: 3px`, `affectedRange: 0–100%` | **Parallax** (translateY), enabled on `desktop, tablet_extra, tablet, mobile` | Independent | Elementor Pro motion FX (no GSAP) |
| 3 | Same container — `zoom_out2` class | `Unknown` — the class is applied in markup; its keyframes live in the theme/Elementor CSS and were not isolated | `Unknown` | `Unknown` | `Unknown` | `Unknown` | `Unknown` | Scale (implied by the name) | `Unknown` | `Unknown` | Site CSS. **Recorded as observed-in-markup only — behaviour not verified.** |
| 4 | Custom cursor follower | Pointer move (`e.clientX` / `e.clientY`) | `Unknown` (est. sub-300 ms settle from the easing choice) | `power2.out` | none | Cursor element at last position | Cursor element at pointer position | `x`, `y` on a GSAP timeline; a second element (`cursorSmall`) is faded via `gsap.to(cursorSmall, { opacity: 0 })` | Neither | Timeline with shared `defaults` | GSAP 3.9.1 |
| 5 | Whole-document scrolling | Wheel / touch | Continuous | Lenis momentum curve — `Unknown` (plugin defaults not read) | none | — | — | Momentum-damped scroll position | Neither. Note: it damps the *feel* but `window.scrollY` still advances, so ScrollTrigger and the capture's `window_scroll` mechanism both work normally. | Wraps everything | `mousewheel-smooth-scroll` plugin → `wp-content/uploads/wpmss/lenis-init.min.js` |
| 6 | Rotating globe (`/es/sobre-nosotros/`, also referenced from `/es/inicio/`) | Autoplay on mount (est.) | Loop — `Unknown` cycle length | Baked into the Lottie | `Unknown` | First frame | Looping | Vector animation | Neither | Independent | Lottie payload `World-global-3.json` (38 KB) — acquired via `--extra-urls` |
| 7 | Hero background reel + 7 portfolio cover videos | Autoplay, muted, looping (est. — inferred from playback with no controls visible) | Clip length | — | none | First frame | Looping | — | Neither | Independent | 21 self-hosted `.mp4`; separate desktop 1080p / mobile 720p hero cuts |
| 8 | Luma Labs splat scene (`/es/escena-3d/`) | Pointer drag / scene autoplay inside the iframe | `Unknown` | `Unknown` | `Unknown` | `Unknown` | `Unknown` | Camera motion within a third-party viewer | `Unknown` | `Unknown` | `cdn-luma.com` viewer iframe — **`Embed`; internals never exercised** |
| 9 | Mobile nav overlay (`Menú` → `Cerrar`) | Tap | `Unknown` | `Unknown` | `Unknown` | Closed | Open | `Unknown` | Neither | Independent | Elementor Pro nav widget. **Not exercised** — the capture scrolls but does not tap. |

## Motion evidence summary

- **Observed motion system(s) and evidence.** Three coexisting systems, all confirmed by source
  inspection of the captured documents, not inferred: **GSAP 3.9.1 + ScrollTrigger** loaded from
  cdnjs and localized (rows 1, 4); **Elementor Pro motion FX** driven by `data-settings` JSON on the
  container (row 2); and **Lenis** momentum scrolling from the `mousewheel-smooth-scroll` plugin
  (row 5). One Lottie animation (row 6). No `requestAnimationFrame` scene, no canvas animation, no
  audio-synced motion anywhere in the declared scope.

- **Shared measured values.** The one global, exactly-known rule is row 1: `start: 'center 100%'`,
  `end: 'center 50%'`, `scrub: true`, `ease: 'none'`, `backgroundSize → 100%`. That single tween is
  the site's whole type-reveal identity and it is applied indiscriminately to *every* heading — which
  is why section rhythm reads as consistent without any per-section choreography. Elementor's
  parallax adds exactly `3px` of translateY across a `0–100%` range. Nothing else was measured; the
  Lenis and Elementor easing curves were not read out of their bundles and are recorded `Unknown`
  rather than guessed.

- **Declared states exercised.** Scroll was driven for real — 14 discrete steps per route at both
  desktop and mobile, on the live source *and* the local mirror, with bounded DOM settling. Row 1 is
  therefore **interaction-tested** on both sides: the paired screenshots catch the wipe mid-progress
  (the source frame shows a heading fully revealed where the local frame shows it part-revealed —
  same mechanism, different scroll offset at shutter time, which is what a scrubbed tween looks like).
  Rows 2, 5, 6 and 7 are **observed visually** in those same passes.

- **Blocked, unexercised, or uncertain behavior.**
  - Row 4 (cursor follower) — **not exercised.** The capture never moves a pointer, so this is
    source-inspection evidence only.
  - Row 9 (mobile nav overlay) and the cookie banner's accept/reject transitions — **not exercised.**
  - Row 8 (Luma scene) — **`Embed`, never exercised.** It is a third-party viewer in an iframe; there
    is no local WebGL context, and it cannot run offline at all.
  - Row 3 (`zoom_out2`) — the class is present in the captured markup but its keyframes were not
    isolated, so its behaviour is `Unknown`. Flagged rather than assumed inert.
  - **`prefers-reduced-motion` was not tested.** No reduced-motion handling was found in the captured
    GSAP call sites, which suggests the source does not honour it — but absence of code in the inline
    scripts is not proof of absence site-wide, so this stays `Unknown`.
  - One pre-existing source JavaScript error, `mouseleaveHandler is not defined`, throws on the
    **live site as well as the mirror**. The paired run classified it
    `exact_failure_matched_explicit_source_local_pair` — a source baseline exception, not a mirror
    defect. It plausibly belongs to a hover handler that never binds, which may mean some intended
    hover motion is dead on the source itself. Not repaired: repairing a source bug would be a
    change, and the mirror's job is fidelity.
