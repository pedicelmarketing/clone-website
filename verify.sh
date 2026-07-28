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
if run_step "$PYTHON" "$SCRIPTS/validate_site.py" "$PLAN_OUT" -o "$VALIDATION"; then row "pipeline: validate_site" PASS; else row "pipeline: validate_site" FAIL "command failed"; fi

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
if any(r.get('verdict')=='NOT-EXERCISED' for r in rs): raise SystemExit('gate NOT-EXERCISED')
report=pathlib.Path('reports/m6-validation/validation-report.md').read_text()
if not any(x in report for x in ('Acceptance tier: Validated','**Acceptance tier:** `Validated`','**Acceptance tier:** Validated','Reached tier: `Validated`')): raise SystemExit('tier != Validated')
print('8/8 gates PASS; tier Validated')
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
