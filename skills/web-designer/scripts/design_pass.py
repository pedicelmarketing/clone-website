#!/usr/bin/env python3
"""LLM design-decision pass: model emits JSON data, never site files."""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys
from pathlib import Path
from urllib import request

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "design_plan_schema.json"
sys.path.insert(0, str(HERE))
from _secrets import require_minimax_key, get_minimax_key  # noqa: E402
# Reuse the provider plumbing already built and tested for the critique loop
# rather than growing a second copy of it. Same rule applies here: the design
# pass is the pipeline's only source of design decisions, so one vendor's
# billing state must not be able to stop it outright.
from critique_pass import (  # noqa: E402
    DEFAULT_MODELS, _gemini_key, _vision_call_gemini, _is_provider_unavailable,
)


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


def validate_plan(plan, brief, assets=None):
    try:
        import jsonschema
        errors = sorted(jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(plan), key=lambda e: list(e.absolute_path))
        violations = ['/'.join(map(str, e.absolute_path)) + ': ' + e.message for e in errors]
    except Exception as exc:
        violations = [f'schema validation unavailable: {exc}']
    # Media filenames must reference REAL fetched assets. Without this the model
    # can cite a plausible-looking filename (or a stock URL) and the renderer emits
    # a broken <img> — the image equivalent of inventing a testimonial.
    allowed = {a['file'] for a in (assets or [])}
    for i, sec in enumerate(plan.get('sections') or []):
        media = sec.get('media')
        if not media:
            continue
        fname = media.get('file')
        if not allowed:
            violations.append(f"sections[{i}].media: no brand photography was fetched, so no section may declare media")
        elif fname not in allowed:
            violations.append(
                f"sections[{i}].media.file '{fname}' is not in the fetched asset manifest; "
                f"use one of the supplied filenames verbatim (never invent or use stock)")
        if not (media.get('alt') or '').strip():
            violations.append(f"sections[{i}].media.alt is required and must describe the photo")
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


