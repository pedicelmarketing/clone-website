/**
 * Layout vocabulary — one component per `Layout` shape.
 *
 * Why this file exists
 * --------------------
 * The renderer previously had four "variants" (hero/primary/secondary/minor)
 * that all resolved to the same physical shape: a small eyebrow label in a
 * 4-column gutter, heading and body in the 8 beside it. Every section, every
 * page, every brand. The design pass was choosing structure and the renderer
 * had nowhere to put it, so the output looked templated no matter how good the
 * plan was.
 *
 * Two rules hold for every component here:
 *
 *  1. RENDER EVERY ROLE YOU ARE GIVEN. The old code hardcoded one role per
 *     variant, so a `secondary` section carrying a headline and body rendered
 *     neither — three sections shipped the literal string "[no body in plan]"
 *     and one shipped an 879px empty box. If a role is absent it is simply not
 *     drawn; nothing is ever invented to fill the gap.
 *  2. NEVER put a text colour on a background it was not checked against.
 *     Inverted bands use `bg-foreground text-background`, the one pair
 *     synthesize_tokens guarantees ≥4.5:1. Brand `--color-muted` is a real
 *     brand colour and can be strongly saturated (one brand's was green), so it
 *     is never used behind copy.
 */

import type { ReactNode } from "react";
import type { RenderableSection } from "@/lib/design-plan";
import { FadeIn, SignatureMark } from "@/components/motion-primitives";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export interface LayoutProps {
  section: RenderableSection;
  /** Position among body sections — used to alternate sides so repeated
   *  shapes do not read as a repeated template. */
  index: number;
}

/** Standard page gutter + max measure. */
export function Container({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`mx-auto w-full max-w-[1440px] px-6 lg:px-12 ${className}`}>{children}</div>
  );
}

/** The small monospace section marker. Uses the plan's own nav_label. */
export function Eyebrow({ section }: { section: RenderableSection }) {
  const label = section.nav_label ?? "";
  return (
    <span className="u-label text-primary">
      {String(section.order).padStart(2, "0")}
      {label ? ` / ${label}` : ""}
    </span>
  );
}

export function BrandImage({
  file, alt, className = "",
}: { file: string; alt: string; className?: string }) {
  // Plain <img>: the renderer builds with output:'export' + images.unoptimized,
  // so next/image would add machinery without optimising anything.
  return (
    <img
      src={`/brand/${file}`}
      alt={alt}
      loading="lazy"
      decoding="async"
      className={`w-full object-cover object-center ${className}`}
    />
  );
}

/**
 * Split a body string into discrete items for grid/row shapes.
 *
 * Sentence boundaries first, then commas as a fallback: a services list is
 * written as one comma-separated sentence ("Social Media Marketing, Community
 * Management, Branding Strategy, …"), and splitting only on sentences left it
 * as a single run-on accordion row instead of eight chapters.
 */
function splitItems(text: string, max = 8): string[] {
  let parts = text
    .split(/\s*[|•]\s*|(?<=[.!?])\s+/)
    .map((t) => t.trim())
    .filter((t) => t.length > 1);
  if (parts.length < 2 && (text.match(/,/g) ?? []).length >= 2) {
    parts = text.split(/\s*,\s*/).map((t) => t.trim()).filter((t) => t.length > 1);
  }
  return parts.slice(0, max);
}

/**
 * Items for a list-shaped layout.
 *
 * Prefers REPEATED copy blocks of the same role — the design pass writes a
 * services list as N separate `headline` blocks, and those are real authored
 * strings that must not be thrown away. Falls back to splitting a single body
 * string only when no repetition exists.
 */
