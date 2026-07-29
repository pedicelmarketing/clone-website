#!/usr/bin/env bash
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
SCRIPTS=skills/web-designer/scripts
BRIEF=reports/brand-smoke/brand-brief.json
REF_TOKENS=reports/validation/linear-app/tokens
REF=reports/validation/linear-app
TOKENS=reports/m3-token-synthesis
PLAN=reports/m6-design/design-plan.json
PLAN_OUT=reports/m6-composed-site
FALLBACK_OUT=reports/m3-composed-site
VALIDATION=reports/m6-validation
# The Next.js renderer is the real deliverable; the static composer above is the
# retired fallback path. Both get built and validated, because gates 9/10
# (build + bundle budget) are Only-On-Exports and can ONLY be exercised against
# a real `_next/` export — validating the composer alone left them permanently
# NOT-EXERCISED, i.e. the renderer shipped unverified.
RENDERER_OUT=reports/m6-renderer-site
RENDERER_VALIDATION=reports/m6-renderer-validation
rows=(); failures=0; warns=0
row() { local name=$1 status=$2 detail=${3:-}; rows+=("$status|$name|$detail"); if [[ $status == FAIL ]]; then failures=$((failures+1)); elif [[ $status == WARN ]]; then warns=$((warns+1)); fi; }
run_step() { echo; echo "==> $*"; "$@"; return $?; }

if run_step "$PYTHON" "$SCRIPTS/synthesize_tokens.py" --brand-brief "$BRIEF" --reference-tokens "$REF_TOKENS" -o "$TOKENS"; then row "pipeline: synthesize_tokens" PASS; else row "pipeline: synthesize_tokens" FAIL "command failed"; fi
mkdir -p "$(dirname "$PLAN")"
DESIGN_STATUS=1
for delay in 0 2 6 15; do
  (( delay > 0 )) && { echo "design_pass retry in ${delay}s"; sleep "$delay"; }
  if run_step "$PYTHON" "$SCRIPTS/design_pass.py" --brand-brief "$BRIEF" --reference "$REF" -o "$PLAN"; then DESIGN_STATUS=0; break; else DESIGN_STATUS=$?; fi
done
if [[ $DESIGN_STATUS -ne 0 ]]; then
  if [[ -s "$PLAN" ]]; then row "pipeline: design_pass" WARN "API failed; reused existing design plan"; else row "pipeline: design_pass" FAIL "no usable design plan"; fi
else row "pipeline: design_pass" PASS; fi
if run_step "$PYTHON" "$SCRIPTS/compose_site.py" --brand-brief "$BRIEF" --tokens "$TOKENS" --reference-report "$REF" --design-plan "$PLAN" -o "$PLAN_OUT"; then row "pipeline: compose_site (plan)" PASS; else row "pipeline: compose_site (plan)" FAIL "command failed"; fi
if run_step "$PYTHON" "$SCRIPTS/compose_site.py" --brand-brief "$BRIEF" --tokens "$TOKENS" --reference-report "$REF" -o "$FALLBACK_OUT"; then row "pipeline: compose_site (fallback)" PASS; else row "pipeline: compose_site (fallback)" FAIL "command failed"; fi
# Content fidelity (Gate 11) is enforced on the RENDERER below, not here: the
# Next.js renderer is the shipped artifact and compose_site.py is the retired
# fallback path. Passing --design-plan here would block verify.sh on a
# deprecated composer's copy handling. Gate 11 reports NOT-EXERCISED for this
# run and says why, rather than silently passing.
if run_step "$PYTHON" "$SCRIPTS/validate_site.py" "$PLAN_OUT" -o "$VALIDATION"; then row "pipeline: validate_site" PASS; else row "pipeline: validate_site" FAIL "command failed"; fi

# --- Next.js renderer path -------------------------------------------------
# Skippable via SKIP_RENDERER=1 for a fast inner loop, but skipping is recorded
# as a WARN row rather than silently omitted: a verify run that did not build
# the renderer must not read as one that did.
if [[ "${SKIP_RENDERER:-0}" == "1" ]]; then
  row "pipeline: render_nextjs" WARN "skipped (SKIP_RENDERER=1)"
  row "pipeline: validate_site (renderer)" WARN "skipped (SKIP_RENDERER=1)"
  row "9. Renderer gates 7-11 exercised" WARN "skipped (SKIP_RENDERER=1)"
