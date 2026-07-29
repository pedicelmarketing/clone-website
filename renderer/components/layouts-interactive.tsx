/**
 * The three harvested layouts that need JavaScript.
 *
 * Kept in a separate module from `layouts.tsx` on purpose: `"use client"` is
 * file-scoped, so putting these beside the zero-JS layouts would drag
 * TypeHero, MarqueeBand, LabelRailCard and ContactPanel into the client bundle
 * for nothing. Half the layout vocabulary ships no JavaScript at all, and that
 * is only true because of this split.
 *
 * All three obey rule 3 from `layouts.tsx`: inactive state is hidden with
 * opacity/transform, never unmounted, so Gate 11 still sees every copy block in
 * the exported HTML.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useScroll, useTransform } from "motion/react";
import type { LayoutProps } from "@/components/layouts";
import { itemsFor, Container, Eyebrow, BrandImage } from "@/components/layouts";

/**
 * scroll-rail — a horizontal rail that advances while the section is pinned.
 *
 * The reference drove this with GSAP ScrollTrigger, which this project cannot
 * use (non-MIT; the build has a licence guard). Rebuilt with sticky positioning
 * over a tall spacer plus `useScroll`/`useTransform` — same effect, MIT, and
 * the hooks were already imported elsewhere so it adds no new dependency.
 *
 * The pin distance is measured from the element (`scrollWidth - clientWidth`),
 * NOT computed from the panels' vw widths: `100vw` includes the scrollbar and
 * the inner `w-max` does not, so the vw arithmetic overshoots by ~15px on
 * desktop Chrome and undershoots with overlay scrollbars.
 *
 * Below `md` the whole mechanism is dropped for a plain vertical column.
 */