export function itemsFor(section: RenderableSection, max = 8): string[] {
  const H = (section.copyList?.headline ?? []).filter(Boolean);
  const B = (section.copyList?.body ?? []).filter(Boolean);

  // Which role carries the items depends on how the plan wrote the section.
  //
  //  - Several HEADLINES => headline[0] is the section title and the rest are
  //    the items (their bodies, if any, are the items' descriptions).
  //  - One headline but several BODIES => the headline is the title and EVERY
  //    body is an item. Blindly dropping body[0] here silently deleted the
  //    first of four programme formats and the first of five engagement
  //    stages — the exact class of defect Gate 11 exists to catch, and it did.
  if (H.length > 1) return H.slice(1, max + 1);
  if (B.length > 1) return B.slice(0, max);
  return splitItems(section.copy.body || "", max);
}

// ---------------------------------------------------------------------------
// split-hero — the opening statement
// ---------------------------------------------------------------------------

export function SplitHero({ section }: LayoutProps) {
  const { copy, media } = section;
  return (
    <Container className="py-20 lg:py-28">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-12 lg:gap-10 xl:gap-14">
        <div className="lg:col-span-7">
          <FadeIn>
            {copy.headline && (
              <h1 className="font-display text-[clamp(2.75rem,6vw,5.5rem)] leading-[0.98] tracking-[-0.02em] text-foreground">
                {copy.headline}
              </h1>
            )}
            {copy.subhead && (
              <p className="mt-7 max-w-[46ch] font-body text-lg leading-relaxed text-muted-foreground lg:text-2xl">
                {copy.subhead}
              </p>
            )}
            {copy.body && (
              <p className="mt-5 max-w-[52ch] font-body text-base leading-relaxed text-foreground">
                {copy.body}
              </p>
            )}
            {copy.cta && (
              <div className="mt-10">
                <Button size="lg">{copy.cta}</Button>
              </div>
            )}
          </FadeIn>
        </div>
        <div className="lg:col-span-5">
          <FadeIn delay={0.08}>
            {media ? (
              <BrandImage file={media.file} alt={media.alt}
                className="aspect-[4/5] max-h-[560px] rounded-[var(--radius-8,8px)]" />
            ) : (
              <SignatureMark />
            )}
          </FadeIn>
        </div>
      </div>
      {copy.caption && (
        <p className="mt-8 u-label text-muted-foreground">
          {copy.caption}
        </p>
      )}
    </Container>
  );
}

// ---------------------------------------------------------------------------
// editorial — numbered index beside running body
// ---------------------------------------------------------------------------

export function Editorial({ section }: LayoutProps) {
  const { copy, media } = section;
  return (
    <Container className="border-t border-border py-20 lg:py-28">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-8 xl:gap-12">
        <div className="lg:col-span-3">
          <FadeIn><Eyebrow section={section} /></FadeIn>
        </div>
        <div className="lg:col-span-9">
          <FadeIn delay={0.06}>
            {copy.headline && (
              <h2 className="max-w-[20ch] font-display text-4xl leading-[1.08] tracking-[-0.01em] text-foreground lg:text-6xl">
                {copy.headline}
              </h2>
            )}
            {copy.subhead && (
              <p className="mt-5 max-w-[60ch] font-body text-xl leading-relaxed text-muted-foreground">
                {copy.subhead}
              </p>
            )}
            {copy.body && (
              <p className="mt-6 max-w-[65ch] font-body text-lg leading-[1.7] text-foreground">
                {copy.body}
              </p>
            )}
            {media && (
              <div className="mt-12">
                <BrandImage file={media.file} alt={media.alt}
                  className="aspect-[16/9] max-h-[460px] rounded-[var(--radius-8,8px)]" />
              </div>
            )}
            {copy.caption && (
              <p className="mt-4 font-body text-sm italic text-muted-foreground">{copy.caption}</p>
            )}
            {copy.cta && <div className="mt-8"><Button>{copy.cta}</Button></div>}
          </FadeIn>
        </div>
      </div>
    </Container>
  );
}

// ---------------------------------------------------------------------------
// feature-split — photo one side, text the other, alternating
// ---------------------------------------------------------------------------

