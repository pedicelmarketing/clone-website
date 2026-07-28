# Does real brand photography improve design quality? — a controlled A/B

**Verdict: yes, but less than expected, and not where expected.** Net **+3/70**, earned
entirely on brand authenticity and de-templating, and partly given back on hierarchy.

## Why this measurement exists

The asset pipeline was built on the argument that *"a site with no photography can't beat a
real reference site regardless of layout."* That was a plausible assumption, not a measured
fact. This run tests it.

## Method

Two builds of the **same brand** (Leo Foods) from the **same design plan**, differing in
exactly one respect: the `sections[].media` assignments were stripped from the control.

| | With photos | Control |
|---|---|---|
| Design plan | `reports/leofoods-design/design-plan.json` | identical, `media` removed from 7 sections |
| Tokens | `reports/leofoods-tokens` | same |
| Brand brief | `reports/brand-leofoods/brand-brief.json` | same |
| `<img>` tags in built HTML | 7 | 0 |

Both were critiqued by the **same judge** (`gemini/gemini-2.5-flash`), one iteration, no
`--apply`, viewports 1440x900 + 375x812. Same-judge pinning is the point: scores from two
different models would have measured the models, not the photography.

## Result

| Dimension | With photos | Control | Delta |
|---|---:|---:|---:|
| visual_hierarchy | 8 | 9 | **−1** |
| use_of_space | 4 | 4 | 0 |
| typographic_contrast | 8 | 9 | **−1** |
| focal_point | 6 | 6 | 0 |
| brand_fit | 6 | 3 | **+3** |
| motion_restraint | 10 | 10 | 0 |
| looks_templated (inverted) | 5 | 3 | **+2** |
| **Total** | **47** | **44** | **+3** |

## What the judge actually observed

**Photography buys brand authenticity — the largest single delta on the board.** Without it
the judge called the page *"entirely text-based"* against a layout thesis that explicitly
promises a bottle lineup and ingredient flat-lays. The thesis was writing cheques the render
could not cash; photography is what makes the stated concept legible.

**It also breaks the sameness.** The control was marked down because *"each section follows
the identical pattern of a small numbered identifier, a large display heading, and a single
body paragraph."* That is the templated-output failure mode this whole capability exists to
avoid, and imagery is a direct antidote.

**But it costs a point on hierarchy and type contrast.** With photos the judge noted the
product image is *"visually dominant"* — it competes with the headline instead of supporting
it. The control's plain three-tier rhythm (eyebrow → display heading → body) reads more
cleanly *precisely because* nothing contends with it. Adding imagery without re-weighting the
composition around it trades one kind of quality for another.

## The finding that matters more than the delta

**`use_of_space` scored 4/10 in *both* builds** — the weakest dimension by a wide margin, and
completely unmoved by photography. Both critiques independently measured the same defect:
roughly **58–60% of the horizontal canvas is empty** at 1440px. That is a layout problem, and
no amount of imagery will fix it. It is the highest-value next target.

Two further gaps surfaced, both of which are the *renderer* failing the *plan*, not the plan
being wrong:

1. **The signature element never renders.** The plan specifies a "Coop Tail" motif; the judge
   reported it absent in both builds. A signature element that does not survive rendering is
   the single cheapest de-templating win available, and it is currently being thrown away.
2. **One photo per section under-serves the thesis.** The plan's thesis is *"bottle lineup
   treated as the shelf"*, but `BrandImage` draws a single image per section, so the judge saw
   *"only a single bottle... which underutilizes the 'shelf' concept."* 22 assets were fetched
   and 7 placed; the renderer has no multi-image treatment to place them into.

## Honest limits of this result

- **n=1 brand, 1 iteration, 1 judge.** This establishes direction, not effect size. The ±1
  movements on hierarchy and type contrast are well inside the noise a single critique run can
  produce; only the +3 brand_fit and +2 looks_templated deltas are large enough to lean on.
- **Not comparable to the earlier 46/70** recorded for the first brand: different brand,
  different judge (that run used `minimax/MiniMax-M3`). Cross-judge score comparison is exactly
  what `_summary_md` now refuses to present as a trend.
- The control is a synthetic ablation, not a design anyone would ship — stripping media from a
  plan that was *written* around media is a slightly unfair baseline for the control.

## Reproduce

```sh
# with photos
python3 skills/web-designer/scripts/render_nextjs.py \
  --brand-brief reports/brand-leofoods/brand-brief.json \
  --design-plan reports/leofoods-design/design-plan.json \
  --tokens reports/leofoods-tokens -o build-photos
python3 skills/web-designer/scripts/critique_pass.py --site build-photos \
  --brand-brief reports/brand-leofoods/brand-brief.json \
  --design-plan reports/leofoods-design/design-plan.json \
  -o critique-photos --max-iterations 1 --provider gemini
```

The control repeats both commands with a plan whose `sections[].media` keys are removed.
Brand imagery is gitignored; re-fetch it first with
`skills/web-designer/scripts/fetch_brand_assets.py --brand-brief reports/brand-leofoods/brand-brief.json -o renderer/public/brand`.
