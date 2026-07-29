/**
 * Build-time loader for the synthesized design plan.
 *
 * Reads reports/m6-design/design-plan.json (relative to the repo root) at
 * module-evaluation time. Next.js bundles this into the server output, so
 * the plan never needs to be present at runtime in production.
 *
 * Invariants enforced here:
 *  - We render ONLY sections in plan.sections whose `id` is NOT in
 *    plan.skipped_sections[].id. Skipped sections stay in the plan (the
 *    audit trail matters) but are never rendered.
 *  - Sections are emitted in `plan.sections[i].order` ascending, NEVER in
 *    the order they appear in `copy_blocks[]`.
 *  - Text content for every section is taken from plan.copy_blocks[]. A
 *    section that exists in `sections[]` but has no copy_blocks entries is
 *    rendered with an explicit empty-content placeholder, NEVER fabricated.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// design-plan.json is colocated with the rest of the reports/ tree, two
// directories up from renderer/.
// Overridable so the renderer is not welded to a single brand. render_nextjs.py
// sets WEB_DESIGNER_DESIGN_PLAN from its --design-plan argument. Hardcoding this
// meant every brand rendered the FIRST brand's plan — invisible until a second
// brand was run through the pipeline.
const PLAN_PATH = process.env.WEB_DESIGNER_DESIGN_PLAN
  ? resolve(process.env.WEB_DESIGNER_DESIGN_PLAN)
  : resolve(process.cwd(), "..", "reports", "m6-design", "design-plan.json");

export type Emphasis = "hero" | "primary" | "secondary" | "minor";

/**
 * The brand's own domain, used as a wordmark when the plan has no masthead
 * section to supply one.
 *
 * Deliberately returns the bare hostname rather than trying to prettify it.
 * Turning "pedicelmarketing.com" into "Pedicel Marketing" means guessing word
 * boundaries, and a guessed brand name is exactly the kind of invented fact the
 * pipeline forbids everywhere else. A domain is something the brand actually
 * published. Returns null when the brief is unavailable — a header with no
 * wordmark is better than a fabricated one.
 */