else
  RENDER_OK=0
  if run_step "$PYTHON" "$SCRIPTS/render_nextjs.py" --brand-brief "$BRIEF" --design-plan "$PLAN" --tokens "$TOKENS" -o "$RENDERER_OUT"; then
    row "pipeline: render_nextjs" PASS; RENDER_OK=1
  else row "pipeline: render_nextjs" FAIL "next build failed"; fi

  if (( RENDER_OK )); then
    if run_step "$PYTHON" "$SCRIPTS/validate_site.py" "$RENDERER_OUT" -o "$RENDERER_VALIDATION" --renderer-root renderer --design-plan "$PLAN"; then
      row "pipeline: validate_site (renderer)" PASS
    else row "pipeline: validate_site (renderer)" FAIL "command failed"; fi

    if "$PYTHON" - <<'PY'
import json,pathlib
d=json.loads(pathlib.Path('reports/m6-renderer-validation/gate-results.json').read_text())
rs={r.get('id'): r for r in d.get('results',[])}
bad=[f"{i}:{r.get('verdict')}" for i,r in rs.items() if r.get('verdict')=='FAIL']
if bad: raise SystemExit('renderer gate FAILED: '+', '.join(bad))
# The whole point of this path: these must actually RUN against the real
# deliverable. Each has silently reported NOT-EXERCISED here before —
# 9/10 because verify.sh only ever validated the static composer, and 7/8
# because root-relative <link href="/_next/..."> resolved to a nonexistent
# filesystem path, so the gates saw "no CSS files" and skipped. Both holes
# read as a clean report while the renderer went unchecked.
for gid in ('7','8','9','10','11'):
    r=rs.get(gid)
    if r is None: raise SystemExit(f'gate {gid} missing from renderer gate-results.json')
    if r.get('verdict')!='PASS':
        raise SystemExit(f"gate {gid} ({r.get('name')}) is {r.get('verdict')} on a Next.js export: {r.get('summary')}")
skipped=[i for i,r in rs.items() if r.get('verdict')=='NOT-EXERCISED']
if skipped: raise SystemExit('renderer gate(s) NOT-EXERCISED: '+', '.join(map(str,skipped)))
print('renderer gates PASS, including 7/8 (motion, tokens), 9/10 (build, bundle) and 11 (content fidelity)')
PY
    then row "9. Renderer gates 7-11 exercised" PASS; else row "9. Renderer gates 7-11 exercised" FAIL "gate 7-11 not exercised or failing"; fi
  else
    row "pipeline: validate_site (renderer)" FAIL "skipped — build failed"
    row "9. Renderer gates 7-11 exercised" FAIL "skipped — build failed"
  fi
fi

# --- Second brand track: the padel academy (multi-page) --------------------
# A second brand is the only thing that reveals brand-lock bugs, and a
# multi-page brand is the only thing that exercises gates 1-6 across more than
# one route. Both tracks share renderer/out and app/_tokens.generated.css, so
# they MUST run sequentially.
#
# The WEB_DESIGNER_* triple is exported rather than passed only to the render
# child because gate_9_build re-runs `npm run build` from validate_site.py with
# no env= — it inherits this process's environment. Without the export, gate 9
# rebuilds whichever brand was baked in and then validates the other one, which
# only a second brand can reveal.
PADEL_BRIEF=reports/padel-marbella/brand-brief.json
PADEL_TOKENS=reports/padel-tokens
PADEL_PLAN=reports/padel-design/design-plan.json
PADEL_OUT=reports/padel-renderer-site
PADEL_VALIDATION=reports/padel-renderer-validation
PADEL_ROUTES=reports/padel-design/routes.txt
PADEL_ASSETS=reports/padel-assets

if [[ "${SKIP_RENDERER:-0}" == "1" ]]; then
  row "10. Padel site: 5 routes validated" WARN "skipped (SKIP_RENDERER=1)"
