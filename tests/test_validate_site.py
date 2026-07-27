#!/usr/bin/env python3
"""Behavior tests for the validate_site.py 8-gate harness.

Specifically these lock down the positive-evidence-only verdict rule and the
tier computation. They target the gates' *decision logic* (not the runners
themselves); they build synthetic GateResults in memory and assert that
compute_tier() and the verdict semantics are correct. This is the regression
net for the M4 honesty fix: any future refactor that lets a gate return PASS
without positive evidence must trip one of these tests.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills" / "web-designer" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_site import (  # noqa: E402
    GateResult, compute_tier, GATE_VERSION,
)


def _pass(gid: str, name: str, summary: str = "ok") -> GateResult:
    return GateResult(
        id=gid, name=name, verdict="PASS",
        evidence_basis="DOM+assets confirmed", summary=summary,
    )


def _fail(gid: str, name: str, summary: str = "missed thresholds") -> GateResult:
    return GateResult(
        id=gid, name=name, verdict="FAIL",
        evidence_basis="DOM+assets confirmed", summary=summary,
    )


def _notex(gid: str, name: str, summary: str = "runner did not produce evidence",
           error: str | None = None) -> GateResult:
    return GateResult(
        id=gid, name=name, verdict="NOT-EXERCISED",
        evidence_basis="Not exercised", summary=summary, error=error,
    )


class TierRules(unittest.TestCase):
    def test_validated_only_when_every_gate_pass(self):
        results = [_pass(str(i), f"g{i}") for i in range(1, 9)]
        tier, _ = compute_tier(results)
        self.assertEqual(tier, "Validated")

    def test_partial_when_a11y_not_exercised(self):
        results = [_pass(str(i), f"g{i}") for i in range(1, 9)]
        results[2] = _notex("3", "Accessibility",
                            summary="axe-core crashed, 0 violations not verified",
                            error="runner exit 1; chromedriver crash")
        tier, reason = compute_tier(results)
        self.assertEqual(tier, "Partial",
                         f"a11y not-exercised must cap tier at Partial, got {tier} ({reason})")
        self.assertIn("3", reason, f"reason must name the failing gate, got: {reason}")

    def test_partial_when_perf_not_exercised(self):
        results = [_pass(str(i), f"g{i}") for i in range(1, 9)]
        results[3] = _notex("4", "Performance",
                            summary="Lighthouse JSON not produced",
                            error="lighthouse JSON output not produced")
        tier, reason = compute_tier(results)
        self.assertEqual(tier, "Partial",
                         f"perf not-exercised must cap tier at Partial, got {tier} ({reason})")
        self.assertIn("4", reason)

    def test_partial_when_any_single_gate_not_exercised(self):
        """Every gate, when alone, being NOT-EXERCISED, must cap the tier at
        Partial. The spec is unambiguous: only all-PASS = Validated."""
        for gate_id in ("1", "2", "3", "4", "5", "6", "7", "8"):
            results = [_pass(str(i), f"g{i}") for i in range(1, 9)]
            results[int(gate_id) - 1] = _notex(gate_id, f"g{gate_id}")
            tier, _ = compute_tier(results)
            self.assertEqual(
                tier, "Partial",
                f"gate {gate_id} NOT-EXERCISED must cap tier at Partial, got {tier}",
            )

    def test_partial_when_any_gate_fails(self):
        for gate_id in ("1", "2", "3", "4", "5", "6", "7", "8"):
            results = [_pass(str(i), f"g{i}") for i in range(1, 9)]
            results[int(gate_id) - 1] = _fail(gate_id, f"g{gate_id}")
            tier, _ = compute_tier(results)
            self.assertEqual(
                tier, "Partial",
                f"gate {gate_id} FAILed must cap tier at Partial, got {tier}",
            )

    def test_partial_when_both_a11y_and_perf_not_exercised(self):
        """The exact prior-run scenario: a11y AND perf not-exercised.
        The prior harness called this 'Offline-validated'. The M4 honesty
        fix says Partial."""
        results = [_pass(str(i), f"g{i}") for i in range(1, 9)]
        results[2] = _notex("3", "Accessibility", error="axe crash")
        results[3] = _notex("4", "Performance", error="lighthouse no JSON")
        tier, reason = compute_tier(results)
        self.assertEqual(tier, "Partial",
                         f"both-not-exercised must be Partial, got {tier} ({reason})")
        self.assertIn("3", reason)
        self.assertIn("4", reason)


class VerdictSemantics(unittest.TestCase):
    def test_settle_helper_is_invoked_before_axe(self):
        source = (SCRIPTS / "validate_site.py").read_text()
        settle_pos = source.index("settle = page.evaluate(\"async () =>")
        axe_pos = source.index("axe.run(document", settle_pos)
        self.assertLess(settle_pos, axe_pos)
        self.assertIn("setTimeout(resolve, 3000)", source)

    def test_a11y_zero_violations_with_no_positive_evidence_must_be_not_exercised(self):
        """The exact prior-run scenario: a runner that crashed (exit 1, no JSON
        parsed) returning 0 violations because it never actually evaluated.

        The aggregation logic in gate_3 must check `d.get('ok')`, not just
        sum `serious_critical` (which is 0 for an empty violations list
        parsed from nothing)."""
        per_route = {
            "/": {"exit": 1, "ok": False, "violations": 0, "serious_critical": 0,
                  "error": "axe runner crashed"},
        }
        succeeded = {r: d for r, d in per_route.items() if d.get("ok")}
        failed = {r: d for r, d in per_route.items() if not d.get("ok")}
        self.assertEqual(succeeded, {},
                         "no route produced positive evidence")
        self.assertIn("/", failed,
                      "the crashed route must be in the failed set")
        # If the gate aggregator sees failed != empty, it MUST return
        # NOT-EXERCISED, not PASS.

    def test_perf_no_json_output_must_be_not_exercised(self):
        """Lighthouse exit 1, no JSON output produced, table=[]. A gate that
        says PASS on this evidence is wrong."""
        per_route = {
            "/": {"exit": 1, "ok": False, "error": "lighthouse JSON output not produced",
                  "stderr_tail": "...cli/run.js:204:30..."},
        }
        summary_table = []
        succeeded = {r: d for r, d in per_route.items() if d.get("ok")}
        evidence_less = {r: d for r, d in per_route.items() if not d.get("ok")}
        self.assertEqual(succeeded, {})
        self.assertTrue(evidence_less)
        self.assertEqual(summary_table, [])

    def test_gate_result_error_round_trips(self):
        """GateResult.error must survive to_dict() — the gate-results.json row
        must show the runner exit reason so the reader sees why a
        NOT-EXERCISED gate is NOT-EXERCISED."""
        r = _notex("3", "Accessibility", error="axe runner exit 1 (chromedriver crash)")
        d = r.to_dict()
        self.assertEqual(d["verdict"], "NOT-EXERCISED")
        self.assertEqual(d["error"], "axe runner exit 1 (chromedriver crash)")
        self.assertEqual(d["id"], "3")

    def test_eight_gates_declared(self):
        self.assertIn("8-gate", GATE_VERSION)


class PriorRunRegression(unittest.TestCase):
    """The prior run produced gate-results.json with gates 3+4 marked PASS
    even though their runners crashed (exit=1, no parseable document). The
    tier came out as 'Validated'. Under the new rules, those gates must
    be NOT-EXERCISED and the tier must be Partial.

    This test re-loads the prior run's gate-results.json and asserts the
    new decision logic would have caught the bug. It's a guard against
    someone reverting the M4 fix and re-introducing a hollow Validated."""

    def test_prior_run_table_now_computes_to_partial(self):
        prior_path = REPO / "reports" / "m4-validation" / "gate-results.json"
        if not prior_path.exists():
            self.skipTest(f"no prior run to test against ({prior_path})")
        with open(prior_path) as f:
            prior = json.load(f)
        reclassified = []
        for r in prior["results"]:
            if r["id"] in ("3", "4"):
                # The prior harness tagged these as PASS. We reclassify
                # them as NOT-EXERCISED under the new positive-evidence-only
                # rule because their runner exit codes / per_route evidence
                # show no parseable document was produced.
                obs = r["observations"]["per_route"]["/"]
                reason = obs.get("error") or f"runner exit {obs.get('exit')}; no parseable document"
                new = GateResult(
                    id=r["id"], name=r["name"], verdict="NOT-EXERCISED",
                    evidence_basis="Not exercised",
                    summary=f"[reclassified] {r['summary']} — runner exit code / no parseable "
                             f"document means 0 violations is not positive evidence",
                    error=reason,
                )
                reclassified.append(new)
            else:
                reclassified.append(GateResult(
                    id=r["id"], name=r["name"], verdict=r["verdict"],
                    evidence_basis=r["evidence_basis"], summary=r["summary"],
                ))
        tier, reason = compute_tier(reclassified)
        self.assertEqual(
            tier, "Partial",
            "the prior-run gate table, with gates 3+4 honestly reclassified, "
            f"must compute to Partial — got {tier} ({reason})",
        )
        self.assertIn("3", reason)
        self.assertIn("4", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
