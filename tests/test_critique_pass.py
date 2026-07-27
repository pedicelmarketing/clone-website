#!/usr/bin/env python3
"""Tests for the deterministic parts of critique_pass.py.

We do NOT test the vision-API call (that requires a live key + money and is
inherently non-deterministic). We DO test:
  - apply_revisions enforces section existence, rejects vague changes,
    preserves the source_brief_fields contract (inv-nothing)
  - rubric dimensions are all present and ordered
  - the regression guard / summary builder produce the right table
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "web-designer" / "scripts" / "critique_pass.py"
_spec = importlib.util.spec_from_file_location("critique_pass", SCRIPT)
assert _spec and _spec.loader
cp = importlib.util.module_from_spec(_spec)
import sys
sys.modules["critique_pass"] = cp
_spec.loader.exec_module(cp)


def _tiny_brief():
    return {
        "project_slug": "smoke",
        "voice_and_tone": {
            "register": "conversational-professional",
            "sentence_case": True,
            "favorite_words": ["unique", "customised"],
            "banned_words": ["synergy", "leverage"],
            "formality_score_1to5": 3,
            "avg_sentence_length_words": 13,
            "example_lines": ["All brands are unique."],
            "notes": "Teacher register.",
        },
        "service_facts": [{"name": "Social Media Marketing"}],
        "real_photo_inventory": ["logo.png"],
        "brand_donts": ["three-column feature grid"],
    }


def _tiny_plan():
    return {
        "schema_version": "1.0",
        "project_slug": "smoke",
        "generated_at": "2026-01-01T00:00:00Z",
        "model": "MiniMax-M3",
        "layout_thesis": {
            "statement": "A workbook.",
            "audience": "Skeptical SMB owners.",
            "job_to_be_done": "Book a call.",
            "why_this_not_generic": "Teacher voice.",
        },
        "sections": [
            {"id": "cover", "order": 0, "purpose": "Set tone.", "component": "Asymmetric cover.",
             "emphasis": "hero", "source_brief_fields": ["voice_and_tone.register"], "rationale": "On-voice.",
             "in_nav": False, "nav_label": None},
            {"id": "manifesto", "order": 1, "purpose": "Beliefs.", "component": "Two-column editorial.",
             "emphasis": "primary", "source_brief_fields": ["voice_and_tone.notes"], "rationale": "On-voice.",
             "in_nav": True, "nav_label": "Manifesto"},
        ],
        "signature_element": {
            "name": "Gold dot",
            "description": "Carried from the logo.",
            "why_it_fits_brand": "Distinctive.",
            "implementation_note": "Margin marker.",
        },
        "motion_vocabulary": {"register": "restrained", "effects": ["fade"], "rationale": "Calm."},
        "copy_blocks": [
            {"section_id": "cover", "role": "headline", "text": "All brands are unique.",
             "source_brief_fields": ["voice_and_tone.example_lines"]},
        ],
        "skipped_sections": [],
        "decisions": [],
    }


class ApplyRevisionsContract(unittest.TestCase):
    def test_unknown_section_is_rejected(self):
        plan = _tiny_plan()
        new_plan, msgs = cp._apply_revisions(
            plan,
            [{"section_id": "does-not-exist", "change": "Make it two columns.",
              "rationale": "Use space.", "addressed_observation": "left empty."}],
            _tiny_brief(),
        )
        self.assertTrue(any(m.startswith("REJECTED") and "does-not-exist" in m for m in msgs))
        self.assertEqual(plan, new_plan)

    def test_vague_change_is_rejected(self):
        plan = _tiny_plan()
        _, msgs = cp._apply_revisions(
            plan,
            [{"section_id": "cover", "change": "improve spacing",
              "rationale": "Better.", "addressed_observation": "x"}],
            _tiny_brief(),
        )
        self.assertTrue(any("vague" in m.lower() for m in msgs))

    def test_specific_change_is_applied(self):
        plan = _tiny_plan()
        new_plan, msgs = cp._apply_revisions(
            plan,
            [{"section_id": "manifesto", "change": "split into two columns at >=1024px with sticky index",
              "rationale": "Use the empty right half of the 1440px viewport.",
              "addressed_observation": "section occupies only left 50% of viewport."}],
            _tiny_brief(),
        )
        self.assertTrue(any(m.startswith("APPLIED") for m in msgs))
        # Component string gained the revision
        sec = next(s for s in new_plan["sections"] if s["id"] == "manifesto")
        self.assertIn("split into two columns", sec["component"])

    def test_apply_does_not_invent_source_brief_fields(self):
        plan = _tiny_plan()
        new_plan, msgs = cp._apply_revisions(
            plan,
            [{"section_id": "manifesto", "change": "swap to a 3-card grid at >=768px",
              "rationale": "Variety.",
              "addressed_observation": "All sections look the same."}],
            _tiny_brief(),
        )
        # source_brief_fields of 'manifesto' is still ['voice_and_tone.notes']
        sec = next(s for s in new_plan["sections"] if s["id"] == "manifesto")
        self.assertEqual(sec["source_brief_fields"], ["voice_and_tone.notes"])


class RubricDimensions(unittest.TestCase):
    def test_all_seven_dimensions_present(self):
        self.assertEqual(
            set(cp.RUBRIC_DIMENSIONS),
            {"visual_hierarchy", "use_of_space", "typographic_contrast",
             "focal_point", "brand_fit", "motion_restraint", "looks_templated"},
        )

    def test_looks_templated_is_listed_inverted(self):
        # We have a hint in the prompt. This test enforces the prompt mentions
        # the inversion so a future refactor doesn't silently flip it.
        self.assertIn("INVERTED", cp.RUBRIC_PROMPT)


class ScoreHelpers(unittest.TestCase):
    def test_safe_total_sums_when_total_missing(self):
        e = {"scores": {d: {"score": 7} for d in cp.RUBRIC_DIMENSIONS}}
        self.assertEqual(cp._safe_total(e), 7 * len(cp.RUBRIC_DIMENSIONS))

    def test_summary_md_marks_best_row(self):
        history = [
            {"iteration": 1, "scores": {d: {"score": 4} for d in cp.RUBRIC_DIMENSIONS},
             "applied": ["APPLIED foo"]},
            {"iteration": 2, "scores": {d: {"score": 6} for d in cp.RUBRIC_DIMENSIONS},
             "applied": ["APPLIED bar"]},
        ]
        md = cp._summary_md(history)
        self.assertIn("| 2 |", md)
        self.assertIn("**best**", md)

    def test_regression_note_appears_when_total_drops(self):
        history = [
            {"iteration": 1, "scores": {d: {"score": 7} for d in cp.RUBRIC_DIMENSIONS},
             "applied": []},
            {"iteration": 2, "scores": {d: {"score": 4} for d in cp.RUBRIC_DIMENSIONS},
             "applied": []},
        ]
        md = cp._summary_md(history)
        self.assertIn("regressed", md)


class ViewportParser(unittest.TestCase):
    def test_default_parse(self):
        v = cp._parse_viewports("1440x900,375x812")
        self.assertEqual(v, [(1440, 900), (375, 812)])

    def test_bad_format_raises(self):
        with self.assertRaises(ValueError):
            cp._parse_viewports("1440")


class RestoreBest(unittest.TestCase):
    def test_picks_highest_total_snapshot(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "iter-01.design-plan.json").write_text("{}")
            (d / "iter-02.design-plan.json").write_text("{}")
            history = [
                {"iteration": 1, "scores": {k: {"score": 4} for k in cp.RUBRIC_DIMENSIONS},
                 "plan_snapshot": "iter-01", "applied": []},
                {"iteration": 2, "scores": {k: {"score": 8} for k in cp.RUBRIC_DIMENSIONS},
                 "plan_snapshot": "iter-02", "applied": []},
            ]
            # Rewrite paths to absolute so _restore_best can stat them
            history[0]["plan_snapshot"] = str(d / "iter-01.design-plan.json")
            history[1]["plan_snapshot"] = str(d / "iter-02.design-plan.json")
            best = cp._restore_best(d, history)
            self.assertEqual(best, str(d / "iter-02.design-plan.json"))

    def test_returns_none_when_history_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(cp._restore_best(Path(td), []))


if __name__ == "__main__":
    unittest.main()