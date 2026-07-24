# Validation Report

> Installed blank template — read-only. Copy it to `<project>/reports/validation-report.md` and fill the project-local copy. Never write project data into the installed skill.
>
> Claims are limited to the declared scope and recorded evidence. Observed behavior and code or HTTP checks are different evidence types; never infer one from the other.

## Declared validation scope

- Source URL / evidence:
- Local URL / serving contract:
- Method: `Static Mirror` | `Editable Recreation (fallback method)`
- Routes:
- Viewports:
- Interaction / loading / media states:
- Source and local capture date/time:

## Per-section checks

| Section / route | Viewport | Scroll behavior | Animation / media | Interaction states | Verification method | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

Verification method values: `Observed visually` | `Interaction-tested` | `DOM+assets confirmed` | `HTTP-200 only` | `Not exercised`.

Verdict values: `Pass for declared evidence` | `Partial` | `Fidelity Gap` | `Accepted exception` | `Blocked` | `Not exercised` | `Out of scope`.

## Global checks

- [ ] Typography and spacing checks completed for the declared comparison scope
- [ ] All kept same-site links resolve locally, intentionally point live/external, or are documented out of scope
- [ ] Every in-scope structured module (tables, pricing, forms, legal) exists on the correct route and is structurally recognizable
- [ ] No unresolved critical overlap, stuck/frozen behavior, or missing asset was found within exercised coverage
- [ ] Performance observations recorded for the declared experience
- [ ] Active module validation results recorded: (list modules)
- [ ] Asset Preservation Table statuses verified — no silent substitutions

## Static Mirror audit (Static Mirror Mode only)

- Result tier: `First-render mirror` | `Validated static mirror — declared scope` | `Offline-validated static mirror — declared scope` | `Partial static mirror`
- Discovery coverage: `Complete for declared triggers` | `Partial` | `Blocked` — evidence and omissions:
- Declared viewport (validation source of truth): `WxH` — narrower preview surfaces are non-representative
- Experience gate (preloader / entry / progress screen): present yes / no — terminal usable state reached: yes / no — observed trajectory:
- Evidence gates: boot ☐ / dependency ☐ / experience (when applicable) ☐
- Asset count: / Total folder size:
- Missing or unresolved files within declared coverage:
- Remaining external requests (critical vs harmless fallback):
- Construction-time accommodations (fonts, analytics no-ops, routing/serving shims, etc.):

## Serving Contract (Static Mirror Mode only)

- Serve command / config (shipped with the project):
- Web root: · Port:
- Contract / manifest schema and path:
- SPA fallback: `Off` | `Confirmed SPA with named safe entry`
- Exact path-and-query route-map coverage / unresolved variants:
- Plain static hosting valid: yes / no — if no, every accommodation required:
  - Range/206 media support: needed / not needed
  - Content-type replay (manifest-recorded types): needed / not needed
  - Query-aware / variant routing: needed / not needed
  - Other (shims, serving-time fallbacks):
- `file://` support: `Unsupported` | `Not tested / not claimed` — reason:
- Validation claims are conditional on this serving setup.

## Automated URL × Viewport Evidence

- `viewports.py` result file:
- Matrix complete: yes / no — passed / expected:
- Per-cell status and final URL recorded: yes / no
- Rejected challenge, login, consent-blocking, error, and 404 states:
- Scroll mechanisms exercised (`window_scroll` / `internal_container` / `wheel_virtual_scroll` / `none`):
- Service-worker-controlled and bypassed results, where relevant:
- Settling method: `DOMContentLoaded + bounded reported settling` — maximum / observed stability:

## Construction-Time Accommodations

> Record only acquisition, routing, or serving accommodations required to make the faithful baseline work locally. Do not record user-requested content, branding, media, or behavior changes here. If none were needed, write `None`; do not infer byte identity without supporting hashes and provenance.

| Artifact / path | Phase / actor | Required local accommodation | Source / provenance evidence | Revalidation evidence |
| --- | --- | --- | --- | --- |
| | `construction` / | | | |

## Interaction Coverage

- Exercised (with result):
- Not exercised — and why:

## External Runtime Dependencies

| Dependency | Handling (`Localized` / `Kept external` / `Construction-time no-op` / `Blocked` / `Unknown`) | Fidelity impact | Evidence |
| --- | --- | --- | --- |
| | | | |

## Fidelity Gaps

| Feature | Missing / downgraded behavior | Constraint | Available baseline paths | Status (`Pending` / `Accepted exception` / `Approved approximation`) |
| --- | --- | --- | --- | --- |
| | | | | |

## Project status

`Complete for declared scope and evidence` | `Partial` | `Blocked`

State the declared routes, viewports, states, and evidence behind the status. If Partial or Blocked, separate clearly:

- Completed:
- Blocked:
- Approved baseline approximations:
- Not exercised / unresolved:
