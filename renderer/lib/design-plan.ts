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
    }));
}