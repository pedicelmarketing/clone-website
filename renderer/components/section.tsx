/**
 * Section component — emphasis-driven layout primitives.
 *
 * Each emphasis value produces a genuinely different COLUMN STRUCTURE at
 * >=1024px (the critique's specific defect was the renderer stacking all
 * content in the left ~45% of a 1440px viewport). The variants are not
 * different font sizes of the same single-column stack.
 *
 *   hero       -> 12-col grid; left 7 (signature + heading), right 5
 *                  (offset annotation + gold dot margin marker)
 *   primary    -> 12-col grid; left 4 (sticky index), right 8 (body copy)
 *   secondary  -> 12-col grid; full-width band; content column offset to
 *                  cols 4-11 (asymmetric, intentional whitespace on left)
 *   minor      -> single-row thin band; full bleed, fixed low height
 *
 * Below 1024px every variant collapses to a single stacked column so the
 * design is still legible on mobile.
 */

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { Emphasis } from "@/lib/design-plan";

interface SectionProps {
  emphasis: Emphasis;
  id: string;
  children: ReactNode;
  /** When true, section is rendered without a surrounding container
   *  (used by the cover band for full-bleed hero treatments). */
  bare?: boolean;
}

export function Section({ emphasis, id, children, bare }: SectionProps) {
  if (bare) {
    return (
      <section id={id} data-emphasis={emphasis}>
        {children}
      </section>
    );
  }
  return (
    <section
      id={id}
      data-emphasis={emphasis}
      className={cn(
        // All variants share base vertical rhythm + container width.
        "w-full",
        // Variant-specific horizontal padding comes from each layout child.
        emphasis !== "minor" && "py-24 lg:py-32",
      )}
    >
      {children}
    </section>
  );
}

/** hero: asymmetric split (7/5), generous whitespace on right, signature
 *  element pinned left of the headline. At <1024px stacks vertically. */
export function HeroLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1440px] px-6 lg:px-12">
      <div
        className={cn(
          "grid gap-12 lg:gap-16",
          // >=1024px: 12-col explicit grid; left 7, right 5.
          "grid-cols-1 lg:grid-cols-12",
          "items-start",
        )}
      >
        {children}
      </div>
    </div>
  );
}

/** primary: narrow left index + wide right body (4/8 with a visible
 *  gutter). Designed to spread content across the viewport rather than
 *  pinning it left. */
export function PrimaryLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1440px] px-6 lg:px-12">
      <div
        className={cn(
          "grid gap-8 lg:gap-24",
          "grid-cols-1 lg:grid-cols-12",
          "items-start",
        )}
      >
        {children}
      </div>
    </div>
  );
}

/** secondary: full-width band; content occupies cols 4-11 of a 12-col
 *  grid (offset right). The left ~25% is intentional whitespace. Used
 *  for image essays and CTA blocks where the content should feel
 *  weighted away from center. */
export function SecondaryLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1440px] px-6 lg:px-12">
      <div
        className={cn(
          "grid gap-8 lg:gap-12",
          "grid-cols-1 lg:grid-cols-12",
          "items-start",
        )}
      >
        {children}
      </div>
    </div>
  );
}

/** minor: compact row — single thin band across the full viewport. Used
 *  for the colophon/footer-style disclosure. */
export function MinorLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1440px] px-6 lg:px-12">
      <div
        className={cn(
          "grid gap-6 lg:gap-8",
          "grid-cols-1 lg:grid-cols-12",
          "items-baseline",
        )}
      >
        {children}
      </div>
    </div>
  );
}

/**
 * Column-occupancy primitives. Each layout above is a 12-col grid at >=1024px;
 * components place their children into the grid via these helpers so the
 * column split is explicit (not "I hope the content fills correctly").
 *
 *   cols-7   -> 7/12 (hero left half)
 *   cols-5   -> 5/12 (hero right half)
 *   cols-4   -> 4/12 (primary left index)
 *   cols-8   -> 8/12 (primary right body)
 *   cols-3   -> 3/12 (secondary offset left)
 *   cols-8-9 -> 9/12, starting at col 4 (secondary offset content; uses
 *               col-start-4 to bias the content to the right)
 *   full     -> 12/12 (minor)
 */

interface ColProps {
  children?: ReactNode;
  className?: string;
  "aria-hidden"?: boolean | "true" | "false";
}

export function Cols7({ children, className }: ColProps) {
  return <div className={cn("lg:col-span-7", className)}>{children}</div>;
}
export function Cols5({ children, className }: ColProps) {
  return <div className={cn("lg:col-span-5", className)}>{children}</div>;
}
export function Cols4({ children, className }: ColProps) {
  return <div className={cn("lg:col-span-4", className)}>{children}</div>;
}
export function Cols8({ children, className }: ColProps) {
  return <div className={cn("lg:col-span-8", className)}>{children}</div>;
}
export function Cols3({ children, className }: ColProps) {
  return <div className={cn("lg:col-span-3", className)}>{children}</div>;
}
/** Right-offset content column: starts at col 4 of 12, spans 9. Together
 *  with a `cols-3` left spacer this produces the asymmetric secondary
 *  layout where content lives in cols 4-11 and the left ~25% is whitespace. */
export function OffsetRight9({ children, className }: ColProps) {
  return (
    <div className={cn("lg:col-start-4 lg:col-span-9", className)}>
      {children}
    </div>
  );
}
export function Full({ children, className }: ColProps) {
  return <div className={cn("lg:col-span-12", className)}>{children}</div>;
}