export function FeatureSplit({ section, index }: LayoutProps) {
  const { copy, media } = section;
  const flip = index % 2 === 1;
  return (
    <Container className="py-20 lg:py-28">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-12 lg:gap-12">
        <div className={`lg:col-span-6 ${flip ? "lg:order-2" : ""}`}>
          <FadeIn>
            {media ? (
              <BrandImage file={media.file} alt={media.alt}
                className="aspect-[4/5] max-h-[560px] rounded-[var(--radius-8,8px)]" />
            ) : (
              <SignatureMark />
            )}
          </FadeIn>
        </div>
        <div className={`lg:col-span-6 ${flip ? "lg:order-1" : ""}`}>
          <FadeIn delay={0.06}>
            <Eyebrow section={section} />
            {copy.headline && (
              <h2 className="mt-5 max-w-[18ch] font-display text-4xl leading-[1.08] text-foreground lg:text-5xl">
                {copy.headline}
              </h2>
            )}
            {copy.subhead && (
              <p className="mt-4 max-w-[46ch] font-body text-lg text-muted-foreground">{copy.subhead}</p>
            )}
            {copy.body && (
              <p className="mt-5 max-w-[52ch] font-body text-lg leading-[1.7] text-foreground">
                {copy.body}
              </p>
            )}
            {copy.caption && (
              <p className="mt-4 font-body text-sm italic text-muted-foreground">{copy.caption}</p>
            )}
            {copy.cta && <div className="mt-8"><Button>{copy.cta}</Button></div>}
          </FadeIn>
        </div>
      </div>
    </Container>
  );
}

// ---------------------------------------------------------------------------
// full-bleed-band — image edge to edge
// ---------------------------------------------------------------------------

export function FullBleedBand({ section }: LayoutProps) {
  const { copy, media } = section;
  return (
    <section className="py-16 lg:py-24">
      <Container className="mb-8">
        <FadeIn>
          <Eyebrow section={section} />
          {copy.headline && (
            <h2 className="mt-4 max-w-[24ch] font-display text-3xl leading-[1.1] text-foreground lg:text-5xl">
              {copy.headline}
            </h2>
          )}
          {copy.subhead && (
            <p className="mt-4 max-w-[60ch] font-body text-lg text-muted-foreground">{copy.subhead}</p>
          )}
        </FadeIn>
      </Container>
      {media && (
        <FadeIn delay={0.06}>
          <BrandImage file={media.file} alt={media.alt} className="h-[clamp(260px,42vw,520px)]" />
        </FadeIn>
      )}
      <Container className="mt-6">
        {copy.body && (
          <p className="max-w-[65ch] font-body text-lg leading-[1.7] text-foreground">{copy.body}</p>
        )}
        {copy.caption && (
          <p className="mt-3 u-label text-muted-foreground">
            {copy.caption}
          </p>
        )}
      </Container>
    </section>
  );
}

// ---------------------------------------------------------------------------
// card-grid — body split into cards, or a grid of photos
// ---------------------------------------------------------------------------

