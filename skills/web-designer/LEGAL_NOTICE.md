# Legal notice — web-designer skill

This skill, like `nt-site-mirror`, is an internal adaptation for the site-cloner profile
on the Hermes Agent platform. It is intended to be used only on the operator's own brand
assets, on reference URLs the operator explicitly names, and on social profiles the
operator has authorization to access.

The web-designer skill does *not* extract the source code of any reference site. It
extracts *observable* design decisions (tokens, structure, copy, motion) and uses those
to inform a brand-new site that the operator owns.

Per `nt-site-mirror`'s asset-hygiene rules, every asset pulled into or referenced from
the new site is classified as one of: Original / Local Copy / Embed / Kept External /
User-Supplied Baseline Asset / Recreated / Approximated / Blocked / Unknown. Paid fonts,
provider-streamed media, and other protected assets are classified, never silently
redistributed.

No third-party code (GSAP, shadcn primitives, etc.) is vendored into this repository.
GSAP source is not included because it is not OSI-approved; install via `npm` or `pnpm`
per the operator's project conventions.
