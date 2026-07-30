# Is the quality gap a model problem or an infrastructure problem?

**Answer: it was infrastructure. It is now becoming the model.** Holding everything
constant except who wrote the design plan is worth **+8/70** (46 → 54). Holding the plan
constant and fixing the renderer was worth considerably more than that.

## Why the question was asked

The operator asked whether upgrading the model would fix the output quality, or whether the
pipeline itself was the limit. Opinion is cheap here, so this is a controlled test.

## Method

One brand (Barcoop Bevy / `brand-leofoods`). Two design plans. **Everything downstream of
the plan is byte-identical**: same brand brief, same fetched photography, same token set,
same Next.js renderer, same 11 gates, same critique judge (`gemini/gemini-2.5-flash`), one
iteration, no `--apply`.

The only variable is the plan's author.

| | MiniMax-M3 | Claude Opus 5 |
|---|---:|---:|
| Sections | 11 | 13 |
| Copy blocks | 20 | 41 |
| **Total words on the page** | **175** | **468** |
| Sections declaring an explicit `layout` | 0/11 | 13/13 |
| Sections deliberately skipped (with reasons) | 5 | 3 |
| Recorded design decisions | 7 | 5 |
| `validate_plan` violations | 0 | 0 |
| Gates | 11/11 PASS | 11/11 PASS |

Both plans obey the same invent-nothing rule: every claim cites a brief field that resolves
to a non-empty value, and every `media.file` exists in the fetched asset manifest.

## Result

| Dimension | MiniMax | Claude | Delta |
|---|---:|---:|---:|
| visual_hierarchy | 8 | 8 | 0 |
| use_of_space | 6 | 6 | **0** |
| typographic_contrast | 8 | 9 | +1 |
| focal_point | 7 | 8 | +1 |
| brand_fit | 4 | 6 | +2 |
| motion_restraint | 10 | 10 | 0 |
| looks_templated (inverted) | 3 | 7 | **+4** |
| **Total** | **46** | **54** | **+8** |

## Reading it honestly

**The gain is real but narrow.** It concentrates in `looks_templated` (+4) and `brand_fit`
(+2) — the dimensions most sensitive to *how much distinct material the plan supplies*. With
2.7x the copy and an explicit layout per section, the page has more to differentiate itself
with. That is a content-volume effect as much as a taste effect.

**`use_of_space` did not move at all — 6/10 for both.** The judge's complaint is nearly
identical on the two pages: the hero's image column is isolated in empty space. No plan can
fix that, because the plan does not control the hero's internal composition. **That number is
the clearest evidence left that infrastructure, not the model, still sets the ceiling.**

**Both plans lost points for the same missing thing.** The judge reported the signature
element absent from both pages — MiniMax's "Coop Tail", Claude's "ratio mark". The renderer
has no wiring for `signature_element` at all; it draws a fixed gold dot. Two different
authors both specified a signature device and both were ignored. That is infrastructure.

## What this says about a model upgrade

Before today's renderer work, this experiment would have measured almost nothing. The old
renderer dropped six of eleven sections' copy and drew one shape for every section, so a
richer plan would have been discarded just as thoroughly as a thin one — and would have made
the bugs *harder* to find, because the JSON would have looked excellent while the page stayed
broken.

So the ordering matters: **fixing the plumbing was a precondition for the model upgrade being
worth anything.** Now that copy reaches the DOM and layout is selectable, plan quality is
visible, and +8 is what it buys on this brand.

## Bugs this experiment found

Running a second author through the pipeline surfaced four defects that one author never hit:

1. **`design_pass.py` was fully broken.** It stamps `plan['provider']` before validating, but
   `provider` was not in the schema and the schema is `additionalProperties: false`. Every run
   failed validation three times and gave up — the "API failed" WARN in verify.sh was partly
   this, not the API.
2. **Filled buttons rendered at 1.47:1.** `--primary-foreground` was hardwired to
   `--color-neutral-0`; on a brand whose neutral-0 is cream and whose primary is yellow, every
   button was cream-on-yellow. Now derived by measured contrast, like `--color-fg`/`--color-bg`.
3. **Card grids showed empty coloured blocks.** A `gap-px` + `bg-border` hairline trick paints
   the container background through unfilled cells; seven items in a three-column grid left two
   green rectangles.
4. **Repeated copy roles were silently collapsed.** The schema permits several blocks with the
   same `(section_id, role)` and the design pass uses that to express lists — one plan wrote a
   services section as nine `headline` + nine `body` pairs. Keying copy by role kept only the
   last of each. Gate 11 caught it; the renderer now preserves and pairs them.

## Limits

- **n=1 brand, 1 iteration, 1 judge.** Direction, not effect size.
- The two plans are not equally aged: MiniMax's predates the `layout` field entirely, so it
  could not have declared layouts even in principle. Part of the +4 on `looks_templated`
  is that handicap rather than authorship.
- A fair rematch requires regenerating the MiniMax plan against the current schema, with the
  layout enum in the prompt. That is the next measurement, not this one.

## Reproduce

```sh
python3 skills/web-designer/scripts/render_nextjs.py \
  --brand-brief reports/brand-leofoods/brand-brief.json \
  --design-plan reports/m6e-author-ab/claude-design-plan.json \
  --tokens reports/leofoods-tokens -o build-claude
python3 skills/web-designer/scripts/validate_site.py build-claude \
  -o val-claude --renderer-root renderer \
  --design-plan reports/m6e-author-ab/claude-design-plan.json
python3 skills/web-designer/scripts/critique_pass.py --site build-claude \
  --brand-brief reports/brand-leofoods/brand-brief.json \
  --design-plan reports/m6e-author-ab/claude-design-plan.json \
  -o crit-claude --max-iterations 1 --provider gemini
```

Brand imagery is gitignored; re-fetch with `fetch_brand_assets.py` first.