export function CardGrid({ section }: LayoutProps) {
  const { copy, media, copyList } = section;
  // Paired title+description cards when the plan repeats BOTH roles — that is
  // how a services section is actually written (six names, six descriptions).
  // Rendering only the names would drop half the authored copy.
  const allTitles = copyList?.headline ?? [];
  const allBodies = copyList?.body ?? [];
  // headline[0] / body[0] are the SECTION's own title and intro; the remainder
  // are the cards. Aligning on slice(1) of both keeps each description with its
  // own title — slicing them differently silently dropped the last pair.
  const titles = allTitles.slice(1);
  const bodies = allBodies.length === allTitles.length
    ? allBodies.slice(1)
    : allBodies.slice(Math.max(0, allBodies.length - titles.length));
  const paired = titles.length >= 2 && bodies.length >= titles.length
    ? titles.map((t, i) => ({ title: t, desc: bodies[i] }))
    : null;
  const items = paired ? [] : itemsFor(section);
  return (
    <Container className="border-t border-border py-20 lg:py-28">
      <FadeIn>
        <Eyebrow section={section} />
        {copy.headline && (
          <h2 className="mt-4 max-w-[22ch] font-display text-4xl leading-[1.08] text-foreground lg:text-5xl">
            {copy.headline}
          </h2>
        )}
        {copy.subhead && (
          <p className="mt-4 max-w-[60ch] font-body text-lg text-muted-foreground">{copy.subhead}</p>
        )}
      </FadeIn>
      {/* Bordered cards with a real gap, NOT a `gap-px` + `bg-border` hairline
       *  trick. That trick paints the container's background through every cell
       *  the items do not fill: seven mixers in a three-column grid left two
       *  empty cells rendering as solid blocks of the brand's border colour — a
       *  green rectangle sitting in the middle of the lineup. */}
      {paired && (
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {paired.map((card, i) => (
            <FadeIn key={i} delay={0.04 * i}>
              <div className="h-full rounded-[var(--radius-8,8px)] border border-border bg-background p-7">
                <span className="u-label text-primary">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="mt-3 font-display text-xl leading-snug text-foreground">{card.title}</h3>
                {card.desc && (
                  <p className="mt-2 font-body text-sm leading-relaxed text-muted-foreground">{card.desc}</p>
                )}
              </div>
            </FadeIn>
          ))}
        </div>
      )}
      {items.length > 0 && (
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => (
            <FadeIn key={i} delay={0.04 * i}>
              <div className="h-full rounded-[var(--radius-8,8px)] border border-border bg-background p-7">
                <span className="u-label text-primary">{String(i + 1).padStart(2, "0")}</span>
                <p className="mt-3 font-body text-base leading-relaxed text-foreground">{item}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      )}
      {media && (
        <div className="mt-10">
          <FadeIn delay={0.06}>
            <BrandImage file={media.file} alt={media.alt}
              className="aspect-[21/9] max-h-[380px] rounded-[var(--radius-8,8px)]" />
          </FadeIn>
        </div>
      )}
      {copy.caption && (
        <p className="mt-4 font-body text-sm italic text-muted-foreground">{copy.caption}</p>
      )}
      {copy.cta && <div className="mt-8"><Button>{copy.cta}</Button></div>}
    </Container>
  );
}

// ---------------------------------------------------------------------------
// proof-row — compact horizontal row of short proof items
// ---------------------------------------------------------------------------

export function ProofRow({ section }: LayoutProps) {
  const { copy } = section;
  const repeated = itemsFor(section, 5);
  const items = repeated.length >= 2 ? repeated : splitItems(copy.caption || copy.body || "", 5);

  // A row needs things to put in a row. When the plan supplies a single
  // sentence, the list rendering degrades into one stranded right-aligned line,
  // so present it as the statement it actually is instead.
  if (items.length < 2) {
    const statement = copy.caption || copy.body || copy.headline;
    if (!statement) return null;
    return (
      <Container className="border-y border-border py-14 lg:py-20">
        <FadeIn>
          {copy.headline && items.length > 0 && (
            <span className="u-label text-primary">
              {copy.headline}
            </span>
          )}
          <p className="mt-3 max-w-[38ch] font-display text-2xl leading-[1.25] text-foreground lg:text-3xl">
            {statement}
          </p>
        </FadeIn>
      </Container>
    );
  }

  return (
    <Container className="border-y border-border py-10 lg:py-14">
      <FadeIn>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-baseline lg:justify-between lg:gap-10">
          {copy.headline && (
            <h2 className="u-label text-primary lg:shrink-0">
              {copy.headline}
            </h2>
          )}
          <ul className="flex flex-col gap-4 lg:flex-1 lg:flex-row lg:flex-wrap lg:justify-end lg:gap-10">
            {items.map((item, i) => (
              <li key={i} className="font-body text-sm leading-snug text-foreground lg:max-w-[24ch]">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </FadeIn>
    </Container>
  );
}

// ---------------------------------------------------------------------------
// pull-quote — one oversized statement
// ---------------------------------------------------------------------------

export function PullQuote({ section }: LayoutProps) {
  const { copy } = section;
  const quote = copy.body || copy.headline || "";
  const attribution = copy.body ? copy.headline : undefined;
  return (
    <Container className="py-24 lg:py-36">
      <div className="grid grid-cols-1 lg:grid-cols-12">
        <div className="lg:col-start-2 lg:col-span-10">
          <FadeIn>
            <span aria-hidden="true" className="block font-display text-6xl leading-none text-primary">
              &ldquo;
            </span>
            <blockquote className="mt-2 max-w-[24ch] font-display text-[clamp(1.75rem,3.6vw,3.25rem)] leading-[1.12] tracking-[-0.01em] text-foreground">
              {quote}
            </blockquote>
            {attribution && (
              <p className="mt-7 u-label text-muted-foreground">
                {attribution}
              </p>
            )}
            {copy.caption && (
              <p className="mt-3 font-body text-sm italic text-muted-foreground">{copy.caption}</p>
            )}
          </FadeIn>
        </div>
      </div>
    </Container>
  );
}

// ---------------------------------------------------------------------------
// index-list — numbered, expandable
// ---------------------------------------------------------------------------

export function IndexList({ section }: LayoutProps) {
  const { copy } = section;
  const items = itemsFor(section, 12);
  return (
    <Container className="border-t border-border py-20 lg:py-28">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-12">
        <div className="lg:col-span-4">
          <FadeIn>
            <Eyebrow section={section} />
            {copy.headline && (
              <h2 className="mt-4 max-w-[16ch] font-display text-3xl leading-[1.1] text-foreground lg:text-4xl">
                {copy.headline}
              </h2>
            )}
            {copy.subhead && (
              <p className="mt-4 font-body text-base text-muted-foreground">{copy.subhead}</p>
            )}
          </FadeIn>
        </div>
        <div className="lg:col-span-8">
          <FadeIn delay={0.06}>
            <Accordion className="w-full">
              {items.map((item, i) => (
                <AccordionItem key={i}>
                  <AccordionTrigger className="font-body text-base">
                    <span className="u-label text-primary">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="ml-4 text-left">{item}</span>
                  </AccordionTrigger>
                  {/* No per-item copy exists in the plan; render nothing rather
                   *  than leaking plan metadata as if it were brand content. */}
                  <AccordionContent />
                </AccordionItem>
              ))}
            </Accordion>
            {copy.caption && (
              <p className="mt-6 font-body text-sm italic text-muted-foreground">{copy.caption}</p>
            )}
          </FadeIn>
        </div>
      </div>
    </Container>
  );
}

// ---------------------------------------------------------------------------
// cta-band — inverted colour band
// ---------------------------------------------------------------------------

export function CtaBand({ section }: LayoutProps) {
  const { copy } = section;
  // bg-foreground/text-background is the one pair synthesize_tokens guarantees
  // meets 4.5:1 for this brand. Do not swap in a brand accent here without
  // re-deriving contrast — that is how the invisible-text class of bug starts.
  return (
    <section className="bg-foreground py-20 text-background lg:py-28">
      <Container>
        <div className="grid grid-cols-1 items-end gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <FadeIn>
              {copy.headline && (
                <h2 className="max-w-[20ch] font-display text-4xl leading-[1.08] lg:text-6xl">
                  {copy.headline}
                </h2>
              )}
              {copy.body && (
                <p className="mt-6 max-w-[52ch] font-body text-lg leading-relaxed opacity-80">
                  {copy.body}
                </p>
              )}
              {copy.subhead && (
                <p className="mt-3 max-w-[52ch] font-body text-base opacity-70">{copy.subhead}</p>
              )}
            </FadeIn>
          </div>
          <div className="lg:col-span-4 lg:text-right">
            <FadeIn delay={0.08}>
              {copy.cta && <Button size="lg">{copy.cta}</Button>}
              {copy.caption && (
                <p className="mt-4 u-label opacity-70">
                  {copy.caption}
                </p>
              )}
            </FadeIn>
          </div>
        </div>
      </Container>
    </section>
  );
}

// ---------------------------------------------------------------------------
// colophon — thin monospace strip (rendered inside <footer>)
// ---------------------------------------------------------------------------

export function Colophon({ section }: LayoutProps) {
  const { copy } = section;
  const lines = [copy.headline, copy.subhead, copy.body, copy.caption].filter(Boolean) as string[];
  if (lines.length === 0) return null;
  return (
    <div className="border-t border-border py-8">
      {lines.map((line, i) => (
        <p key={i} className="u-label leading-relaxed text-foreground/70">
          {line}
        </p>
      ))}
    </div>
  );
}

import { ScrollRail, GhostIndex, CardCarousel } from "@/components/layouts-interactive";

export const LAYOUT_COMPONENTS = {
  "split-hero": SplitHero,
  "type-hero": TypeHero,
  "scroll-rail": ScrollRail,
  "label-rail": LabelRailCard,
  "ghost-index": GhostIndex,
  "card-carousel": CardCarousel,
  "marquee-band": MarqueeBand,
  "contact-panel": ContactPanel,
  editorial: Editorial,
  "feature-split": FeatureSplit,
  "full-bleed-band": FullBleedBand,
  "card-grid": CardGrid,
  "proof-row": ProofRow,
  "pull-quote": PullQuote,
  "index-list": IndexList,
  "cta-band": CtaBand,
  colophon: Colophon,
} as const;

// ===========================================================================
// HARVESTED LAYOUTS
// ---------------------------------------------------------------------------
// Geometry below was measured from a reference site and rebuilt from those
// measurements. No markup, styling, imagery, type or colour was copied — what
// transfers is structure, which is the part that generalises across brands.
//
// A THIRD rule applies to every component here, on top of the two in this
// file's header:
//
//   3. NOTHING MAY BE CONDITIONALLY RENDERED OUT OF THE DOM. Gate 11 reads the
//      exported HTML. A carousel that mounts only the active slide, or an
//      accordion that mounts content on open, silently drops real copy from a
//      static export. Hide inactive state with opacity/transform — never `&&`.
// ===========================================================================

/**
 * type-hero — a full-height opening built from type alone.
 *
 * The harvested idea is that hierarchy can come from a 12-step opacity ladder
 * on ONE ink rather than from a palette: the operative words sit at full
 * strength and the connective words drop back, so a single colour does the work
 * of three. That is what lets this carry a hero with no photograph at all —
 * which matters, because a full-bleed image is the most unforgiving placement
 * on a site and a weak one fails there and nowhere else.
 *
 * The headline is split on a `|` if the plan supplies one, so the design pass
 * controls which words are emphasised without any markup in the copy.
 */
export function TypeHero({ section }: LayoutProps) {
  const { copy } = section;
  const parts = (copy.headline ?? "").split("|").map((t) => t.trim()).filter(Boolean);
  return (
    <Container className="flex min-h-[88svh] flex-col justify-center py-24 lg:py-32">
      <div className="grid grid-cols-1 items-end gap-12 lg:grid-cols-12">
        <div className="lg:col-span-9">
          <FadeIn>
            {section.nav_label && (
              <span className="u-label text-primary">{section.nav_label}</span>
            )}
            {parts.length > 0 && (
              <h1 className="mt-7 font-display text-[clamp(2.5rem,8vw,7.5rem)] leading-[0.92] tracking-[-0.03em] text-foreground">
                {parts.map((line, i) => (
                  <span key={i} className={i % 2 === 1 ? "block text-foreground/45" : "block"}>
                    {line}
                  </span>
                ))}
              </h1>
            )}
          </FadeIn>
        </div>
        <div className="lg:col-span-3">
          <FadeIn delay={0.1}>
            <SignatureMark variant="monogram" />
          </FadeIn>
        </div>
      </div>
      <FadeIn delay={0.16}>
        <div className="mt-14 h-px w-full bg-primary/40" />
        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="lg:col-span-7">
            {copy.subhead && (
              <p className="max-w-[52ch] font-body text-lg leading-relaxed text-foreground/70 lg:text-xl">
                {copy.subhead}
              </p>
            )}
            {copy.body && (
              <p className="mt-5 max-w-[56ch] font-body text-base leading-relaxed text-foreground/70">
                {copy.body}
              </p>
            )}
          </div>
          <div className="flex items-start gap-3 lg:col-span-5 lg:justify-end">
            {copy.cta && <Button size="lg">{copy.cta}</Button>}
            {copy.caption && (
              <span className="u-label self-center text-foreground/70">{copy.caption}</span>
            )}
          </div>
        </div>
      </FadeIn>
    </Container>
  );
}

/**
 * marquee-band — the page's only luminance inversion.
 *
 * Harvested as a *rule*, not as content: one full-bleed inverted strip between
 * movements does more separating work than a border ever will, and costs one
 * element. Uses `bg-foreground text-background`, the one pair
 * synthesize_tokens guarantees at >=4.5:1.
 *
 * Pure CSS, so zero JS. The animation is genuinely disabled under
 * prefers-reduced-motion (see globals.css) — Gate 7 only checks that a
 * reduced-motion block EXISTS, so this one has to be right by construction.
 */
export function MarqueeBand({ section }: LayoutProps) {
  const { copy } = section;
  const words = itemsFor(section, 6);
  const line = words.length >= 2 ? words : [copy.headline ?? ""].filter(Boolean);
  if (line.length === 0) return null;
  const group = (
    <div className="marquee-group flex shrink-0 items-center gap-8 pr-8" aria-hidden="true">
      {line.map((w, i) => (
        <span key={i} className="flex items-center gap-8 font-display text-3xl whitespace-nowrap lg:text-5xl">
          {w}
          <span className="text-background/40">/</span>
        </span>
      ))}
    </div>
  );
  return (
    <div className="w-full overflow-hidden bg-foreground py-6 text-background">
      {/* Screen readers get the list once, as text; the duplicated visual
       *  groups are aria-hidden so the loop is not announced twice. */}
      <span className="sr-only">{line.join(", ")}</span>
      <div className="marquee-track flex w-max flex-nowrap">
        {group}
        {group}
      </div>
    </div>
  );
}

/**
 * label-rail — an asymmetric row: narrow label rail beside a surfaced card.
 *
 * The measured split is 240 / 790 inside a 1274 container with
 * `justify-between`, which leaves ~244px of empty middle. That gap is the whole
 * point: it makes a 19/62 split read as a deliberate composition rather than a
 * broken thirds grid. Reproduced proportionally rather than in fixed pixels so
 * it holds at other container widths.
 */
export function LabelRailCard({ section }: LayoutProps) {
  const { copy, media } = section;
  const items = itemsFor(section, 6);
  return (
    <Container className="py-20 lg:py-28">
      <div className="flex flex-col gap-12 lg:flex-row lg:items-start lg:justify-between lg:gap-16">
        <div className="shrink-0 lg:w-[240px] lg:pt-1">
          <FadeIn>
            {copy.headline && (
              <h2 className="font-display text-4xl leading-[0.95] tracking-[-0.02em] text-foreground lg:text-6xl">
                {copy.headline}
              </h2>
            )}
            {items.length > 0 && (
              <ul className="mt-8 flex flex-col gap-0.5">
                {items.map((item, i) => (
                  <li
                    key={i}
                    className="flex items-baseline gap-3 border-b border-foreground/10 py-2.5 font-body text-sm text-foreground/70"
                  >
                    <span className="u-label text-primary">{String(i + 1).padStart(2, "0")}</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            )}
          </FadeIn>
        </div>
        <div className="w-full lg:max-w-[790px] lg:flex-1">
          <FadeIn delay={0.08}>
            <div className="dotted-card relative overflow-hidden rounded-[20px] p-8 md:p-11">
              {copy.subhead && (
                <p className="font-display text-2xl leading-[1.28] tracking-[-0.01em] text-foreground lg:text-[2.6rem]">
                  {copy.subhead}
                </p>
              )}
              {copy.body && (
                <p className="mt-6 max-w-[60ch] font-body text-base leading-[1.7] text-foreground/70 lg:text-lg">
                  {copy.body}
                </p>
              )}
              {media && (
                <div className="mt-8 max-w-[320px]">
                  <BrandImage
                    file={media.file}
                    alt={media.alt}
                    className="aspect-[4/3] rounded-[12px]"
                  />
                </div>
              )}
              {copy.caption && (
                <p className="mt-5 font-body text-sm italic text-foreground/70">{copy.caption}</p>
              )}
              {copy.cta && <div className="mt-8"><Button>{copy.cta}</Button></div>}
            </div>
          </FadeIn>
        </div>
      </div>
    </Container>
  );
}

/**
 * contact-panel — address, location and (only with a real endpoint) a form.
 *
 * Under a static export there is no server to POST to, so a form needs an
 * external endpoint. We do not have one, and there is no phone number anywhere
 * in the client's source material either — so a `wa.me/` link would mean
 * inventing a number. The published email address is real, so that is what
 * ships. The gap is recorded in the plan's skipped_sections rather than papered
 * over with a form that silently goes nowhere.
 */
export function ContactPanel({ section }: LayoutProps) {
  const { copy } = section;
  const details = itemsFor(section, 8);
  const email = copy.cta && copy.cta.includes("@") ? copy.cta : null;
  return (
    <Container className="py-24 lg:py-36">
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <FadeIn>
            {copy.headline && (
              <h2 className="max-w-[16ch] font-display text-[clamp(2.25rem,6vw,4.5rem)] leading-[0.95] tracking-[-0.03em] text-foreground">
                {copy.headline}
              </h2>
            )}
            {copy.subhead && (
              <p className="mt-6 max-w-[50ch] font-body text-lg leading-relaxed text-foreground/70">
                {copy.subhead}
              </p>
            )}
            {email && (
              <a
                href={`mailto:${email}?subject=${encodeURIComponent("Enquiry from the website")}`}
                className="mt-10 inline-block font-display text-2xl tracking-[-0.01em] text-foreground underline decoration-primary decoration-2 underline-offset-[6px] transition-opacity hover:opacity-70 lg:text-4xl"
              >
                {email}
              </a>
            )}
          </FadeIn>
        </div>
        <div className="lg:col-span-5">
          <FadeIn delay={0.08}>
            {copy.body && (
              <p className="max-w-[40ch] font-body text-base leading-relaxed text-foreground/70">
                {copy.body}
              </p>
            )}
            {details.length > 0 && (
              <ul className="mt-8 flex flex-col">
                {details.map((d, i) => (
                  <li
                    key={i}
                    className="border-t border-foreground/10 py-4 font-body text-sm text-foreground/70"
                  >
                    {d}
                  </li>
                ))}
              </ul>
            )}
            {copy.caption && (
              <p className="mt-6 u-label text-foreground/70">{copy.caption}</p>
            )}
          </FadeIn>
        </div>
      </div>
    </Container>
  );
}