else
  export WEB_DESIGNER_TOKENS_DIR="$ROOT/$PADEL_TOKENS"
  export WEB_DESIGNER_DESIGN_PLAN="$ROOT/$PADEL_PLAN"
  export WEB_DESIGNER_BRAND_BRIEF="$ROOT/$PADEL_BRIEF"
  PADEL_OK=0
  if run_step "$PYTHON" "$SCRIPTS/synthesize_tokens.py" --brand-brief "$PADEL_BRIEF" --reference-tokens "$REF_TOKENS" -o "$PADEL_TOKENS" \
     && run_step "$PYTHON" "$SCRIPTS/render_nextjs.py" --brand-brief "$PADEL_BRIEF" --design-plan "$PADEL_PLAN" --tokens "$PADEL_TOKENS" --assets "$PADEL_ASSETS" --routes-out "$PADEL_ROUTES" -o "$PADEL_OUT" \
     && run_step "$PYTHON" "$SCRIPTS/validate_site.py" "$PADEL_OUT" -o "$PADEL_VALIDATION" --renderer-root renderer --design-plan "$PADEL_PLAN" --routes "$(cat "$PADEL_ROUTES")"; then
    PADEL_OK=1
  fi
  if (( PADEL_OK )) && "$PYTHON" "$ROOT/tools/check_padel_gates.py"; then
    row "10. Padel site: 5 routes validated" PASS
  else
    row "10. Padel site: 5 routes validated" FAIL "multi-route validation failed"
  fi
fi

if "$PYTHON" - <<'PY'
import importlib.util, pathlib
for p in sorted(pathlib.Path('skills/web-designer/scripts').glob('*.py')):
    spec=importlib.util.spec_from_file_location('verify_'+p.stem,p); m=importlib.util.module_from_spec(spec); import sys; sys.modules[spec.name]=m; spec.loader.exec_module(m)
print('all script imports clean')
PY
then row "1. Python script imports" PASS; else row "1. Python script imports" FAIL "import failure"; fi
if uv run --with pytest pytest -q; then row "2. pytest" PASS; else row "2. pytest" FAIL "pytest failed"; fi
if "$PYTHON" -m doctest "$SCRIPTS/_output_assertions.py"; then row "3. _output_assertions doctests" PASS; else row "3. _output_assertions doctests" FAIL "doctest failed"; fi
if "$PYTHON" - <<'PY'
import re,pathlib,sys
sys.path.insert(0,'skills/web-designer/scripts'); from _output_assertions import validate_css_font_family
errs=[]
for line in pathlib.Path('reports/m6-composed-site/tokens.css').read_text().splitlines():
 m=re.search(r'--[^:]*font-family[^:]*:\s*([^;]+);',line)
 if m: errs += validate_css_font_family(m.group(1))
if errs: raise SystemExit('\n'.join(errs))
print('all emitted font-family values valid')
PY
then row "4. CSS font-family chains" PASS; else row "4. CSS font-family chains" FAIL "validate_css_font_family rejected tokens.css"; fi
if "$PYTHON" - <<'PY'
import pathlib,re
pat=re.compile(r'#[0-9a-fA-F]{3,8}\b'); hits=[]
for p in pathlib.Path('reports/m6-composed-site').rglob('*'):
 if p.is_file() and p.name!='tokens.css' and p.suffix=='.css':
  hits += [f'{p}:{i}:{x.strip()}' for i,x in enumerate(p.read_text(errors='replace').splitlines(),1) if pat.search(x)]
if hits: raise SystemExit('\n'.join(hits))
print('no raw hex outside tokens.css')
PY
then row "5. No raw hex outside tokens.css" PASS; else row "5. No raw hex outside tokens.css" FAIL "raw hex found"; fi
if "$PYTHON" - <<'PY'
import json,pathlib
p=pathlib.Path('reports/m6-validation/gate-results.json'); d=json.loads(p.read_text()); rs=d.get('results',[])
if any(r.get('verdict')=='FAIL' for r in rs): raise SystemExit('gate FAILED')
# NOT-EXERCISED is only acceptable when the gate DECLARED itself inapplicable to
# this artifact — gates 9/10 (Next.js build/bundle) genuinely cannot run against
# the static composer's output. A gate that skipped without declaring
# `applicable: false` is a silent hole and still fails here. The renderer path
# above is what proves 9/10 actually pass somewhere.
silent=[r.get('id') for r in rs
        if r.get('verdict')=='NOT-EXERCISED'
        and (r.get('observations') or {}).get('applicable') is not False]
