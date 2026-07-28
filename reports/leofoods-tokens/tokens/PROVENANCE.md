# Token provenance

- Project: `leo-foods-redesign`
- Generated at: `2026-07-28T00:15:24Z`
- Brand brief: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/brand-leofoods/brand-brief.json` (schema validated before use)
- Reference tokens: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/validation/linear-app/tokens`
- Evidence basis: `DOM+assets confirmed`

The reference color inventory was intentionally not consumed. Brand colors and
font families are authoritative; the reference contributes structure only.

| Token group | Source | Detail |
|---|---|---|
| Color | `brand-brief` | palette_from_logo; reference colors ignored |
| Font families | `brand-brief + substitution` | typography_recommendation families, paid->OFL substitution applied |
| Type scale | `brand-brief` | typography_recommendation.scale_steps |
| Type scale ratio | `brand-brief` | typography_recommendation.scale_ratio |
| Spacing | `reference-structure` | spacing.json scale |
| Radius | `reference-structure` | radius.json scale |
| Shadow | `reference-structure` | shadow.json elevations |

## Font license notes (carried over verbatim from brand-brief)

Recoleta is a paid Klim Type Foundry face — DO NOT vendored. For production substitute Fraunces (OFL) or a similar humanist serif. Inter is SIL OFL 1.1. JetBrains Mono is OFL. The live site uses a single custom webfont (variable) with a heavy display face for headings ('Meet The Cocktail Coop', 'All Natural Cocktail Mixers', 'REAL Ingredients Only', 'Made with real ingredients', 'Easy to use and even easier to enjoy', 'Crafted by Bartenders') and a humanist sans for body. Use a serif display + neutral sans pairing to honor the 'real / crafted / simple' feel without copying the proprietary display face. Avoid 100% Inter everywhere — that is the agency-website look the brand is NOT.

Review these notes before vendoring or redistributing any font files. Paid or
restricted fonts remain external until the project has the required license.

## Font substitutions (paid -> OFL)

The brand brief's `license_notes` flag restricted licensing, so every
role with a paid/commercial family is emitted as an OFL-licensed
substitute. The original family is preserved here for provenance; it
never appears as a live CSS `font-family` value, and no Google Fonts
request is emitted for it.

| Role | Original (paid) | Substitute (OFL) | Reason |
|---|---|---|---|
| display | Recoleta | Inter | license_notes flagged restricted licensing; substituted 'Recoleta' with OFL substitute 'Inter' |
| body | Inter | Inter | license_notes flagged restricted licensing; substituted 'Inter' with OFL substitute 'Inter' |
| mono | JetBrains Mono | JetBrains Mono | license_notes flag restricted licensing, but the brief explicitly names 'JetBrains Mono' as OFL; brand family kept |

