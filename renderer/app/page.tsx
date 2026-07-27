/**
 * Root page: renders the brand's re-versioned site directly from the
 * design plan. Every section comes from plan.sections[], every text
 * string comes from plan.copy_blocks[]. Skipped sections are filtered
 * out (see lib/design-plan.ts).
 *
 * No text is fabricated here. If a section has no copy_blocks entries,
 * the section is still rendered (so the gap is visible to the auditor)
 * but with an explicit "[no copy in plan]" placeholder rather than
 * invented content.
 */

import { getRenderableSections, loadDesignPlan } from "@/lib/design-plan";
import {
  Section,
  HeroLayout,
  PrimaryLayout,
  SecondaryLayout,
  MinorLayout,
  Cols7,
  Cols5,
  Cols4,
  Cols8,
  Cols3,
  OffsetRight9,
  Full,
} from "@/components/section";
import { FadeIn, GoldDotMarker, SmoothScroll } from "@/components/motion-primitives";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

// Server-side load. This runs at build time in Next 15 (App Router).
const plan = loadDesignPlan();
const sections = getRenderableSections(plan);

function chooseLayout(emphasis: string) {
  switch (emphasis) {
    case "hero":
      return HeroLayout;
    case "primary":
      return PrimaryLayout;
    case "secondary":
      return SecondaryLayout;
    case "minor":
      return MinorLayout;
    default:
      // Defensive: loadDesignPlan validates emphasis, so we never hit this.
      return PrimaryLayout;
  }
}

/**
 * Render a section's content. The variant tree is driven entirely by
 * the section's `emphasis` value so the layout primitives exercise
 * real column structure, not just font-size toggles.
 */
function SectionContent({
  section,
}: {
  section: ReturnType<typeof getRenderableSections>[number];
}) {
  const { emphasis, id, copy, purpose, component } = section;
  const Layout = chooseLayout(emphasis);

  // === hero (cover) ===
  if (emphasis === "hero") {
    return (
      <Layout>
        <Cols7>
          <FadeIn>
            <h1 className="font-display text-5xl leading-[1.05] tracking-tight text-foreground lg:text-7xl">
              {copy.headline ?? "[no headline in plan]"}
            </h1>
            {copy.subhead && (
              <p className="mt-8 max-w-prose font-body text-xl leading-relaxed text-muted-foreground lg:text-2xl">
                {copy.subhead}
              </p>
            )}
          </FadeIn>
        </Cols7>
        <Cols5>
          <FadeIn delay={0.08}>
            <div className="border-l border-border pl-6 text-sm leading-relaxed text-muted-foreground lg:pt-3">
              <span className="font-mono text-xs uppercase tracking-widest text-primary">
                {purpose.slice(0, 32)}
              </span>
              <p className="mt-3 font-body">{component}</p>
            </div>
          </FadeIn>
        </Cols5>
      </Layout>
    );
  }

  // === primary (manifesto / lesson / services) ===
  if (emphasis === "primary") {
    // Services-as-chapters is the only primary section that needs an
    // accordion; everything else is a wide-body editorial block with a
    // sticky-style left index.
    if (id === "services-as-chapters") {
      const chapterLines = (copy.body ?? "").split(/,\s*/).filter(Boolean);
      return (
        <Layout>
          <Cols4>
            <FadeIn>
              <h2 className="font-display text-3xl leading-tight text-foreground lg:text-4xl">
                {copy.headline ?? "[no headline in plan]"}
              </h2>
            </FadeIn>
          </Cols4>
          <Cols8>
            <FadeIn delay={0.06}>
              <Accordion type="single" collapsible className="w-full">
                {chapterLines.map((line, i) => (
                  <AccordionItem key={i} value={`ch-${i}`}>
                    <AccordionTrigger className="font-body text-base">
                      <span className="font-mono text-xs text-muted-foreground">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="ml-3">{line}</span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <p className="font-body text-sm text-muted-foreground">
                        {purpose}
                      </p>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </FadeIn>
          </Cols8>
        </Layout>
      );
    }
    // Generic primary: sticky left index + wide right body
    return (
      <Layout>
        <Cols4>
          <FadeIn>
            <span className="font-mono text-xs uppercase tracking-widest text-primary">
              {String(section.order).padStart(2, "0")} / {purpose.slice(0, 24)}
            </span>
          </FadeIn>
        </Cols4>
        <Cols8>
          <FadeIn delay={0.06}>
            <h2 className="font-display text-4xl leading-tight text-foreground lg:text-5xl">
              {copy.headline ?? "[no headline in plan]"}
            </h2>
            {copy.body && (
              <p className="mt-6 font-body text-lg leading-relaxed text-foreground lg:text-xl">
                {copy.body}
              </p>
            )}
            {copy.caption && (
              <p className="mt-4 font-body text-base italic text-muted-foreground">
                {copy.caption}
              </p>
            )}
          </FadeIn>
        </Cols8>
      </Layout>
    );
  }

  // === secondary (proof essay + CTA) ===
  if (emphasis === "secondary") {
    if (id === "lead-generation-cta") {
      return (
        <Layout>
          <Cols3 aria-hidden="true" />
          <OffsetRight9>
            <FadeIn>
              <p className="font-body text-2xl leading-snug text-foreground lg:text-3xl">
                {copy.body ?? "[no body in plan]"}
              </p>
              {copy.cta && (
                <div className="mt-10">
                  <Button size="lg">{copy.cta}</Button>
                </div>
              )}
            </FadeIn>
          </OffsetRight9>
        </Layout>
      );
    }
    // Annotated image essay stand-in
    return (
      <Layout>
        <Cols3>
          <FadeIn>
            <span className="font-mono text-xs uppercase tracking-widest text-primary">
              {purpose.slice(0, 28)}
            </span>
          </FadeIn>
        </Cols3>
        <OffsetRight9>
          <FadeIn delay={0.06}>
            <div className="aspect-[16/10] w-full rounded-8 border border-border bg-muted" />
            {copy.caption && (
              <p className="mt-4 font-body text-base italic text-muted-foreground">
                {copy.caption}
              </p>
            )}
          </FadeIn>
        </OffsetRight9>
      </Layout>
    );
  }

  // === minor (colophon) ===
  return (
    <Layout>
      <Full>
        <FadeIn>
          <p className="font-mono text-xs leading-relaxed text-muted-foreground lg:text-sm">
            {copy.body ?? "[no body in plan]"}
          </p>
        </FadeIn>
      </Full>
    </Layout>
  );
}

export default function Home() {
  return (
    <SmoothScroll>
      <main className="min-h-screen bg-background text-foreground">
        <GoldDotMarker />
        {sections.map((s) => (
          <Section key={s.id} id={s.id} emphasis={s.emphasis}>
            <SectionContent section={s} />
          </Section>
        ))}
      </main>
    </SmoothScroll>
  );
}