if silent: raise SystemExit('gate NOT-EXERCISED without declaring inapplicability: '+', '.join(map(str,silent)))
report=pathlib.Path('reports/m6-validation/validation-report.md').read_text()
if not any(x in report for x in ('Acceptance tier: Validated','**Acceptance tier:** `Validated`','**Acceptance tier:** Validated','Reached tier: `Validated`')): raise SystemExit('tier != Validated')
n_skipped=len(rs)-sum(1 for r in rs if r.get('verdict')=='PASS')
print(f'composer gates PASS ({n_skipped} declared inapplicable); tier Validated')
PY
then row "6. Gate table and tier" PASS; else row "6. Gate table and tier" FAIL "gate failure, NOT-EXERCISED, or tier mismatch"; fi
if "$PYTHON" - <<'PY'
import hashlib,json,pathlib
site=pathlib.Path('reports/m6-composed-site'); d=json.loads(pathlib.Path('reports/m6-validation/gate-results.json').read_text()); got=d.get('meta',{}).get('input_hashes',{}); exp={n:hashlib.sha256((site/n).read_bytes()).hexdigest() for n in ('index.html','styles.css','tokens.css')}
if got!=exp: raise SystemExit(f'stale input_hashes: expected {exp}, got {got}')
print('gate-results input_hashes match current composed artifacts')
PY
then row "7. Validation staleness hashes" PASS; else row "7. Validation staleness hashes" FAIL "gate-results.json is stale"; fi

# 8. Vision design critique — ADVISORY ONLY. Scored against a 7-dimension rubric by
# critique_pass.py; printed in the summary table but never blocks verify.sh.
# Hard correctness gates (rows 1-7) stay the only thing that can fail verify.sh.
if [[ "${WITH_CRITIQUE:-0}" == "1" ]]; then
  CRITIQUE_DIR=reports/m6-critique
  rm -rf "$CRITIQUE_DIR"
  if "$PYTHON" "$SCRIPTS/critique_pass.py" \
       --site "$PLAN_OUT" --brand-brief "$BRIEF" --design-plan "$PLAN" \
       -o "$CRITIQUE_DIR" \
       --tokens "$TOKENS" --reference-report "$REF" --reference-tokens "$REF_TOKENS" \
       >reports/critique.log 2>&1; then
    if [[ -s "$CRITIQUE_DIR/iterations.json" ]]; then
      SCORES=$(python3 -c "import json; d=json.load(open('$CRITIQUE_DIR/iterations.json')); print(','.join(str(sum(int(h['scores'][k]['score']) for k in ('visual_hierarchy','use_of_space','typographic_contrast','focal_point','brand_fit','motion_restraint','looks_templated')))+'/70' for h in d))" 2>/dev/null || echo "parse-error")
      LAST=$(python3 -c "import json; d=json.load(open('$CRITIQUE_DIR/iterations.json')); s=d[-1]['scores']; print(' '.join(f\"{k}={s[k]['score']}\" for k in ('visual_hierarchy','use_of_space','typographic_contrast','focal_point','brand_fit','motion_restraint','looks_templated')))" 2>/dev/null || echo "parse-error")
      row "8. Vision critique (advisory)" PASS "iter scores: $SCORES — $LAST"
    else
      row "8. Vision critique (advisory)" WARN "no iterations.json — see reports/critique.log"
    fi
  else
    # critique_pass.py is designed to be non-blocking: missing API key, 402
    # insufficient balance, or any transient API issue must WARN, not FAIL.
    row "8. Vision critique (advisory)" WARN "vision API unavailable — see reports/critique.log"
  fi
fi
printf '\n%-40s %-8s %s\n' CHECK STATUS DETAIL
printf '%-40s %-8s %s\n' '----------------------------------------' '--------' '------'
for r in "${rows[@]}"; do IFS='|' read -r s n d <<<"$r"; printf '%-40s %-8s %s\n' "$n" "$s" "$d"; done
printf '\nSummary: %d failure(s), %d warning(s)\n' "$failures" "$warns"
(( failures == 0 ))
