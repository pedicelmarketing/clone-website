# Token provenance

- Project: `pedicel-marketing-redesign-smoke`
- Generated at: `2026-07-28T23:11:03Z`
- Brand brief: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/brand-smoke/brand-brief.json` (schema validated before use)
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

Switzer is by Indian Type Foundry — free for personal use; commercial use requires a paid license. Do not vendor the .otf files into the production build. Poppins is by Indian Type Foundry as well — released under the SIL Open Font License (OFL) and is safe to self-host. JetBrains Mono is OFL. Recommended safe self-hosted pair for a redesign: Switzer (paid) retained for the live Pedicel brand if a site license is purchased; otherwise substitute with Inter (OFL) for display and keep Poppins for body. The brand's own site loads Switzer-Light, Switzer-Regular, Switzer-Medium and Poppins-Regular from the Webflow CDN (per mirror-manifest.json in pedicelmarketing/audit).

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
| display | Switzer | Inter | license_notes flagged restricted licensing; substituted 'Switzer' with OFL substitute 'Inter' |
| body | Poppins | Poppins | license_notes flag restricted licensing, but the brief explicitly names 'Poppins' as OFL; brand family kept |
| mono | JetBrains Mono | JetBrains Mono | license_notes flag restricted licensing, but the brief explicitly names 'JetBrains Mono' as OFL; brand family kept |

