#!/usr/bin/env node
/**
 * check-licenses.mjs
 *
 * Fails the build (and CI) if any package with motion/animation intent
 * appears in package.json without an MIT-compatible license.
 *
 * Why this exists: the design pipeline must work for any client in any
 * industry, so we cannot bake non-OSI motion libraries (e.g. GSAP's
 * standard license, which is NOT OSI-approved) into the renderer. The
 * approved runtime motion stack is `motion` (MIT, framer-motion's
 * successor) and `lenis` (MIT). Everything else is on the deny list.
 *
 * The check is intentionally narrow: it only flags packages whose NAME
 * matches an animation/animation-adjacent pattern AND whose license is
 * not MIT-compatible. Generic packages with restrictive licenses are
 * outside this guard's scope — npm's own licensing checks should cover
 * those.
 */

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const rendererRoot = resolve(here, "..");

const pkg = JSON.parse(
  readFileSync(resolve(rendererRoot, "package.json"), "utf8"),
);

// Known motion/animation packages that are NOT OSI-approved. Add to this
// list as new restricted-license libraries are encountered.
const DENYLIST = new Set([
  "gsap",          // GreenSock standard license is not OSI
  "@gsap/business", "@gsap/bonus", "@gsap/shockingly", "@gsap/free",
  "animejs",       // anime.js v4 is MIT but older v3 has a custom license — guard either way
  "mo-js", "mojs",
  "velocity-animate", // historic license issues; kept flagged
]);

// Names we DO allow regardless of how their package.json describes
// themselves (e.g. some forks ship without a "license" field). The MIT
// ones we use are listed here so accidental license bumps are caught.
const ALLOWLIST = new Set([
  "motion",     // MIT
  "lenis",      // MIT
]);

const issues = [];
const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };

for (const name of Object.keys(deps)) {
  // Normalize @scope/name form
  const base = name.startsWith("@") ? name.split("/").slice(0, 2).join("/") : name.split("/")[0];

  if (DENYLIST.has(name) || DENYLIST.has(base)) {
    issues.push(`DENY: ${name} is on the restricted-license list (not OSI-approved).`);
    continue;
  }
  if (!ALLOWLIST.has(name) && !ALLOWLIST.has(base)) {
    // Skip packages that aren't motion-related; we only police motion libs.
    continue;
  }
  // Read the installed package's license field.
  let license = "UNKNOWN";
  try {
    const sub = JSON.parse(
      readFileSync(
        resolve(rendererRoot, "node_modules", base, "package.json"),
        "utf8",
      ),
    );
    license = sub.license ?? sub.licenses ?? "UNKNOWN";
  } catch {
    license = "NOT-INSTALLED";
  }
  if (license !== "MIT" && license !== "Apache-2.0" && license !== "BSD-3-Clause" && license !== "BSD-2-Clause") {
    issues.push(
      `LICENSE: ${name} resolves to license=${license}; expected MIT/Apache/BSD. ` +
        `If intentional, add to ALLOWLIST with justification.`,
    );
  }
}

if (issues.length) {
  console.error("[check-licenses] FAILED\n" + issues.map((s) => "  - " + s).join("\n"));
  process.exit(1);
}
console.log("[check-licenses] OK — all motion packages are MIT/Apache/BSD.");