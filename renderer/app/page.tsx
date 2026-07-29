/**
 * Root page: renders the brand's re-versioned site from the design plan.
 *
 * Structure comes from each section's resolved `shape` (see lib/design-plan.ts
 * resolveLayout), NOT from `emphasis`. Emphasis only ever described scale, so
 * driving layout from it produced one repeated shape for every section of every
 * page — the templated output this capability exists to avoid.
 *
 * Every text string comes from plan.copy_blocks[]; skipped sections are
 * filtered out. Nothing is fabricated here. A section whose plan supplies no
 * copy for a given role simply does not render that role — the old
 * "[no body in plan]" placeholders were shipping to the live page.
 */

import { getPageRegions, loadBrandWordmark, loadDesignPlan } from "@/lib/design-plan";
import { LAYOUT_COMPONENTS } from "@/components/layouts";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { GoldDotMarker, SmoothScroll } from "@/components/motion-primitives";

// Server-side load. This runs at build time in Next 15 (App Router).
const plan = loadDesignPlan();
const { masthead, body, colophons, nav } = getPageRegions(plan);
// Wordmark: the masthead section's headline is the brand's own name written by
// the design pass from brief facts. Only when no masthead exists do we fall
// back to the brand's published domain.
const wordmark = masthead?.copy.headline ?? loadBrandWordmark();

export default function Home() {
  return (
    <SmoothScroll>
      <div id="top" />
      <SiteHeader wordmark={wordmark} tagline={masthead?.copy.subhead ?? null} nav={nav} />
      <GoldDotMarker />
      <main className="min-h-screen bg-background text-foreground">
        {body.map((section, i) => {
          const Layout = LAYOUT_COMPONENTS[
            section.shape as Exclude<typeof section.shape, "masthead">
          ];
          if (!Layout) return null;
          return (
            // scroll-mt clears the sticky header: without it an in-page nav
            // link lands with the section's heading hidden underneath it.
            <section
              key={section.id}
              id={section.id}
              data-emphasis={section.emphasis}
              data-layout={section.shape}
              className="scroll-mt-20"
            >
              <Layout section={section} index={i} />
            </section>
          );
        })}
      </main>
      <SiteFooter wordmark={wordmark} nav={nav}>
        {colophons.map((section, i) => {
          const Layout = LAYOUT_COMPONENTS.colophon;
          return (
            <div key={section.id} id={section.id} data-layout="colophon">
              <Layout section={section} index={i} />
            </div>
          );
        })}
      </SiteFooter>
    </SmoothScroll>
  );
}
