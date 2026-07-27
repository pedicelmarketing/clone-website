#!/usr/bin/env python3
"""LLM design-decision pass: model emits JSON data, never site files."""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys
from pathlib import Path
from urllib import request

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "design_plan_schema.json"
sys.path.insert(0, str(HERE))
from _secrets import require_minimax_key  # noqa: E402


def resolve_path(document, dotted):
    node = document
    parts = dotted.replace('[', '.').replace(']', '').split('.')
    for part in parts:
        if not part: continue
        if isinstance(node, dict) and part in node: node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node): node = node[int(part)]
        else: return None
    return node


def _nonempty(value):
    if value is None or value == "": return False
    if isinstance(value, (list, dict)) and not value: return False
    return True


def verify_source_fields(plan, brief):
    violations = []
    for collection in ('sections', 'copy_blocks'):
        for index, item in enumerate(plan.get(collection, [])):
            fields = item.get('source_brief_fields', [])
            label = f'{collection}[{index}]'
            if not fields: violations.append(f'{label}: source_brief_fields must be non-empty')
            for field in fields:
                value = resolve_path(brief, field)
                if not _nonempty(value): violations.append(f'{label}: source field does not resolve to a non-empty value: {field}')
    return violations


def validate_plan(plan, brief):
    try:
        import jsonschema
        errors = sorted(jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(plan), key=lambda e: list(e.absolute_path))
        violations = ['/'.join(map(str, e.absolute_path)) + ': ' + e.message for e in errors]
    except Exception as exc:
        violations = [f'schema validation unavailable: {exc}']
    return violations + verify_source_fields(plan, brief)


def compact_reference(root):
    root = Path(root); out = {'files': [], 'counts': {}}
    for name in ('tokens/color.json','tokens/typography.json','tokens/spacing.json','tokens/radius.json','tokens/shadow.json','copy.json','components.json','breakpoints.json'):
        p = root / name
        if not p.is_file(): continue
        data = json.loads(p.read_text())
        out['files'].append(name)
        if name == 'copy.json':
            out['counts']['copy_blocks'] = sum(len(v) for v in data.values() if isinstance(v, list))
            out['sections'] = sorted({x.get('section_index') for v in data.values() if isinstance(v, list) for x in v if isinstance(x, dict) and 'section_index' in x})
        elif name == 'components.json':
            comps = data.get('components', data if isinstance(data, list) else [])
            out['counts']['components'] = len(comps) if isinstance(comps, list) else 0
            out['component_names'] = [x.get('name') for x in comps[:30] if isinstance(x, dict) and x.get('name')]
        elif name == 'breakpoints.json':
            out['breakpoints'] = [(x.get('label'), x.get('min_width_px')) for x in data.get('breakpoints', [])]
        elif name.endswith('typography.json'):
            out['typography'] = data
        elif name.endswith('color.json'):
            out['colors'] = data
    return out


def call_model(brief, reference, model, feedback=''):
    key = require_minimax_key('design_pass.call_model')
    system = '''You are a senior web designer. Return JSON only matching the supplied schema. Produce a plan, never files. State a layout thesis first; every section serves it. For every section supply a short human nav_label (1-2 words, or null) and in_nav boolean; footer, colophon, legal and utility sections must have in_nav false. Forbidden defaults: centered-everything hero, three-column feature grid with icons, purple/blue gradients, uniform rounded corners, Inter-for-everything, generic stock-photo layout. Choose one memorable brand-specific SIGNATURE ELEMENT. Vary order and emphasis for this brand, never a fixed template. Invent layout, structure, emphasis, and phrasing, but NEVER facts: cite only real non-empty brand brief dotted paths in source_brief_fields. Empty/missing evidence belongs in skipped_sections.'''
    payload = {'model': model, 'max_tokens': 6000, 'system': system, 'messages': [{'role':'user','content': 'Schema:\n'+SCHEMA.read_text()+'\nBrand brief:\n'+json.dumps(brief)+'\nCompact reference analysis:\n'+json.dumps(reference)+'\nValidation feedback from prior attempt:\n'+feedback}]}
    req = request.Request('https://api.minimax.io/anthropic/v1/messages', data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer '+key, 'Content-Type':'application/json'}, method='POST')
    with request.urlopen(req, timeout=120) as response: body = json.loads(response.read())
    text = ''.join(x.get('text','') for x in body.get('content',[]) if isinstance(x,dict))
    if '```' in text: text = text.split('```json',1)[-1].split('```',1)[0]
    return json.loads(text.strip())


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--brand-brief',required=True); ap.add_argument('--reference'); ap.add_argument('-o',required=True); ap.add_argument('--model',default='MiniMax-M3'); ap.add_argument('--max-retries',type=int,default=2); args=ap.parse_args(argv)
    brief_path=Path(args.brand_brief); brief=json.loads(brief_path.read_text())
    validator=HERE/'validate_brand_brief.py'
    import importlib.util
    spec = importlib.util.spec_from_file_location('validate_brand_brief', validator)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    schema = json.loads((HERE/'brand_brief_schema.json').read_text())
    try:
        valid, brief_errors = module._jsonschema_validate(schema, brief)
    except Exception:
        valid, brief_errors, _ = module._fallback_validate(schema, brief)
    if not valid:
        print('invalid brand brief:\n'+'\n'.join(brief_errors),file=sys.stderr); return 1
    reference=compact_reference(args.reference) if args.reference else {'available': False}
    feedback=''; plan=None
    for attempt in range(args.max_retries+1):
        try:
            plan=call_model(brief, reference, args.model, feedback)
            plan['schema_version'] = '1.0'
            plan['project_slug'] = brief['project_slug']
            plan['generated_at'] = dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
            plan['model'] = args.model
            violations=validate_plan(plan,brief)
        except Exception as exc: violations=[str(exc)]
        if not violations: break
        feedback='\n'.join(violations)
        print(f'attempt {attempt+1} rejected: {feedback}',file=sys.stderr)
        plan=None
    if plan is None: return 1
    Path(args.o).parent.mkdir(parents=True,exist_ok=True); Path(args.o).write_text(json.dumps(plan,indent=2)+'\n'); print(args.o); return 0
if __name__ == '__main__': sys.exit(main())