export function ScrollRail({ section }: LayoutProps) {
  const items = itemsFor(section, 8);
  const { copy } = section;
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const stickyRef = useRef<HTMLDivElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [overflow, setOverflow] = useState(0);

  useEffect(() => {
    const measure = () => {
      const track = trackRef.current;
      const frame = stickyRef.current;
      if (!track || !frame) return;
      // Only pin where the rail is actually horizontal.
      if (!window.matchMedia("(min-width: 768px)").matches) {
        setOverflow(0);
        return;
      }
      // Measure the track against its FRAME, not against itself. The track is
      // `w-max`, so it sizes to its own content and `scrollWidth -
      // clientWidth` is always 0 — it overflows its parent, not itself. That
      // returned an overflow of zero, the pin never engaged, and the section
      // rendered as a screen-tall band of dead space.
      //
      // The frame's clientWidth is also the right reference rather than
      // `100vw`, because clientWidth excludes the scrollbar and `vw` does not.
      setOverflow(Math.max(0, track.scrollWidth - frame.clientWidth));
    };
    measure();
    // Fonts change text metrics, which changes the track width.
    document.fonts?.ready.then(measure).catch(() => {});
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [items.length]);

  const { scrollYProgress } = useScroll({
    target: wrapRef,
    offset: ["start start", "end end"],
  });
  const x = useTransform(scrollYProgress, [0, 1], [0, -overflow]);

  return (
    <div
      ref={wrapRef}
      // Total scroll height = one viewport + exactly the horizontal overflow,
      // so the rail finishes travelling at the instant the pin releases.
      style={overflow ? { height: `calc(100vh + ${overflow}px)` } : undefined}
    >
      <div
        ref={stickyRef}
        className="md:sticky md:top-0 md:h-screen md:overflow-hidden md:flex md:items-center"
      >
        <motion.div
          ref={trackRef}
          style={overflow ? { x } : undefined}
          className="flex w-full flex-col gap-12 px-6 py-20 md:w-max md:flex-row md:items-stretch md:gap-0 md:py-0 lg:px-12"
        >
          <div className="flex flex-col justify-center md:w-[46vw] md:shrink-0 md:pr-16">
            <Eyebrow section={section} />
            {copy.headline && (
              <h2 className="mt-5 max-w-[16ch] font-display text-4xl leading-[0.98] tracking-[-0.02em] text-foreground lg:text-6xl">
                {copy.headline}
              </h2>
            )}
            {copy.subhead && (
              <p className="mt-6 max-w-[46ch] font-body text-lg leading-relaxed text-foreground/70">
                {copy.subhead}
              </p>
            )}
          </div>
          {items.map((item, i) => (
            <div
              key={i}
              className="flex flex-col justify-center border-t border-foreground/10 pt-8 md:w-[42vw] md:shrink-0 md:border-t-0 md:px-10"
            >
              <span className="u-label text-primary">{String(i + 1).padStart(2, "0")}</span>
              <p className="mt-4 max-w-[34ch] font-display text-2xl leading-[1.2] tracking-[-0.01em] text-foreground lg:text-[2rem]">
                {item}
              </p>
            </div>
          ))}
          <div className="hidden md:block md:w-[8vw] md:shrink-0" aria-hidden="true" />
        </motion.div>
      </div>
    </div>
  );
}

/**
 * ghost-index — display-scale rows in low-opacity ink, with a preview that
 * follows the cursor.
 *
 * The rows ARE the design: at 5.5vw in 16%-opacity ink they read as texture
 * until you approach one, which is why this works with no imagery of its own.
 * The preview is a progressive enhancement — guarded by
 * `matchMedia("(pointer: fine)")`, so on touch it is simply a legible list.
 *
 * Position is written straight to `style.transform` inside rAF rather than
 * through React state: a state update per mousemove would re-render the whole
 * section sixty times a second.
 */
export function GhostIndex({ section }: LayoutProps) {
  const items = itemsFor(section, 8);
  const { copy } = section;
  const media = section.media;
  const previewRef = useRef<HTMLDivElement | null>(null);
  const frame = useRef(0);
  const [fine, setFine] = useState(false);
  const [active, setActive] = useState<number | null>(null);

  useEffect(() => {
    setFine(window.matchMedia("(pointer: fine)").matches);
  }, []);

  useEffect(() => {
    if (!fine) return;
    const onMove = (e: MouseEvent) => {
      if (frame.current) return;
      frame.current = requestAnimationFrame(() => {
        frame.current = 0;
        const el = previewRef.current;
        if (el) el.style.transform = `translate3d(${e.clientX + 24}px, ${e.clientY - 150}px, 0)`;
      });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", onMove);
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [fine]);

  return (
    <Container className="py-20 lg:py-28">
      <div className="flex items-end justify-between gap-6">
        {copy.headline && (
          <h2 className="max-w-[18ch] font-display text-4xl leading-[1.02] tracking-[-0.02em] text-foreground lg:text-6xl">
            {copy.headline}
          </h2>
        )}
        <span className="u-label shrink-0 text-foreground/70">
          ({String(items.length).padStart(2, "0")})
        </span>
      </div>
      {copy.subhead && (
        <p className="mt-6 max-w-[52ch] font-body text-lg leading-relaxed text-foreground/70">
          {copy.subhead}
        </p>
      )}

      <div className="mt-12 border-b border-foreground/10">
        {items.map((item, i) => (
          <a
            key={i}
            href={`#${section.id}`}
            onMouseEnter={() => setActive(i)}
            onMouseLeave={() => setActive(null)}
            className="group flex items-center justify-between gap-6 border-t border-foreground/10 py-6 outline-none focus-visible:ring-2 focus-visible:ring-primary lg:py-7"
          >
            <span className="font-display text-[clamp(1.5rem,5.5vw,4.75rem)] leading-[1.05] tracking-[-0.02em] text-foreground/45 transition-colors duration-200 group-hover:text-foreground group-focus-visible:text-foreground">
              {item}
            </span>
            <span aria-hidden="true" className="shrink-0 text-foreground/70 transition-colors group-hover:text-primary">
              ↗
            </span>
          </a>
        ))}
      </div>

      {/* Single preview node, moved rather than remounted.
       *
       *  This used to be `{fine && media && …}`, which broke rule 3 of
       *  layouts.tsx: `fine` is false during server rendering, so the <img>
       *  was absent from the STATIC EXPORT entirely — the photograph never
       *  shipped and Gate 2 never saw it. It is now always in the DOM and only
       *  its visibility is conditional. */}
      {media && (
        <div
          ref={previewRef}
          aria-hidden="true"
          className={[
            "pointer-events-none fixed left-0 top-0 z-30 h-[300px] w-[420px]",
            "overflow-hidden rounded-[14px] shadow-2xl transition-opacity duration-300",
            fine ? "" : "invisible",
          ].join(" ")}
          style={{ opacity: fine && active !== null ? 1 : 0 }}
        >
          <BrandImage file={media.file} alt={media.alt} className="h-full" />
        </div>
      )}
    </Container>
  );
}

/**
 * card-carousel — one large card at a time, controls outside it.
 *
 * Every card stays mounted and the track is translated, so all four titles are
 * in the exported HTML even though only one is visible. The tab strip beneath
 * repeats those titles as always-visible text, which means the copy survives
 * even if the card layer were ever broken — belt and braces, because Gate 11
 * cannot tell a visible card from a hidden one.
 */
export function CardCarousel({ section }: LayoutProps) {
  const items = itemsFor(section, 6);
  const { copy, media } = section;
  const [index, setIndex] = useState(0);
  const count = items.length || 1;
  const go = (d: number) => setIndex((i) => (i + d + count) % count);

  return (
    <Container className="py-20 lg:py-28">
      <div className="max-w-[46ch]">
        <Eyebrow section={section} />
        {copy.headline && (
          <h2 className="mt-4 font-display text-4xl leading-[1.05] tracking-[-0.02em] text-foreground lg:text-5xl">
            {copy.headline}
          </h2>
        )}
        {copy.subhead && (
          <p className="mt-5 font-body text-lg leading-relaxed text-foreground/70">{copy.subhead}</p>
        )}
      </div>

      <div className="mt-12 flex items-center justify-center gap-4 lg:gap-6">
        <button
          type="button"
          aria-label="Previous"
          onClick={() => go(-1)}
          className="hidden h-12 w-12 shrink-0 place-items-center rounded-full border border-foreground/20 text-foreground/70 transition-colors hover:border-foreground/60 hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary sm:grid"
        >
          ←
        </button>

        <div className="w-full overflow-hidden rounded-[14px] lg:w-[85%]">
          <div
            className="flex transition-transform duration-500 ease-out"
            style={{ transform: `translateX(-${index * 100}%)` }}
          >
            {items.map((item, i) => (
              <div
                key={i}
                aria-hidden={i !== index}
                className="relative w-full shrink-0 overflow-hidden bg-foreground/5 p-8 lg:aspect-[3/2] lg:p-12"
              >
                {/* The photograph sits BEHIND the copy under a gradient, which
                 *  is what lets a phone-grade image work here: the busy lower
                 *  third of the frame is covered by the scrim by design rather
                 *  than by luck. */}
                {media && (
                  <>
                    <BrandImage
                      file={media.file}
                      alt={i === 0 ? media.alt : ""}
                      className="absolute inset-0 h-full opacity-45"
                    />
                    <div
                      aria-hidden="true"
                      className="absolute inset-0 bg-gradient-to-t from-background via-background/70 to-background/20"
                    />
                  </>
                )}
                <div className="relative flex h-full flex-col justify-end">
                  {/* /80, not the usual /70 floor: this label sits on the
                   *  card's tinted `bg-foreground/5` surface, which lifts the
                   *  background from #f7f5ef to #edece6 and drops /70 to 4.4:1
                   *  — just under AA. The ladder's floor depends on the
                   *  surface, not only on the ink. */}
                  <span className="u-label text-primary">
                    {String(i + 1).padStart(2, "0")} / {String(count).padStart(2, "0")}
                  </span>
                  <p className="mt-4 max-w-[30ch] font-display text-2xl leading-[1.2] text-foreground lg:text-4xl">
                    {item}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <button
          type="button"
          aria-label="Next"
          onClick={() => go(1)}
          className="hidden h-12 w-12 shrink-0 place-items-center rounded-full border border-foreground/20 text-foreground/70 transition-colors hover:border-foreground/60 hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary sm:grid"
        >
          →
        </button>
      </div>

      {/* Always-visible titles. This is the copy's real home as far as Gate 11
       *  and a search engine are concerned. */}
      <div className="mt-6 flex flex-wrap justify-center gap-x-7 gap-y-2 border-t border-foreground/10 pt-5">
        {items.map((item, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setIndex(i)}
            className={[
              "font-body text-sm transition-colors",
              i === index ? "text-foreground" : "text-foreground/70 hover:text-foreground/70",
            ].join(" ")}
          >
            {item.length > 42 ? `${item.slice(0, 40)}…` : item}
          </button>
        ))}
      </div>

      {copy.caption && (
        <p className="mt-8 text-center font-body text-sm italic text-foreground/70">{copy.caption}</p>
      )}
    </Container>
  );
}