def call_model(brief, reference, model, feedback='', assets=None, provider='minimax'):
    system = '''You are a senior web designer. Return JSON only matching the supplied schema. Produce a plan, never files. State a layout thesis first; every section serves it. For every section supply a short human nav_label (1-2 words, or null) and in_nav boolean; footer, colophon, legal and utility sections must have in_nav false. Forbidden defaults: centered-everything hero, three-column feature grid with icons, purple/blue gradients, uniform rounded corners, Inter-for-everything, generic stock-photo layout. Choose one memorable brand-specific SIGNATURE ELEMENT. LAYOUT IS YOUR MAIN LEVER: give every section an explicit `layout` from the schema enum and VARY IT DELIBERATELY — a page where most sections share a layout is exactly the templated output we are rejecting. Aim for a distinct opening (split-hero), at least one full-bleed or feature-split moment if brand photography exists, one pull-quote or index-list, a proof-row where real proof exists, and a cta-band. Include a `masthead` section (its headline is the site wordmark, its subhead the tagline) and mark `in_nav` true on the sections a visitor would navigate to. Vary order and emphasis for this brand, never a fixed template. Invent layout, structure, emphasis, and phrasing, but NEVER facts: cite only real non-empty brand brief dotted paths in source_brief_fields. Empty/missing evidence belongs in skipped_sections.
REAL BRAND PHOTOGRAPHY: you are given an inventory of the brand's OWN photographs that have already been downloaded. Place them deliberately via each section's optional `media` object ({file, alt, treatment, rationale}). Rules: `file` MUST be one of the supplied filenames verbatim — never invent one, never reference stock imagery or a URL. `alt` must genuinely describe that photo (use its subject). Choose `treatment` to serve the layout thesis. A page carrying the brand's real photography beats a text-only page, so use the good ones; but a section with no suitable photo should simply omit media rather than force a bad fit.'''
    payload = {'model': model, 'max_tokens': 6000, 'system': system, 'messages': [{'role':'user','content': 'Schema:\n'+SCHEMA.read_text()+'\nBrand brief:\n'+json.dumps(brief)+'\nCompact reference analysis:\n'+json.dumps(reference)+'\nAvailable brand photographs (use filenames verbatim in sections[].media.file):\n'+json.dumps(assets or [])+'\nValidation feedback from prior attempt:\n'+feedback}]}
    if provider == 'gemini':
        # _vision_call_gemini normalises Gemini's reply into the Anthropic
        # response shape, so the parsing below stays provider-agnostic. It also
        # raises (rather than returning half a document) when the model is
        # truncated or blocked.
        body = _vision_call_gemini(model, system, payload['messages'], timeout=120)
    else:
        key = require_minimax_key('design_pass.call_model')
        req = request.Request('https://api.minimax.io/anthropic/v1/messages', data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer '+key, 'Content-Type':'application/json'}, method='POST')
        with request.urlopen(req, timeout=120) as response: body = json.loads(response.read())
    text = ''.join(x.get('text','') for x in body.get('content',[]) if isinstance(x,dict))
    if '```' in text: text = text.split('```json',1)[-1].split('```',1)[0]
    return json.loads(text.strip())


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--brand-brief',required=True); ap.add_argument('--reference'); ap.add_argument('-o',required=True); ap.add_argument('--model',default=None,help='model id; defaults per provider'); ap.add_argument('--provider',default='auto',choices=('auto','minimax','gemini'),help="'auto' (default) uses minimax and fails over to gemini only when minimax is "
     'unavailable for billing/auth reasons');  ap.add_argument('--max-retries',type=int,default=2); ap.add_argument('--assets',help='dir containing ASSET-MANIFEST.json from fetch_brand_assets.py'); args=ap.parse_args(argv)
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
    # Real brand photography available to place. Only files listed here may be used;
    # validate_plan enforces that so the model cannot invent a filename or reach for stock.
    assets=[]
    if args.assets:
        mpath=Path(args.assets)/'ASSET-MANIFEST.json'
        if mpath.is_file():
            assets=[{'file':a['file'],'subject':a.get('subject',''),
                     'width':a.get('width'),'height':a.get('height')}
                    for a in json.loads(mpath.read_text()).get('assets',[])]
        else:
            print(f'warning: no ASSET-MANIFEST.json in {args.assets}; designing without photography',file=sys.stderr)
    # Provider chain. Explicit --provider pins one; 'auto' allows a single
    # failover, and ONLY when the first provider is unavailable for
    # billing/auth reasons (401/402/403) — states no retry can fix. A
    # malformed response is NOT a reason to switch vendors.
    if args.provider == 'auto':
        chain=[('minimax', args.model or DEFAULT_MODELS['minimax']),
               ('gemini', DEFAULT_MODELS['gemini'])]
    else:
        chain=[(args.provider, args.model or DEFAULT_MODELS[args.provider])]
    key_probe={'minimax':get_minimax_key,'gemini':_gemini_key}
    chain=[(p,m) for p,m in chain if key_probe[p]()]
    if not chain:
        print('ERROR: no model provider key could be resolved (checked MINIMAX_API_KEY and '
              'GEMINI_API_KEY/GOOGLE_API_KEY in the environment and the known .env files)',
              file=sys.stderr)
        return 1

    feedback=''; plan=None
    for provider, model in chain:
        for attempt in range(args.max_retries+1):
            try:
                plan=call_model(brief, reference, model, feedback, assets, provider)
                plan['schema_version'] = '1.0'
                plan['project_slug'] = brief['project_slug']
                plan['generated_at'] = dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
                # Record the provider that actually answered, not the one asked
                # for — with failover in play they are not the same thing.
                plan['provider'] = provider
                plan['model'] = model
                violations=validate_plan(plan,brief,assets)
            except Exception as exc:
                if _is_provider_unavailable(exc):
                    print(f"provider '{provider}' unavailable ({exc}); failing over",file=sys.stderr)
                    plan=None
                    break
                violations=[str(exc)]
            if not violations: break
            feedback='\n'.join(violations)
            print(f'attempt {attempt+1} rejected: {feedback}',file=sys.stderr)
            plan=None
        if plan is not None: break
    if plan is None: return 1
    Path(args.o).parent.mkdir(parents=True,exist_ok=True); Path(args.o).write_text(json.dumps(plan,indent=2)+'\n'); print(args.o); return 0
if __name__ == '__main__': sys.exit(main())
