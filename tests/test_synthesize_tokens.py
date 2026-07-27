#!/usr/bin/env python3
"""Behavior tests for the web-designer token synthesis CLI."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/web-designer/scripts/synthesize_tokens.py"
BRIEF = REPO / "reports/brand-smoke/brand-brief.json"
REFERENCE = REPO / "reports/validation/linear-app/tokens"


class SynthesizeTokensCliTests(unittest.TestCase):
    def run_cli(self, brief: Path, reference: Path, out: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--brand-brief",
                str(brief),
                "--reference-tokens",
                str(reference),
                "-o",
                str(out),
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_brand_identity_wins_and_reference_structure_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tokens-build"
            result = self.run_cli(BRIEF, REFERENCE, out)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(out))

            color = json.loads((out / "tokens/json/color.json").read_text())
            typography = json.loads((out / "tokens/json/typography.json").read_text())
            spacing = json.loads((out / "tokens/json/spacing.json").read_text())
            radius = json.loads((out / "tokens/json/radius.json").read_text())
            shadow = json.loads((out / "tokens/json/shadow.json").read_text())
            tailwind = json.loads((out / "tokens/dist/tailwind-tokens.json").read_text())
            css = (out / "tokens/dist/tokens.css").read_text()
            provenance = (out / "tokens/PROVENANCE.md").read_text()

            self.assertEqual(color["color"]["primary"]["value"], "#efad2b")
            # Brand brief marks Switzer as paid and recommends Inter (OFL) as the
            # safe substitution. The M6 paid-font substitution must rewrite the
            # live CSS family from Switzer to Inter.
            self.assertEqual(
                typography["typography"]["fontFamily"]["display"]["value"],
                "Inter",
            )
            self.assertEqual(
                typography["typography"]["fontFamily"]["body"]["value"],
                "Poppins",
            )
            self.assertEqual(
                typography["typography"]["fontFamily"]["mono"]["value"],
                "JetBrains Mono",
            )
            self.assertEqual(
                [token["value"] for token in spacing["spacing"].values()],
                ["8px"],
            )
            self.assertEqual(
                [token["value"] for token in radius["radius"].values()],
                ["0px", "4px", "6px", "8px", "24px", "9999px"],
            )
            self.assertTrue(shadow["shadow"])

            self.assertIn("--color-primary: #efad2b;", css)
            self.assertNotIn("#5e6ad2", css.lower())
            # The live CSS must use the OFL substitute (Inter), never the
            # brand-declared paid family (Switzer), as a primary face.
            self.assertIn(
                "--typography-font-family-display: Inter,",
                css,
            )
            self.assertNotIn("--typography-font-family-display: Switzer,", css)
            self.assertNotIn("Switzer,", css.replace("JetBrains", ""))
            self.assertEqual(tailwind["theme"]["extend"]["colors"]["primary"], "#efad2b")
            self.assertEqual(tailwind["theme"]["extend"]["fontFamily"]["display"], ["Inter"])
            # Sidecar records every substitution for the composer to consume.
            substitutions = json.loads(
                (out / "tokens/dist/font-substitutions.json").read_text()
            )
            by_role = substitutions["font_substitutions"]
            self.assertEqual(by_role["display"]["original_family"], "Switzer")
            self.assertEqual(by_role["display"]["primary"], "Inter")
            self.assertTrue(by_role["display"]["substituted"])
            # No live CSS request for the paid family.
            self.assertNotIn(
                "family=Switzer",
                json.dumps(substitutions["google_fonts_requested"]),
            )

            for payload in (color, typography, spacing, radius, shadow):
                self.assertEqual(payload["meta"]["schema_version"], "1.0")
                self.assertIn("generated_at", payload["meta"])
                self.assertEqual(payload["meta"]["evidence_basis"], "DOM+assets confirmed")

            self.assertIn("| Color | `brand-brief` |", provenance)
            self.assertIn("| Spacing | `reference-structure` |", provenance)
            self.assertIn("Switzer is by Indian Type Foundry", provenance)

    def test_missing_brand_scale_uses_reference_structure_and_records_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief_data = copy.deepcopy(json.loads(BRIEF.read_text()))
            del brief_data["typography_recommendation"]["scale_ratio"]
            del brief_data["typography_recommendation"]["scale_steps"]
            brief = root / "brand-without-scale.json"
            brief.write_text(json.dumps(brief_data), encoding="utf-8")
            out = root / "out"

            result = self.run_cli(brief, REFERENCE, out)

            self.assertEqual(result.returncode, 0, result.stderr)
            typography = json.loads((out / "tokens/json/typography.json").read_text())
            self.assertEqual(
                [token["value"] for token in typography["typography"]["fontSize"].values()],
                ["13px", "15px", "16px", "20px", "48px", "64px"],
            )
            self.assertEqual(typography["typography"]["scaleRatio"]["value"], 4.923)
            provenance = (out / "tokens/PROVENANCE.md").read_text()
            self.assertIn(
                "| Type scale | `reference-structure` | brand steps absent; used observed reference font sizes |",
                provenance,
            )
            self.assertIn(
                "| Type scale ratio | `reference-structure` | brand ratio absent; used typography.json scale_ratio |",
                provenance,
            )

    def test_invalid_brief_exits_nonzero_without_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = copy.deepcopy(json.loads(BRIEF.read_text()))
            invalid["palette_from_logo"]["primary"] = "#12345"
            brief = root / "invalid-brand-brief.json"
            brief.write_text(json.dumps(invalid), encoding="utf-8")
            out = root / "out"

            result = self.run_cli(brief, REFERENCE, out)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid brand brief", result.stderr.lower())
            self.assertFalse((out / "tokens").exists())


if __name__ == "__main__":
    unittest.main()
