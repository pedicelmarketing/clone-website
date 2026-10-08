# Restructure Validation — Premium Padel Academy Marbella

Validates the **mechanical restructure pass only** (`tools/restructure.py`). No copy, layout or
media has been changed yet, so this report says nothing about the deliverable's content.

## Declared validation scope

- **Subject:** `travelproductions-padel/site/`, derived from the validated baseline at
  `travelproductions/mirror/` (see that project's `reports/validation-report.md`).
- **What the pass claimed to do:** move seven captured `/es/<slug>/_/` documents to the English
  route structure, rewrite internal links, and resolve Elementor `?ver=` asset references to real
  filenames so the result works on **ordinary static hosting** without a manifest-aware server.
- **Local URL:** `http://127.0.0.1:8614/` — a plain static host (no route map, no serve contract)
  with byte-range support. Range is deliberate, not a convenience: the baseline recorded that
  91% of the payload is video and that "Range/206 serving is load-bearing, not optional."
- **Routes:** the 6 restructured routes. `/coaches/juanpi-vanella/` **does not exist yet** — it is
  a net-new page in the architecture document with no source route to derive from, so it is
  outside this pass.
- **Viewports:** `desktop` (1440×900) and `mobile` — 12 cells.
- **Capture date:** 2026-07-30.
- **Not exercised:** consent accept/reject, cursor follower, mobile nav overlay tap, Vimeo player
  controls, Luma scene interaction. Unchanged from the baseline's exclusions.

## Result

| Check | Evidence basis | Result |
| --- | --- | --- |
| Restructure is idempotent / fully applied | `restructure.py site --check` reports 0 rewrites, 0 moves, 88 aliases already present | **Pass** |
| All 6 routes resolve on a plain static host | `HTTP-200 only` — direct request per route | **Pass** (6/6) |
| Asset references resolve without a manifest | `DOM+assets confirmed` — 12/12 browser cells, zero same-origin HTTP errors | **Pass** |
| Screenshots produced for every cell | `Observed visually` | **Pass** (12/12) |
| No restructure-introduced regression | A/B against baseline; every failure traced to a pre-existing or external cause (below) | **Pass** |

**Acceptance tier reached: `Partial`** — the same tier and the same grounds as the baseline itself.
The viewport matrix reports `INCOMPLETE`, and that verdict is not overridden here: every cell
carries at least the pre-existing source exception. What follows accounts for each one.

## Accounting for every observed failure

**1. `mouseleaveHandler is not defined` — 12/12 cells.**
Pre-existing source bug. The baseline machine-confirmed it throws identically on the live site
(`exact_failure_matched_explicit_source_local_pair`) and accepted it rather than repair it.
Present in all 7 baseline documents and all 6 derived documents. `Accepted exception` — carried
over unchanged, not introduced here.

**2. 234 × HTTP 403 from `player.vimeo.com` — all 12 cells.**
21 unique player URLs. Every one is external; **zero same-origin HTTP errors were observed.**
Vimeo refuses a `127.0.0.1` referrer. This is the baseline's documented row-1
`Fidelity Gap (offline only)` — 147 embeds classified `Embed`, never downloadable — and it
resolves on a real domain. Not a restructure defect.

**3. 9 × `.mp4` request aborts on 5 unique files.**
All five files are **present on disk** (5.2–9.4 MB each); these are cancellations, not missing
assets. The baseline hit the same nondeterministic aborts and recorded them as the sole reason two
of its own cells landed on `Partial`. Same class, same conclusion.

> An earlier check with `python3 -m http.server` produced far more media failures. That server
> answers a Range request with `200`, not `206`. The failures were the test harness's, not the
> site's, and are excluded — this is why the Range-capable server above is the one of record.

## Fidelity Gaps and open items

**19 dangling clickable internal links.** Real, and they need resolving in the content pass. None
are restructure bugs — each points at source content that was never in the baseline's declared
scope, or at a page the brief dropped.

| Dangling link(s) | Linked from | Cause |
| --- | --- | --- |
| `/es/condiciones-legales/` | all 5 non-home routes | Route **dropped by the brief**; the footer link survived it |
| `/programmes/<10 case-study slugs>` | `/`, `/programmes/` | The baseline declared 10 case-study detail routes **out of scope**; the `/es/trabajos/ → /programmes/` prefix rewrite carried their links across |
| `/about/`, `/services/`, `/work/` | `/coaches/`, `/coaching/`, `/programmes/` | The baseline declared 18 EN routes **out of scope**; these are the source's own English siblings |
| `/campo-de-golf/`, `/pruebas-3d-*` (4) | `/marbella/` | Out-of-scope source children of `/es/escena-3d/` |

All but the first sit inside Travel Productions copy that the content pass replaces outright, so
they disappear with it. The `condiciones-legales` footer link is the one that needs a decision:
the site currently has no legal page.

**A note on static reference scanning.** A scrape of `href`/`src`/`url()` across the 6 documents
flags ~102 unresolved local references, most of them `.png`/`.jpg` under `wp-content/uploads/`.
These are **not** live breakage. The source runs WebP delivery: the file on disk is
`foo.png.webp` and the raw `.png` appears only in `<noscript>` and `srcset` fallbacks the browser
never requests. Verified by A/B — the baseline mirror returns 404 for exactly the same paths.
The browser evidence above supersedes the scrape: zero same-origin errors in 12 cells.

## Verdict

The restructure pass did what it claimed. The derived site serves from ordinary static hosting with
no manifest and no route map, and carries no regression against its baseline. Every remaining
failure is either a pre-existing source bug, an external embed that needs a real domain, or a
nondeterministic media abort on a file that is present.

**This validates structure only.** All six documents still carry the original Spanish Travel
Productions copy, titles and imagery. The content re-version has not begun.
