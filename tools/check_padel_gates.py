#!/usr/bin/env python3
"""Assert the padel site's gate results actually cover all five routes.

Kept as a file rather than an inline heredoc in verify.sh because the shell
block that calls it already lives inside one, and nesting heredocs is how you
get a script that silently truncates.

The route-count assertions matter as much as the verdicts. `--routes` was
declared without a type for the whole life of the project, so argparse handed
`run()` a raw string and it iterated one character at a time: multi-route
validation had never once executed, and gate 5 had only ever taken its
single-route shortcut. A regression there would report a clean sweep of PASSes
while four fifths of the site went unchecked, which is exactly the shape of
failure these gates exist to prevent.
"""

import json
import pathlib
import sys

RESULTS = pathlib.Path("reports/padel-renderer-validation/gate-results.json")
EXPECTED_ROUTES = 5


def main() -> int:
    if not RESULTS.is_file():
        print(f"missing {RESULTS}", file=sys.stderr)
        return 1
    data = json.loads(RESULTS.read_text())
    results = {r["id"]: r for r in data.get("results", [])}
    routes = data.get("routes") or []

    if len(routes) != EXPECTED_ROUTES:
        print(f"expected {EXPECTED_ROUTES} routes, got {routes!r}", file=sys.stderr)
        return 1

    bad = [f"{i}:{r['verdict']}" for i, r in results.items() if r["verdict"] != "PASS"]
    if bad:
        print("padel gate(s) not PASS: " + ", ".join(sorted(bad)), file=sys.stderr)
        for i, r in sorted(results.items()):
            if r["verdict"] != "PASS":
                print(f"  {i} {r['name']}: {r.get('summary', '')}", file=sys.stderr)
        return 1

    # Positive evidence that the multi-route path ran, not just that it passed.
    boot = results.get("1", {}).get("summary", "")
    if f"All {EXPECTED_ROUTES} route(s)" not in boot:
        print(f"gate 1 did not report {EXPECTED_ROUTES} routes: {boot}", file=sys.stderr)
        return 1
    if not (results.get("5", {}).get("observations") or {}).get("per_route"):
        print("gate 5 is still on its single-route branch", file=sys.stderr)
        return 1

    fidelity = results.get("11", {}).get("summary", "")
    print(f"padel: {len(results)}/{len(results)} gates PASS across {len(routes)} routes")
    print(f"  {fidelity}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