export function loadBrandWordmark(): string | null {
  const briefPath = process.env.WEB_DESIGNER_BRAND_BRIEF;
  if (!briefPath) return null;
  try {
    const brief = JSON.parse(readFileSync(resolve(briefPath), "utf8"));
    const url: string | undefined = brief?.sources?.own_site?.url;
    if (!url) return null;
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

/**
 * The section's LAYOUT SHAPE — what it physically looks like.
 *
 * `emphasis` only ever set scale/weight, so four emphases collapsed into one
 * repeated shape: eyebrow label in a side column, heading and body beside it,
 * on every section of every page. The design pass was making real structural
 * decisions (in prose, in `component`) that the renderer had nowhere to put.
 */
export type Layout =
  | "masthead"
  | "split-hero"
  | "editorial"
  | "feature-split"
  | "full-bleed-band"
  | "card-grid"
  | "proof-row"
  | "pull-quote"
  | "index-list"
  | "cta-band"
  | "colophon";

const LAYOUTS: Layout[] = [
  "masthead", "split-hero", "editorial", "feature-split", "full-bleed-band",
  "card-grid", "proof-row", "pull-quote", "index-list", "cta-band", "colophon",
];

/**
 * Infer a layout for plans written before `layout` existed.
 *
 * The design pass has always described the structure it wanted in the
 * `component` prose field ("annotated image essay", "services as chapters",
 * "sticky index"). That intent was being thrown away. Reading it here means
 * existing plans render with real variety without being regenerated — and a
 * plan that states `layout` explicitly always wins over this guess.
 */
const LAYOUT_PATTERNS: [Layout, RegExp][] = [
  ["masthead", /masthead|wordmark|brand[- ]bar|site[- ]header/],
  ["colophon", /colophon|legal|disclosure|fine[- ]print|footer/],
  ["pull-quote", /quote|testimonial|manifesto|creed/],
  ["proof-row", /award|press|accolade|proof|stat[-s ]|logo[- ]strip/],
  ["index-list", /accordion|chapter|curriculum|faq|index/],
  ["cta-band", /\bcta\b|call[- ]to[- ]action|shop|buy|contact|book/],
  ["card-grid", /grid|cards?|recipes?|tiles/],
  ["full-bleed-band", /full.?bleed|spread|banner/],
];

/**
 * Design prose is full of NEGATIONS — "no price badge", "no rounded badges",
 * "instead of icons". Naive keyword matching read those as positives and
 * collapsed five different sections onto the same layout.
 */
const NEGATION = /\b(?:no|without|not|never|avoid|instead of)\s+(?:\w+\s+){0,2}/g;

function matchLayout(text: string): Layout | null {
  const cleaned = text.toLowerCase().replace(NEGATION, " ");
  for (const [layout, pattern] of LAYOUT_PATTERNS) {
    if (pattern.test(cleaned)) return layout;
  }
  return null;
}

export function resolveLayout(s: PlanSection): Layout {
  if (s.layout && LAYOUTS.includes(s.layout)) return s.layout;

  // The id is the section's identity and outranks its description: "manifesto"
  // resolved to index-list purely because its prose mentioned a "sticky index".
  const byId = matchLayout(s.id);
  if (byId) return byId;

  // Only the FIRST clause of `component` names the shape; the rest is prose.
  const lead = s.component.split(/[.;]/)[0].slice(0, 90);
  const byProse = matchLayout(lead);
  if (byProse) return byProse;

  if (s.emphasis === "hero") return "split-hero";
  const treatment = s.media?.treatment;
  if (s.media) {
    if (treatment === "grid") return "card-grid";
    if (treatment === "full-bleed") return "full-bleed-band";
    return "feature-split";
  }
  if (s.emphasis === "minor") return "colophon";
  return "editorial";
}

export interface CopyBlock {
  section_id: string;
  role: string;
  text: string;
  source_brief_fields: string[];
}

export interface PlanSection {
  id: string;
  order: number;
  nav_label: string | null;
  in_nav: boolean;
  purpose: string;
  component: string;
  emphasis: Emphasis;
  /** Optional explicit layout shape. When absent, resolveLayout() infers one
   *  from the section's own `component` prose (see resolveLayout). */
  layout?: Layout;
  source_brief_fields: string[];
  rationale: string;
  /** Optional brand photograph placed by the design pass. `file` is always a
   *  filename that exists in public/brand (validated in design_pass.py against
   *  the fetched ASSET-MANIFEST.json), never an invented name or stock URL. */
  media?: {
    file: string;
    alt: string;
    treatment?: "full-bleed" | "inset" | "side-by-side" | "grid" | "background" | "portrait";
    rationale?: string;
  } | null;
}

export interface SkippedSection {
  id: string;
  reason: string;
  missing_brief_fields?: string[];
}

export interface DesignPlan {
  schema_version: string;
  project_slug: string;
  generated_at: string;
  sections: PlanSection[];
  copy_blocks: CopyBlock[];
  skipped_sections: SkippedSection[];
  // The remaining top-level keys are passed through but not required by the
  // renderer: signature_element, motion_vocabulary, layout_thesis, decisions,
  // model. They inform design intent but do not change the rendered layout.
  [extra: string]: unknown;
}

/**
 * Load + validate the design plan once at module load. Throws (and therefore
 * fails the build) if the plan is missing, malformed, or has unknown
 * emphasis values.
 */
export function loadDesignPlan(): DesignPlan {
  let raw: string;
  try {
    raw = readFileSync(PLAN_PATH, "utf8");
  } catch {
    throw new Error(
      `design-plan.json not found at ${PLAN_PATH}. ` +
        "Run skills/web-designer/scripts/design_pass.py first.",
    );
  }
  const plan = JSON.parse(raw) as DesignPlan;

  if (!Array.isArray(plan.sections)) {
    throw new Error("design-plan.json: missing `sections` array");
  }
  if (!Array.isArray(plan.copy_blocks)) {
    throw new Error("design-plan.json: missing `copy_blocks` array");
  }
  if (!Array.isArray(plan.skipped_sections)) {
    plan.skipped_sections = [];
  }
  for (const s of plan.sections) {
    const validEmphasis: Emphasis[] = ["hero", "primary", "secondary", "minor"];
    if (!validEmphasis.includes(s.emphasis)) {
      throw new Error(
        `design-plan.json: section "${s.id}" has unknown emphasis "${s.emphasis}"`,
      );
    }
  }
  return plan;
}

/**
 * Returns sections in render order with their copy_blocks grouped by role.
 * Skipped sections are excluded.
 */
export interface RenderableSection extends PlanSection {
  copy: Record<string, string>;
  /** Resolved layout — always set, never undefined, so no consumer has to guess. */
  shape: Layout;
}

export function getRenderableSections(
  plan: DesignPlan,
): RenderableSection[] {
  const skippedIds = new Set(plan.skipped_sections.map((s) => s.id));
  const copyBySection: Record<string, Record<string, string>> = {};
  for (const cb of plan.copy_blocks) {
    if (skippedIds.has(cb.section_id)) continue;
    if (!copyBySection[cb.section_id]) copyBySection[cb.section_id] = {};
    copyBySection[cb.section_id][cb.role] = cb.text;
  }
  return plan.sections
    .filter((s) => !skippedIds.has(s.id))
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((s) => ({
      ...s,
      copy: copyBySection[s.id] ?? {},
      shape: resolveLayout(s),
    }));
}

/**
 * Split the plan into the three regions a real page has.
 *
 * The output had zero <nav>, <header> and <footer> elements: every section was
 * rendered into one flat <main> stack, so the pages were a scroll of text
 * blocks rather than a site. The plan already carries everything needed to fix
 * that — `in_nav` and `nav_label` per section (both computed by the design pass
 * and `in_nav` previously ignored outright), plus a masthead section whose
 * headline is the brand's own wordmark.
 */
export interface PageRegions {
  masthead: RenderableSection | null;
  body: RenderableSection[];
  colophons: RenderableSection[];
  nav: { id: string; label: string }[];
}

export function getPageRegions(plan: DesignPlan): PageRegions {
  const sections = getRenderableSections(plan);
  const masthead = sections.find((s) => s.shape === "masthead") ?? null;
  const colophons = sections.filter((s) => s.shape === "colophon");
  const body = sections.filter((s) => s.shape !== "masthead" && s.shape !== "colophon");

  // A page should open with something that carries weight. When no section
  // declares `emphasis: hero` — common when the plan's first section is a
  // masthead strip — the page otherwise opened on a mid-weight body shape and
  // had no focal point at all, which the critique repeatedly scored it down for.
  if (body.length > 0 && !body.some((s) => s.shape === "split-hero")) {
    body[0] = { ...body[0], shape: "split-hero" };
  }
  // Navigation comes from the plan's own in_nav decision. Fall back to the
  // body sections that carry a headline, so a plan that marks nothing still
  // produces usable navigation rather than none at all.
  let nav = sections
    .filter((s) => s.in_nav && s.nav_label && s.shape !== "masthead")
    .map((s) => ({ id: s.id, label: s.nav_label as string }));
  if (nav.length === 0) {
    nav = body
      .filter((s) => s.copy.headline)
      .slice(0, 5)
      .map((s) => ({ id: s.id, label: s.nav_label ?? s.copy.headline.split(/[.,—]/)[0] }));
  }
  return { masthead, body, colophons, nav };
}