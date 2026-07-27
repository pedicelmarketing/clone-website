#!/usr/bin/env python3
"""Validate a brand-brief JSON document against brand_brief_schema.json.

Usage:
    validate_brand_brief.py <brand-brief.json> [--schema <path>]

Default schema path is `brand_brief_schema.json` next to this script.

Strategy:
  - If `jsonschema` is importable, use it (Draft 2020-12 validator). This is the
    full-fidelity path; system python3 has it installed.
  - Otherwise fall back to a built-in structural check that mirrors the most
    important constraints from the schema: required top-level keys present,
    primitive types match, every value declared as a hex color matches
    ^#[0-9a-fA-F]{6}$. This is a strict-but-narrow subset; it will NOT catch
    every schema violation, but it WILL catch every malformed response shape
    we have seen so far.

Output:
  - exit 0 + stdout "VALID <path>"        -> the document passes validation
  - exit 1 + stderr violation list        -> the document fails validation
  - exit 2 + stderr usage / I/O error     -> could not even attempt validation

We follow the same honesty conventions as the rest of the pipeline: state the
evidence basis, never claim a higher tier than the run supports. The fallback
path is reported as such on stderr so downstream consumers don't mistake it for
full Draft-2020-12 validation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# Hex pattern used by the schema. Keep it in sync with brand_brief_schema.json.
HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

# Required top-level keys (must mirror the schema's `required` list).
REQUIRED_TOP_LEVEL = (
    "schema_version",
    "project_slug",
    "fetched_at",
    "sources",
    "voice_and_tone",
    "palette_from_logo",
    "typography_recommendation",
    "real_photo_inventory",
    "service_facts",
    "social_highlights",
    "testimonials",
    "brand_donts",
    "limitations",
)


def _violation(msg: str) -> str:
    return f"  - {msg}"


def _jsonschema_validate(
    schema: dict[str, Any], document: Any
) -> tuple[bool, list[str]]:
    """Run the full Draft 2020-12 validator. Returns (ok, violations)."""
    try:
        import jsonschema  # type: ignore
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised only on the fallback path
        raise RuntimeError(f"jsonschema import failed: {exc!r}") from exc

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    if not errors:
        return True, []
    out: list[str] = []
    for err in errors:
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        out.append(_violation(f"{loc}: {err.message}"))
    return False, out


# JSON-pointer paths inside the brief that are documented to hold a hex color
# (must mirror the schema). We test the value at these paths against HEX_PATTERN.
HEX_PATHS: tuple[tuple[str, ...], ...] = (
    ("palette_from_logo", "primary"),
    ("palette_from_logo", "secondary"),
    ("palette_from_logo", "accent"),
    ("palette_from_logo", "neutrals"),
    # Any "*color*" or "*_hex" or top-level "hex" slot anywhere else:
    # covered by the recursive walker below.
)


def _looks_like_hex_attempt(s: str) -> bool:
    """Heuristic: a string that *looks like* someone tried to write a hex value but
    failed (so we should warn) — starts with '#' followed by 3-8 hex chars, OR is
    a 6-hex-char run with no leading '#'. We only flag these; otherwise we'd
    false-positive on prose strings ('notes', 'license_notes', etc.)."""
    if not isinstance(s, str):
        return False
    return bool(re.match(r"^#[0-9a-fA-F]{3,8}$", s)) or bool(re.match(r"^[0-9a-fA-F]{6}$", s))


def _walk_collect_hex_attempts(node: Any, path: str = "") -> Iterable[tuple[str, str]]:
    """Yield (path, value) for every string that looks like an attempted hex color
    but failed the schema's ^#[0-9a-fA-F]{6}$ pattern. Conservative — only flags
    strings that LOOK like a hex attempt, never arbitrary prose.

    Skips values under the known hex slots (HEX_PATHS) — those are already covered
    by the explicit hex-slot check and would otherwise produce duplicate
    violations for the same value.
    """
    # Collect the set of path prefixes to skip (hex slots).
    skip_prefixes: set[str] = {".".join(p) for p in HEX_PATHS}

    def _walk(n: Any, p: str) -> Iterable[tuple[str, str]]:
        if isinstance(n, dict):
            for k, v in n.items():
                child = f"{p}/{k}" if p else str(k)
                yield from _walk(v, child)
        elif isinstance(n, list):
            for i, v in enumerate(n):
                yield from _walk(v, f"{p}/{i}")
        elif isinstance(n, str):
            # Skip if this path is under a known hex slot (already covered).
            if any(p == pref or p.startswith(pref + "/") or p.startswith(pref + "[") for pref in skip_prefixes):
                return
            if _looks_like_hex_attempt(n) and not HEX_PATTERN.match(n):
                yield p, n
        return
    yield from _walk(node, "")


def _add_violation(violations: list[str], seen: set[tuple[str, str]], path: str, message: str) -> None:
    """Append a violation to *violations* unless (path, message) is already present
    in *seen*. Used to dedup overlapping reports from the hex-slot check and the
    hex-attempt walker when the same value fails both."""
    key = (path, message)
    if key in seen:
        return
    seen.add(key)
    violations.append(_violation(f"{path}: {message}"))


def _fallback_validate(schema: dict[str, Any], document: Any) -> tuple[bool, list[str], list[str]]:
    """Built-in structural check. Returns (ok, violations, info_notes)."""
    notes: list[str] = []
    notes.append(
        "jsonschema not importable; running built-in structural check "
        "(required-key + type + hex-pattern only)."
    )
    violations: list[str] = []

    if not isinstance(document, dict):
        violations.append(_violation(f"<root>: expected object, got {type(document).__name__}"))
        return False, violations, notes

    # Required top-level keys present.
    for key in REQUIRED_TOP_LEVEL:
        if key not in document:
            violations.append(_violation(f"<root>: missing required key '{key}'"))

    # Per-key type checks for the most load-bearing fields.
    type_checks: dict[str, type | tuple[type, ...]] = {
        "schema_version":               str,
        "project_slug":                 str,
        "fetched_at":                   str,
        "voice_and_tone":               dict,
        "palette_from_logo":            dict,
        "typography_recommendation":    dict,
        "real_photo_inventory":         list,
        "service_facts":                list,
        "social_highlights":            dict,
        "testimonials":                 list,
        "brand_donts":                  list,
        "limitations":                  list,
    }
    for key, expected in type_checks.items():
        if key in document and not isinstance(document[key], expected):
            violations.append(
                _violation(
                    f"{key}: expected {expected.__name__ if isinstance(expected, type) else expected}, "
                    f"got {type(document[key]).__name__}"
                )
            )

    # sources MUST be an object with the four known keys.
    sources = document.get("sources")
    if sources is not None:
        if not isinstance(sources, dict):
            violations.append(_violation(f"sources: expected object, got {type(sources).__name__}"))
        else:
            for sub in ("own_site", "linkedin", "instagram", "reference"):
                if sub not in sources:
                    violations.append(_violation(f"sources: missing key '{sub}'"))
                else:
                    val = sources[sub]
                    if val is not None and not isinstance(val, dict):
                        violations.append(
                            _violation(f"sources/{sub}: expected object or null, got {type(val).__name__}")
                        )

    # Hex-color check, two layers:
    #   (a) Every KNOWN hex slot (palette_from_logo.primary/secondary/accent/neutrals):
    #       value MUST match the pattern — any non-hex at these slots is a violation.
    #   (b) Recursive walker: flag any string ELSEWHERE that LOOKS like a hex
    #       attempt but failed the pattern (e.g. "#1F4D3F88" 8-char ARGB).
    seen_violations: set[tuple[str, str]] = set()
    for path_tuple in HEX_PATHS:
        node: Any = document
        ok = True
        for step in path_tuple:
            if isinstance(node, dict) and step in node:
                node = node[step]
            else:
                ok = False
                break
        if not ok:
            continue  # slot missing entirely; required-key check already covers it
        slot_path = "/".join(path_tuple)
        if isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str) and not HEX_PATTERN.match(v):
                    _add_violation(
                        violations,
                        seen_violations,
                        f"{slot_path}/{i}",
                        f"'{v}' is not a valid ^#[0-9a-fA-F]{{6}}$ hex color",
                    )
        elif isinstance(node, str) and not HEX_PATTERN.match(node):
            _add_violation(
                violations,
                seen_violations,
                slot_path,
                f"'{node}' is not a valid ^#[0-9a-fA-F]{{6}}$ hex color",
            )

    for path, value in _walk_collect_hex_attempts(document):
        _add_violation(
            violations,
            seen_violations,
            path,
            f"'{value}' looks like a hex color attempt but is not a valid ^#[0-9a-fA-F]{{6}}$",
        )

    return (len(violations) == 0), violations, notes


def _print_violations(label: str, violations: list[str], notes: list[str] | None = None) -> None:
    print(f"{label}:", file=sys.stderr)
    for v in violations:
        print(v, file=sys.stderr)
    if notes:
        for n in notes:
            print(f"  (note) {n}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a brand-brief JSON document against brand_brief_schema.json.",
    )
    parser.add_argument("brief", help="Path to the brand-brief JSON document.")
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).resolve().parent / "brand_brief_schema.json"),
        help="Path to the JSON Schema (default: brand_brief_schema.json next to this script).",
    )
    args = parser.parse_args(argv)

    brief_path = Path(args.brief)
    schema_path = Path(args.schema)

    if not brief_path.is_file():
        print(f"error: brand brief not found: {brief_path}", file=sys.stderr)
        return 2
    if not schema_path.is_file():
        print(f"error: schema not found: {schema_path}", file=sys.stderr)
        return 2

    try:
        document = json.loads(brief_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{brief_path}: invalid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: schema is not valid JSON ({schema_path}): {exc}", file=sys.stderr)
        return 2

    # Try the full validator first.
    try:
        ok, violations = _jsonschema_validate(schema, document)
    except Exception as exc:
        # jsonschema not available — run the built-in fallback.
        ok, violations, notes = _fallback_validate(schema, document)
        if not ok:
            _print_violations(f"INVALID {brief_path}", violations, notes)
            return 1
        # Fallback ok. Emit notes to stderr so downstream consumers know the
        # evidence basis. Treat as a successful validation; the path was
        # considered structurally sound for the keys we can check.
        for n in notes:
            print(f"  (note) {n}", file=sys.stderr)
        print(f"VALID {brief_path} (fallback checker; not full Draft-2020-12)")
        return 0

    if not ok:
        _print_violations(f"INVALID {brief_path}", violations)
        return 1

    print(f"VALID {brief_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())