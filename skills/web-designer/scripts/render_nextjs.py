#!/usr/bin/env python3
"""Next.js renderer adapter — a drop-in replacement for compose_site.py.

Why this exists
---------------
`critique_pass.py` runs an improve loop: critique -> apply revisions to the design
plan -> RECOMPOSE -> critique again. It recomposes by invoking a "compose script"
with a fixed argument shape:

    <script> --brand-brief X --design-plan Y --tokens Z -o <site_dir>

`compose_site.py` (the plain HTML/CSS emitter) satisfies that contract. The Next.js
renderer did not, so the improve loop could only ever run against the static
composer — where revisions like "two-column at >=1024px" had no grid primitives to
act on, and the score moved 39 -> 41 over two iterations.

This adapter gives the Next.js renderer the same contract: it syncs the tokens,
builds the static export, and copies the result to the requested output directory.
The loop can then drive the *real* renderer without knowing anything about npm.

Honesty notes
-------------
- Exits nonzero if the build fails. A failed build must never look like a success
  to the caller (the loop treats a nonzero compose as a failed iteration).
- Does not fabricate output: if `out/` is missing after a "successful" build, that
  is reported as a failure rather than leaving a stale directory in place.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# skills/web-designer/scripts -> repo root
REPO_ROOT = HERE.parent.parent.parent
RENDERER = REPO_ROOT / "renderer"


def run(cmd: list[str], cwd: Path, label: str, env: dict | None = None) -> None:
    print(f"[render_nextjs] {label}: {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-2000:])
        sys.stderr.write(proc.stderr[-2000:])
        raise SystemExit(f"[render_nextjs] {label} failed with exit {proc.returncode}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--brand-brief", required=True)
    ap.add_argument("--design-plan", required=True)
    ap.add_argument("--tokens", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--reference-report")  # accepted for contract compatibility
    ap.add_argument("--project-slug")
    args = ap.parse_args(argv)

    if not RENDERER.is_dir():
        raise SystemExit(f"[render_nextjs] renderer/ not found at {RENDERER}")

    plan = Path(args.design_plan).resolve()
    if not plan.is_file():
        raise SystemExit(f"[render_nextjs] design plan not found: {plan}")
    # Fail fast on a malformed plan rather than letting the build emit a broken page.
    json.loads(plan.read_text(encoding="utf-8"))

    if not (RENDERER / "node_modules").is_dir():
        run(["npm", "install", "--silent"], RENDERER, "npm install")

    # Point the renderer at THIS brand's artifacts. Without these the renderer
    # falls back to hardcoded paths and silently renders whichever brand happens
    # to be baked in — it rendered brand B's plan entirely in brand A's palette
    # until a second brand exposed it.
    env = dict(os.environ)
    env["WEB_DESIGNER_TOKENS_DIR"] = str(Path(args.tokens).resolve())
    env["WEB_DESIGNER_DESIGN_PLAN"] = str(plan)

    # Tokens first: the renderer's Tailwind theme is generated from them.
    run(["npm", "run", "sync:tokens"], RENDERER, "sync tokens", env=env)
    run(["npm", "run", "build"], RENDERER, "next build", env=env)

    out_src = RENDERER / "out"
    if not out_src.is_dir() or not (out_src / "index.html").is_file():
        raise SystemExit(
            "[render_nextjs] build reported success but renderer/out/index.html is "
            "missing — refusing to report success without the artifact"
        )

    dest = Path(args.out).resolve()
    # The improve loop passes -o renderer/out, i.e. the build's OWN output dir.
    # Blindly rmtree-ing dest would delete the artifact we just built and then
    # fail copying it into itself. When they are the same path, the build has
    # already put the files exactly where the caller wants them.
    if dest == out_src.resolve():
        print(str(dest))
        return 0
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(out_src, dest)
    print(str(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
