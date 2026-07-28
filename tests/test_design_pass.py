#!/usr/bin/env python3
"""Unit tests for design-pass invent-nothing source verification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills/web-designer/scripts"
sys.path.insert(0, str(SCRIPTS))

from design_pass import verify_source_fields  # noqa: E402


class SourceFieldVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = {
            "voice_and_tone": {"example_lines": ["Find your uniqueness."]},
            "service_facts": [{"name": "Branding Strategy"}],
            "testimonials": [],
        }

    def test_valid_plan_passes(self) -> None:
        plan = {
            "sections": [
                {
                    "id": "services",
                    "source_brief_fields": ["service_facts"],
                }
            ],
            "copy_blocks": [
                {
                    "section_id": "hero",
                    "source_brief_fields": ["voice_and_tone.example_lines"],
                }
            ],
            "skipped_sections": [],
        }

        self.assertEqual(verify_source_fields(plan, self.brief), [])

    def test_plan_citing_missing_field_is_rejected(self) -> None:
        plan = {
            "sections": [
                {
                    "id": "proof",
                    "source_brief_fields": ["testimonials.0.quote"],
                }
            ],
            "copy_blocks": [
                {
                    "section_id": "proof",
                    "source_brief_fields": ["imaginary_stats.conversion_rate"],
                }
            ],
            "skipped_sections": [],
        }

        violations = verify_source_fields(plan, self.brief)

        self.assertTrue(any("testimonials.0.quote" in item for item in violations))
        self.assertTrue(any("imaginary_stats.conversion_rate" in item for item in violations))


if __name__ == "__main__":
    unittest.main()
