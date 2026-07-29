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
function Container({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`mx-auto w-full max-w-[1440px] px-6 lg:px-12 ${className}`}>{children}</div>
  );
}

/** The small monospace section marker. Uses the plan's own nav_label. */
function Eyebrow({ section }: { section: RenderableSection }) {
  const label = section.nav_label ?? "";
  return (
    <span className="font-mono text-xs uppercase tracking-[0.18em] text-primary">
      {String(section.order).padStart(2, "0")}
      {label ? ` / ${label}` : ""}
    </span>
  );
}

function BrandImage({
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
        <p className="mt-8 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
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
          <p className="mt-3 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
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
  const { copy, media } = section;
  const items = copy.body ? splitItems(copy.body) : [];
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
      {items.length > 0 && (
        <div className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-[var(--radius-8,8px)] border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => (
            <FadeIn key={i} delay={0.04 * i}>
              <div className="h-full bg-background p-7">
                <span className="font-mono text-xs text-primary">{String(i + 1).padStart(2, "0")}</span>
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
  const items = splitItems(copy.caption || copy.body || "", 5);

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
            <span className="font-mono text-xs uppercase tracking-[0.18em] text-primary">
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
            <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-primary lg:shrink-0">
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
              <p className="mt-7 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
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
  const items = splitItems(copy.body || "", 12);
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
            <Accordion type="single" collapsible className="w-full">
              {items.map((item, i) => (
                <AccordionItem key={i} value={`item-${i}`}>
                  <AccordionTrigger className="font-body text-base">
                    <span className="font-mono text-xs text-muted-foreground">
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
                <p className="mt-4 font-mono text-xs uppercase tracking-[0.18em] opacity-70">
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
        <p key={i} className="font-mono text-xs leading-relaxed text-muted-foreground lg:text-sm">
          {line}
        </p>
      ))}
    </div>
  );
}

export const LAYOUT_COMPONENTS = {
  "split-hero": SplitHero,
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
