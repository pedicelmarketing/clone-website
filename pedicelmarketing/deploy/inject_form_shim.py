#!/usr/bin/env python3
"""Add the form submit shim to every page that has a captured Webflow form.

Self-hosted, Webflow forms fail silently (see form-shim.js); the shim routes them to
our relay (/api/forms/*), which records the lead in the Hub CRM and emails the owner.
Idempotent: pages that already load the shim are left alone.

  python3 deploy/inject_form_shim.py <site-root> [<site-root> ...]
"""
import pathlib
import shutil
import sys

TAG = '<script src="/form-shim.js" defer></script>'
FORM_IDS = ("wf-form-Audit-Form", "wf-form-Email-Form-Version-Two")
SHIM = pathlib.Path(__file__).with_name("form-shim.js")

for root in map(pathlib.Path, sys.argv[1:]):
    shutil.copyfile(SHIM, root / "form-shim.js")
    for page in root.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        if not any(f in text for f in FORM_IDS) or "/form-shim.js" in text:
            continue
        if "</body>" not in text:
            print(f"skip (no </body>): {page}")
            continue
        page.write_text(text.replace("</body>", f"{TAG}</body>", 1), encoding="utf-8")
        print(f"shim added: {page.relative_to(root)}")
