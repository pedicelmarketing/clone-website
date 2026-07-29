/**
 * PageBody — renders ONE page of the design plan.
 *
 * Shared by `app/page.tsx` (home) and `app/[slug]/page.tsx` (everything else).
 * Sharing it is not just tidiness: five separate route folders would emit five
 * separate page chunks, and Gate 10 caps the whole bundle at 300 KB gzipped.
 * One dynamic route plus this component means the layout vocabulary is compiled
 * once and shared across every route.
 *
 * Nav and footer are computed from `plan.pages[]` here, once, so every route
 * gets identical chrome by construction rather than by discipline. The only
 * per-route difference is which nav item is marked `aria-current`.
 */

import {
  getPageRegions, getPages, getSiteNav, loadBrandWordmark, routeForSlug,
  type DesignPlan,
} from "@/lib/design-plan";
import { LAYOUT_COMPONENTS } from "@/components/layouts";
import { PillNav, SiteFooter } from "@/components/site-chrome";
import { SmoothScroll } from "@/components/motion-primitives";

export function PageBody({ plan, slug }: { plan: DesignPlan; slug: string }) {
  const page = getPages(plan).find((p) => p.slug === slug) ?? getPages(plan)[0];
  const { masthead, body, colophons } = getPageRegions(plan, page.section_ids);
  const nav = getSiteNav(plan);

  const site = (plan as { site?: { wordmark?: string; tagline?: string | null } }).site;
  const wordmark = site?.wordmark ?? masthead?.copy.headline ?? loadBrandWordmark();
  const tagline = site?.tagline ?? masthead?.copy.subhead ?? null;

  return (
    <SmoothScroll>
      <div id="top" />
      <PillNav
        wordmark={wordmark}
        tagline={tagline}
        nav={nav}
        currentHref={routeForSlug(slug)}
      />
      <main className="min-h-screen bg-background text-foreground">
        {body.map((section, i) => {
          const Layout = LAYOUT_COMPONENTS[
            section.shape as Exclude<typeof section.shape, "masthead">
          ];
          if (!Layout) return null;
          return (
            // scroll-mt clears the fixed nav: without it an in-page anchor
            // lands with the section's heading hidden underneath it.
            <section
              key={section.id}
              id={section.id}
              data-emphasis={section.emphasis}
              data-layout={section.shape}
              className="scroll-mt-28"
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
