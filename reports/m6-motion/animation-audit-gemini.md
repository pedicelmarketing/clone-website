# Gemini Motion-Fidelity Audit

- Source video: `reports/m6-motion/source.webm`
- Mirror video: `reports/m6-motion/mirror.webm`
- Model: `gemini-2.5-flash`
- Frame sampling: `12.0 fps`
- Evidence tier: `Interaction-tested`

*   **Entrance / load animations** — All elements, including the initial text and yellow circle, the subsequent text blocks ("What we believe," "The four things," "Eight chapters"), the list items, the grey placeholder box, and the final call-to-action, animate onto the screen in an identical manner (fading or sliding up) in both videos.
*   **Scroll choreography** — The yellow circle exhibits a slight parallax effect as the page scrolls, which is consistent between both videos (e.g., 0:01-0:02). All content sections reveal themselves on scroll in the same way. No pinned sections were observed.
*   **Continuous motion** — No continuous motion elements like carousels, marquees, or looping videos were present in either the source or the mirror.
*   **Missing or broken motion in the mirror** — There is no observable missing or broken motion in the mirrored video. All animations and scroll-driven effects from the source are present and function correctly.

**Verdict** — `Motion faithful` — All observed animations and scroll choreography are perfectly replicated.
