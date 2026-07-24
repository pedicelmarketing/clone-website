# Multi-Route Module

Triggers: Scope Classification of `Multi-Route Site`, `Portfolio Site`, or `Application`; multiple routes; route transitions; detail/portfolio pages; app screens; shared or nested layouts; content collections; CMS-driven routes; navigation targets outside the requested page.

## Discovery additions

- Map the observed route structure: URLs, shared layouts, navigation behavior, route transitions, app state, loading and not-found states, and visible CMS/content patterns. Record route files, components, or source paths only when they are available from authorized evidence.
- Mark which routes are in scope and which are out of scope. Identify route-specific assets, animation timelines, metadata, and responsive differences.
- If a linked route contains structured content (tables, pricing/comparison grids, data grids, shipping rates, legal/policy sections, spec matrices, forms), document whether that route is in scope before baseline construction.

## Baseline construction

Do not expand beyond the user's requested routes. Never silently omit, flatten, merge, or convert in-scope structured content modules into unrelated cards or lists.

### Static Mirror

Preserve the captured routing behavior, shared layouts, and route transitions needed by the declared scope. Each kept same-site link must resolve locally, intentionally remain live/external, or be reported as out of scope or blocked.

### Editable Recreation fallback

When Static Mirror is unsuitable, recreate only the requested routes and their observed shared structure. Use source architecture only when supplied or otherwise authorized; do not imply that a deployed runtime reveals canonical source structure.

## Validation additions

Run the declared route-by-viewport matrix. Verify that each in-scope route has the stated evidence coverage, each kept same-site link resolves locally or intentionally points live/external, and each in-scope structured module remains on the correct route and structurally recognizable. Mark blocked or unexercised route-state combinations explicitly.

For `Hero Only`, `Homepage`, or `Landing Page` scope, keep route analysis brief unless route transitions are detected.
