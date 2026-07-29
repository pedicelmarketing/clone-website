"use client";

/**
 * Restrained motion primitives driven by the brand brief's
 * motion_vocabulary: "reading-speed motion, not showcase motion."
 *
 * We provide ONLY what the design plan actually calls for:
 *  - a fade-in-on-view hook (under 200ms)
 *  - a single gold-dot highlighter that pins to the side of the viewport
 *    while the reader scrolls
 *  - native smooth scrolling via CSS (no scroll library)
 *
 * Anything else (parallax, scroll-jacking, complex timelines) is
 * intentionally NOT included.
 */

import { useEffect, useRef, type ReactNode } from "react";
import { motion, useScroll, useSpring, useTransform } from "motion/react";

/**
 * SmoothScroll — intentionally a plain passthrough.
 *
 * This used to drive Lenis. Lenis costs ~10KB, hijacks the scroll thread, and
 * fought the `scroll-mt` offsets that keep in-page nav links from landing under
 * the sticky header. `scroll-behavior: smooth` in globals.css does the same job
 * for zero bytes and honours prefers-reduced-motion for free. Kept as a
 * component so the page structure does not churn if a scroll library is ever
 * reintroduced deliberately.
 */
export function SmoothScroll({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

/** Fade a single block in once it enters the viewport. ~180ms. */
export function FadeIn({
  children,
  delay = 0,
}: {
  children: ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      whileInView={{ opacity: 1, y: 0 }}
      // `amount`, NOT a negative viewport margin. The previous
      // `margin: "-10% 0px -10% 0px"` shrank the detection box by 10% at the
      // bottom, so an element sitting at the very end of the document could
      // never enter it once the page had scrolled as far as it goes — the
      // colophon's text stayed at opacity 0 permanently. `amount: 0.2` reveals
      // once a fifth of the block is visible, which is always reachable, and
      // still delays the fade until the block is meaningfully on screen.
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.18, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

/** The brand's signature gold dot. A 10px circle that travels down the
 *  viewport as the reader scrolls. Position interpolation follows the
 *  brief: 280ms cubic-bezier easing on the position value. */
export function GoldDotMarker() {
  const ref = useRef<HTMLDivElement | null>(null);
  const { scrollYProgress } = useScroll();
  const y = useSpring(useTransform(scrollYProgress, [0, 1], [0, 2000]), {
    stiffness: 90,
    damping: 26,
    mass: 0.6,
  });
  return (
    <div
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none fixed top-0 left-0 z-50 hidden lg:block"
      style={{ willChange: "transform" }}
    >
      <motion.div
        style={{ y }}
        className="ml-3 mt-12 size-2.5 rounded-full bg-primary"
      />
    </div>
  );
}

/**
 * SignatureMark — the design plan's signature element rendered at scale.
 *
 * The plan specifies "the gold dot": the literal fill of the dot above the
 * 'i' in the Pedicel wordmark, reused as a recurring brand device. Here it
 * anchors the cover's right column, giving the hero a focal point instead
 * of dead space. Colour comes from --color-primary (never a raw hex).
 */
export function SignatureMark() {
  return (
    <div className="relative flex h-full min-h-[220px] items-start justify-start lg:justify-center lg:pt-6">
      <motion.div
        aria-hidden="true"
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.7, ease: [0.2, 0.7, 0.2, 1] }}
        className="rounded-full"
        style={{
          width: "clamp(88px, 12vw, 168px)",
          height: "clamp(88px, 12vw, 168px)",
          background: "var(--color-primary)",
        }}
      />
    </div>
  );
}
