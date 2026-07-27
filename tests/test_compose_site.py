#!/usr/bin/env python3
"""Regression tests for WCAG-safe brand text variants in compose_site.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "web-designer" / "scripts" / "compose_site.py"

_spec = importlib.util.spec_from_file_location("compose_site", SCRIPT)
assert _spec and _spec.loader
compose_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compose_site)


class AccessibleBrandTextTests(unittest.TestCase):
    def test_low_contrast_light_background_gets_darkened_variant(self) -> None:
        decision = compose_site.derive_accessible_text_variant("#3898ec", "#ffffff")

        self.assertEqual(decision["original_hex"], "#3898ec")
        self.assertNotEqual(decision["derived_hex"], "#3898ec")
        self.assertGreaterEqual(decision["derived_ratio"], 4.5)
        self.assertLess(decision["original_ratio"], 4.5)
        self.assertEqual(decision["direction"], "darken")

    def test_low_contrast_dark_background_gets_lightened_variant(self) -> None:
        decision = compose_site.derive_accessible_text_variant("#5d5d6d", "#0b0c0d")

        self.assertNotEqual(decision["derived_hex"], "#5d5d6d")
        self.assertGreaterEqual(decision["derived_ratio"], 4.5)
        self.assertLess(decision["original_ratio"], 4.5)
        self.assertEqual(decision["direction"], "lighten")

    def test_already_accessible_text_keeps_original_color(self) -> None:
        decision = compose_site.derive_accessible_text_variant("#0b0c0d", "#ffffff")

        self.assertEqual(decision["derived_hex"], "#0b0c0d")
        self.assertEqual(decision["original_ratio"], decision["derived_ratio"])
        self.assertEqual(decision["direction"], "unchanged")

    def test_resolve_contrast_records_primary_and_accent_text_tokens(self) -> None:
        contrast = compose_site.resolve_contrast(
            {
                "primary": "#efad2b",
                "accent": "#3898ec",
                "neutrals": ["#0b0c0d", "#ffffff"],
            },
            "Pedicel",
        )

        decisions = {item["name"]: item for item in contrast["brand_text_decisions"]}
        self.assertEqual(decisions["primary"]["token"], "--color-primary-text")
        self.assertEqual(decisions["accent"]["token"], "--color-accent-text")
        self.assertGreaterEqual(decisions["primary"]["derived_ratio"], 4.5)
        self.assertGreaterEqual(decisions["accent"]["derived_ratio"], 4.5)

    def test_stylesheet_uses_accessible_variants_only_for_brand_text(self) -> None:
        contrast = compose_site.resolve_contrast(
            {
                "primary": "#efad2b",
                "accent": "#3898ec",
                "neutrals": ["#0b0c0d", "#ffffff"],
            },
            "Pedicel",
        )
        css = compose_site.render_stylesheet(contrast)

        self.assertIn("a {\n  color: var(--color-accent-text);", css)
        self.assertIn(".hero-tagline {", css)
        self.assertIn("color: var(--color-primary-text);", css)
        self.assertIn("background: var(--color-accent);", css)
        self.assertNotIn("a {\n  color: var(--color-accent);", css)

    def test_accessible_tokens_are_added_to_output_tokens_css(self) -> None:
        contrast = compose_site.resolve_contrast(
            {
                "primary": "#efad2b",
                "accent": "#3898ec",
                "neutrals": ["#0b0c0d", "#ffffff"],
            },
            "Pedicel",
        )
        css = compose_site.add_accessible_text_tokens(
            ":root {\n  --color-accent: #3898ec;\n}\n", contrast
        )

        self.assertIn("--color-primary-text:", css)
        self.assertIn("--color-accent-text:", css)
        self.assertIn(contrast["brand_text_tokens"]["accent"]["hex"], css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
