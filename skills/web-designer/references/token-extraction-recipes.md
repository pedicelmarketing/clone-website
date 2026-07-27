# Token extraction recipes — operational reference

This is the operational companion to `research/understand-the-reference.md` §2. The
research document describes the *why*; this document describes the *how* — the exact
recipe `scripts/extract_tokens.py` implements, the priority order, and what to do when
the data is incomplete.

The same five token classes apply: **color, typography, spacing, radius, shadow.** Each
has a primary source, a secondary source, and a fallback — in that priority order.

---

## 2a. Color

**Primary source:** CSS custom properties at `:root` (and any `:where(html, body)`
rule). The extractor walks `document.styleSheets` and reads every property whose name
starts with `--`. Cross-origin stylesheets throw on `cssRules` access — skipped silently.

**Secondary source:** Tailwind's CDN bundle. If the page loads
`https://cdn.tailwindcss.com`, look for an inline `tailwind.config = { ... }` in a
subsequent `<script>`. The object's `theme.extend.colors` is the palette.

**Fallback:** `getComputedStyle` on representative elements — body, hero, headings,
buttons. The applied colors tell us what the runtime is actually painting, even when
the source variables are unreachable.

**Output:** `tokens/color.json` with:
- `tokens[]` — every observed `--color-*` (or `--fg-*` / `--bg-*` / `--brand-*`)
  variable with its raw value, normalized hex, and reference count.
- `families` — variables grouped by name prefix (e.g. `gray`, `primary`, `accent`).
- `primary_candidates` — top-3 variables by reference count (best guess at the
  brand's primary palette).
- `total_unique` — the number of distinct color tokens observed.

**What we never do:** synthesize a palette we didn't observe. If the page only exposes
3 colors, we emit 3 colors. We do not round up to a "complete" 11-color palette.

---

## 2b. Typography

**Primary source:** `getComputedStyle` on representative elements (h1, h2, h3, h4, p,
body, button, small). Capture `font-family`, `font-size`, `font-weight`,
`line-height`, `letter-spacing`, `text-transform`.

**Secondary source:** CSS custom properties — `--font-display`, `--font-body`,
`--font-mono`, `--leading-*`, `--tracking-*` — when present.

**Output:** `tokens/typography.json` with:
- `scale[]` — the per-element observations (size, weight, line-height, family).
- `family_by_role` — the role-to-style mapping.
- `families` — display / body / mono classification (heuristic: presence of "mono" /
  "code" / "courier" → mono; h1/h2 entries → display; everything else → body).
- `scale_ratio` — the ratio between the largest and smallest observed size (e.g. 2.0
  means the type scale is 2× from body to display).

**Asset-hygiene note:** Google Fonts and Adobe Fonts are widely licensed for *use* but
not for *redistribution* in a derived product. The extractor records the family name
and the source URL; the brand-brief (M2+) decides whether to substitute.

---

## 2c. Spacing

**Primary source:** `getComputedStyle` on representative container elements (section,
main > div, [class*="container"], [class*="grid"], [class*="flex"], header, footer,
nav). Capture `padding`, `margin`, and `gap`.

**Detection of the base unit:** take the GCD of observed values; the most common
design-system base units are 4, 6, 8, 10, 12 px. We try each in order and pick the
first that divides all observed values.

**Output:** `tokens/spacing.json` with:
- `base_unit_px` — the detected base unit (or `null` if the data is too sparse).
- `scale[]` — every multiple of the base unit that was observed.
- `samples[]` — the raw observations (tag, class, padding, margin, gap).

**Trim policy:** the largest 10% of values (full-bleed padding) and the smallest 10%
(sub-pixel) are dropped before the GCD computation, to keep the base-unit detection
stable.

---

## 2d. Radius

**Primary source:** `getComputedStyle` on representative elements (button, card, input,
image, tag/badge). Capture `border-top-left-radius`.

**Output:** `tokens/radius.json` with:
- `scale[]` — the observed values, snapped to the canonical scale {0, 4, 6, 8, 12, 16,
  20, 24, 9999}.
- `defaults_by_role` — the most common value per role (e.g. `{button: 8, card: 12}`).
- `value_frequency` — the raw count of each observed value.

The 9999px value is the canonical "pill" shape (any radius ≥ 999 is treated as a pill).

---

## 2e. Shadow

**Primary source:** `getComputedStyle` on representative elements (card, popover,
modal, header, button). Capture `box-shadow`.

**Output:** `tokens/shadow.json` with:
- `elevations[]` — buckets grouped by first blur radius (in px). Each elevation has
  the level (0, 1, 2, …), the blur radius, a representative box-shadow value, and
  the roles that use it.
- `samples[]` — the raw observations.

**Why blur radius?** Two box-shadows with the same blur radius are visually equivalent
at the same elevation level. The first blur (the strip-comma-separated list)
identifies the layer's intensity.

---

## When extraction returns empty arrays

| Class | Empty means | What we record |
|-------|-------------|----------------|
| `color` | no CSS variables at `:root` (e.g. unstyled HTML) | `tokens: []`, `families: {}`, `note: "no CSS custom properties found at :root"` |
| `typography` | rare — every page has typography | `scale: []`, `note: "no representative elements found"` |
| `spacing` | page has no `<section>` / `<main>` structure | `scale: []`, `base_unit_px: null`, `note: "no container elements found"` |
| `radius` | page has no buttons / cards / inputs | `scale: []`, `note: "no `border-radius` observed"` |
| `shadow` | page has no elevated surfaces | `elevations: []`, `note: "no `box-shadow` observed"` |

In every case, the `meta.notes` array records the reason. We do not silently substitute
default values.

---

## What the extractor does NOT do

- **No source-map extraction.** We do not peek at the JS bundle's component names to
  learn the palette. Those are *guardrails*, not the same as the rendered output.
- **No image color extraction.** The `lokesh/color-thief` cross-check (per
  `understand-the-reference.md` §2a) is the brand-brief's job (M2+), not the
  reference-extraction's.
- **No CSS variable discovery beyond `:root`.** Variables scoped to specific scopes
  (e.g. `[data-theme="dark"]`) are out of scope for the reference brief; the
  brand-brief can ask for them separately.
- **No cross-origin stylesheet processing.** When a CDN delivers a stylesheet
  (`fonts.googleapis.com`, etc.), the browser denies `cssRules` access. We honor that
  and skip silently — the reference's own fonts are picked up separately via the
  `--local` mirror in M2+.

---

## Confidence reporting

Every per-class output has a top-level `evidence_basis` field. Values:

- `DOM+assets confirmed` — the measured values were observed in the rendered DOM.
- `HTTP-200 only` — the page returned but extraction failed (e.g. CSP, runtime error).
- `Not exercised` — the class was not probed (e.g. Tailwind was not present).

If `meta.access_state` is anything other than `ok`, every class's `evidence_basis` is
demoted to `HTTP-200 only`, regardless of the in-DOM result — the page might be
serving a challenge page that we couldn't recognize.
