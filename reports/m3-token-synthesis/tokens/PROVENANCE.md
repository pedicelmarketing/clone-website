# Token provenance

- Project: `pedicel-marketing-redesign-smoke`
- Generated at: `2026-07-27T11:00:01Z`
- Brand brief: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/brand-smoke/brand-brief.json` (schema validated before use)
- Reference tokens: `/home/openclaw/Coding/clone-website-wt/feat-web-designer/reports/validation/linear-app/tokens`
- Evidence basis: `DOM+assets confirmed`

The reference color inventory was intentionally not consumed. Brand colors and
font families are authoritative; the reference contributes structure only.

| Token group | Source | Detail |
|---|---|---|
| Color | `brand-brief` | palette_from_logo; reference colors ignored |
| Font families | `brand-brief` | typography_recommendation families |
| Type scale | `brand-brief` | typography_recommendation.scale_steps |
| Type scale ratio | `brand-brief` | typography_recommendation.scale_ratio |
| Spacing | `reference-structure` | spacing.json scale |
| Radius | `reference-structure` | radius.json scale |
| Shadow | `reference-structure` | shadow.json elevations |

## Font license notes (carried over verbatim from brand-brief)

Switzer is by Indian Type Foundry — free for personal use; commercial use requires a paid license. Do not vendor the .otf files into the production build. Poppins is by Indian Type Foundry as well — released under the SIL Open Font License (OFL) and is safe to self-host. JetBrains Mono is OFL. Recommended safe self-hosted pair for a redesign: Switzer (paid) retained for the live Pedicel brand if a site license is purchased; otherwise substitute with Inter (OFL) for display and keep Poppins for body. The brand's own site loads Switzer-Light, Switzer-Regular, Switzer-Medium and Poppins-Regular from the Webflow CDN (per mirror-manifest.json in pedicelmarketing/audit).

Review these notes before vendoring or redistributing any font files. Paid or
restricted fonts remain external until the project has the required license.
