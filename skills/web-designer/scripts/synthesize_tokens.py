#!/usr/bin/env python3
"""Fuse brand identity tokens with a reference site's structural token scales.

The validated brand brief is authoritative for colors and font families. Reference
outputs from extract_tokens.py contribute spacing, radius, shadow, and (only when the
brand omits it) type-scale structure. The canonical Style Dictionary JSON, direct CSS,
Tailwind bridge, and provenance report are written below the requested output directory.

Usage:
    synthesize_tokens.py --brand-brief reports/brand/brand-brief.json \
        --reference-tokens reports/reference/tokens -o build/
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

from validate_brand_brief import _fallback_validate, _jsonschema_validate
from _output_assertions import (
    OutputAssertionError,
    parse_css_variable_declarations,
    validate_css_font_family,
)


SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.0"
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_SPACING: list[int | float] = [4, 8, 12, 16, 24, 32, 48, 64]
DEFAULT_RADIUS: list[int | float] = [0, 4, 8, 12, 9999]
DEFAULT_SHADOWS = [
    {"level": 0, "value": "none"},
    {"level": 1, "value": "0 1px 2px rgba(0, 0, 0, 0.08)"},
    {"level": 2, "value": "0 4px 12px rgba(0, 0, 0, 0.12)"},
    {"level": 3, "value": "0 12px 32px rgba(0, 0, 0, 0.16)"},
]

# OFL-licensed substitutes used when a brief-declared family requires a paid
# commercial license and cannot be vendored. Picked by class (geometric humanist
# sans for display/body, monospaced slab for mono) so they ship with full
# fallback chains that degrade to system fonts. The mapping is hardcoded here
# rather than per-call so the substitution is deterministic and auditable; the
# detection of *which* family is paid lives in
# `_resolve_font_substitutions()` and is driven by the brief's `license_notes`,
# never by the literal family name string.
OFL_SUBSTITUTES: dict[str, str] = {
    "display": "Inter",
    "body": "Inter",
    "mono": "JetBrains Mono",
}

# CSS fallback chains appended after the primary family in every emitted token.
# A single-family declaration with no generic fallback is a real-world bug:
# when the primary face fails to load the browser falls back to a Times-like
# default that visually breaks the page. Always include system fonts.
FALLBACK_CHAINS: dict[str, str] = {
    "display": 'system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif',
    "body": 'system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif',
    "mono": 'ui-monospace, "SFMono-Regular", "Menlo", "Consolas", monospace',
}

# Phrases in `typography_recommendation.license_notes` that flag a family as
# restricted/paid. Matched case-insensitively as substrings of the license_notes
# block. Generic on purpose — driven by wording the brand brief already uses,
# never by hardcoded font names.
PAID_LICENSE_PHRASES: tuple[str, ...] = (
    "paid license",
    "commercial license",
    "do not vendor",
    "not licensed",
    "requires a paid",
    "requires a commercial",
    "is not free for commercial",
    "free for personal use",
    "personal use only",
    "not free for commercial",
)


class InputError(ValueError):
    """An input could not support honest token synthesis."""


def load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise InputError(f"{label} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"{label} is not valid JSON ({path}): {exc}") from exc
    except OSError as exc:
        raise InputError(f"could not read {label} ({path}): {exc}") from exc


def validate_brief(brief_path: Path, schema_path: Path) -> dict[str, Any]:
    """Validate with the shared brand-brief validator, then check synthesis fields."""
    document = load_json(brief_path, "brand brief")
    schema = load_json(schema_path, "brand brief schema")

    # The synthesis contract explicitly permits scale_ratio / scale_steps to be
    # absent so reference structure can fill them. Validate every other brief field
    # against the shared schema by removing only those two `required` entries from a
    # private schema copy; present values still have to satisfy their schema types.
    validation_schema = copy.deepcopy(schema)
    typography_schema = (
        validation_schema.get("$defs", {}).get("typography_recommendation", {})
        if isinstance(validation_schema, dict)
        else {}
    )
    required = typography_schema.get("required")
    if isinstance(required, list):
        typography_schema["required"] = [
            field for field in required if field not in {"scale_ratio", "scale_steps"}
        ]

    try:
        ok, violations = _jsonschema_validate(validation_schema, document)
    except Exception:
        ok, violations, _notes = _fallback_validate(validation_schema, document)
    if not ok:
        detail = "; ".join(item.strip().lstrip("- ") for item in violations)
        raise InputError(f"invalid brand brief {brief_path}: {detail}")
    if not isinstance(document, dict):
        raise InputError(f"invalid brand brief {brief_path}: root must be an object")

    # These checks also protect the narrow built-in validator path when jsonschema is
    # unavailable. Missing brand colors are fatal: reference colors are never a fallback.
    palette = document.get("palette_from_logo")
    if not isinstance(palette, dict):
        raise InputError(f"invalid brand brief {brief_path}: palette_from_logo must be an object")
    for field in ("primary", "secondary", "accent"):
        value = palette.get(field)
        if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
            raise InputError(
                f"invalid brand brief {brief_path}: palette_from_logo/{field} "
                "must be a 6-digit hex color"
            )
    neutrals = palette.get("neutrals")
    if not isinstance(neutrals, list) or not neutrals:
        raise InputError(
            f"invalid brand brief {brief_path}: palette_from_logo/neutrals "
            "must be a non-empty array"
        )
    for index, value in enumerate(neutrals):
        if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
            raise InputError(
                f"invalid brand brief {brief_path}: palette_from_logo/neutrals/{index} "
                "must be a 6-digit hex color"
            )

    typography = document.get("typography_recommendation")
    if not isinstance(typography, dict):
        raise InputError(
            f"invalid brand brief {brief_path}: typography_recommendation must be an object"
        )
    for field in ("display_family", "body_family", "mono_family", "license_notes"):
        value = typography.get(field)
        if not isinstance(value, str) or not value.strip():
            raise InputError(
                f"invalid brand brief {brief_path}: typography_recommendation/{field} "
                "must be a non-empty string"
            )
    ratio = typography.get("scale_ratio")
    if ratio is not None and not _valid_ratio(ratio):
        raise InputError(
            f"invalid brand brief {brief_path}: typography_recommendation/scale_ratio "
            "must be greater than 1 and at most 2"
        )
    steps = typography.get("scale_steps")
    if steps is not None and (
        not isinstance(steps, list)
        or len(steps) < 2
        or any(not _finite_number(value) or value <= 0 for value in steps)
    ):
        raise InputError(
            f"invalid brand brief {brief_path}: typography_recommendation/scale_steps "
            "must contain at least two positive numbers"
        )
    return document


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_ratio(value: Any) -> bool:
    return _finite_number(value) and 1 < value <= 2


def load_reference_file(reference_dir: Path, name: str) -> dict[str, Any] | None:
    path = reference_dir / f"{name}.json"
    if not path.exists():
        return None
    payload = load_json(path, f"reference {name} tokens")
    if not isinstance(payload, dict):
        raise InputError(f"reference {name} tokens must be a JSON object: {path}")
    return payload


def numeric_scale(payload: dict[str, Any] | None, field: str = "scale") -> list[int | float]:
    if not payload or not isinstance(payload.get(field), list):
        return []
    result: list[int | float] = []
    for value in payload[field]:
        if _finite_number(value) and value >= 0 and value not in result:
            result.append(value)
    return result


def typography_scale_from_reference(payload: dict[str, Any] | None) -> list[int | float]:
    if not payload or not isinstance(payload.get("scale"), list):
        return []
    values: set[int | float] = set()
    for item in payload["scale"]:
        if not isinstance(item, dict):
            continue
        size = item.get("size_px")
        if isinstance(size, (int, float)) and not isinstance(size, bool) and math.isfinite(size) and size > 0:
            values.add(size)
    return sorted(values)


def shadow_scale(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload or not isinstance(payload.get("elevations"), list):
        return []
    result = []
    for index, item in enumerate(payload["elevations"]):
        if not isinstance(item, dict) or not isinstance(item.get("value"), str):
            continue
        value = item["value"].strip()
        if not value:
            continue
        level = item.get("level", index)
        if not isinstance(level, (str, int)):
            level = index
        result.append({"level": level, "value": value})
    return result


def number_label(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).replace(".", "_")


def dimension_tokens(values: list[int | float], *, full_radius: bool = False) -> dict[str, Any]:
    tokens: dict[str, Any] = {}
    for value in values:
        key = "full" if full_radius and value >= 9999 else number_label(value)
        if key in tokens:
            key = f"{key}_{len(tokens)}"
        tokens[key] = {"value": f"{value:g}px"}
    return tokens


def make_meta(
    *,
    generated_at: str,
    project_slug: str,
    brief_path: Path,
    reference_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "generated_at": generated_at,
        "evidence_basis": "DOM+assets confirmed",
        "project_slug": project_slug,
        "brand_brief": str(brief_path.resolve()),
        "reference_tokens": str(reference_dir.resolve()),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def css_family(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance. Used to pick fg/bg by measurement, not position."""
    parts = []
    for channel in _hex_to_rgb(hex_color):
        c = channel / 255
        parts.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    a, b = _relative_luminance(fg_hex), _relative_luminance(bg_hex)
    hi, lo = max(a, b), min(a, b)
    return round((hi + 0.05) / (lo + 0.05), 2)


def css_family_chain(primary: str, role: str) -> str:
    """Return a CSS `font-family` declaration value with a real fallback chain.

    A bare family name (e.g. `"Inter"`) is a bug because if the family fails
    to load the browser picks an arbitrary serif default. Every emitted token
    includes the role-appropriate system-font chain so the page degrades
    gracefully. The returned value is the unquoted CSS chain itself
    (e.g. `Inter, system-ui, -apple-system, "Segoe UI", Arial, sans-serif`),
    suitable for direct interpolation into a `--typography-font-family-*: …;`
    declaration.

    Individual family names are quoted only when they contain characters that
    aren't valid in an unquoted CSS identifier (spaces, digits-leading, dots,
    etc.). Wrapping the whole chain in `json.dumps` would produce one bogus
    quoted family name and break `document.fonts.check(...)` lookups.
    """

    def _quote(name: str) -> str:
        # CSS unquoted family names are limited to identifier-like chars.
        # Anything else (spaces, digits-leading, dots, hyphens at start, …) must
        # be wrapped in double quotes; inner double quotes are escaped.
        if re.fullmatch(r"[A-Za-z0-9_-]+", name):
            return name
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    chain = FALLBACK_CHAINS.get(role, FALLBACK_CHAINS["body"])
    return f"{_quote(primary)}, {chain}"


def _license_notes_flag_paid(license_notes: str) -> bool:
    """Generic paid-license detection from the brand brief's license_notes.

    Driven by wording, not by family name, so it generalizes to any brand whose
    brief declares restricted fonts. Returns True if the license_notes block
    mentions at least one of the restricted-licensing phrases.
    """
    text = (license_notes or "").lower()
    return any(phrase in text for phrase in PAID_LICENSE_PHRASES)


def _family_explicitly_ofl(license_notes: str, family: str) -> bool:
    """Return True if the brand brief's license_notes explicitly names `family`
    as OFL / safe-to-self-host as the *subject* of its clause.

    Patterns accepted as the OFL declaration for `family`:
        "<family> is OFL"
        "<family> is released under ..."
        "<family> is safe to self-host"
        "<family> ... released under the SIL Open Font License"
        "<family> ... is open font license"

    The detection is conservative: it requires the OFL phrase to be in the
    same clause as the family name, AND the family name to appear before the
    OFL phrase (so a sentence like
        "Switzer (paid) retained ... otherwise substitute with Inter (OFL)"
    does NOT mark Switzer as OFL — only Inter qualifies).

    If a sentence mentions multiple families, only the family that appears
    before the OFL marker is treated as OFL.
    """
    text = (license_notes or "")
    if not family:
        return False
    name = family.lower()
    ofl_markers = (
        " is ofl",
        " was ofl",
        " is released under",
        " was released under",
        " is safe to self-host",
        " is open font license",
        " is released under the sil open font license",
        " is licensed under the open font license",
        " is licensed under the sil open font license",
    )
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sl = sentence.lower()
        if name not in sl:
            continue
        for marker in ofl_markers:
            index = sl.find(marker)
            if index == -1:
                continue
            # The family name must appear strictly before the OFL marker so
            # sentences of the form "X (paid) ... substitute with Y (OFL)"
            # mark Y as OFL but leave X alone.
            if sl.find(name) < index:
                return True
    return False


def _resolve_font_substitutions(
    *,
    brand_type: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Apply OFL-substitution rules to every family role.

    Returns a dict keyed by role ("display", "body", "mono") with each entry
    shaped as::

        {"primary": "Inter",
         "original_family": "Switzer",
         "substituted": True,
         "reason": "license_notes flags paid/commercial use"}

    When the brief's license_notes flag restricted licensing, the brand-declared
    family is substituted with the OFL substitute UNLESS the brief explicitly
    calls the family OFL / safe-to-self-host, in which case the brand family is
    kept verbatim. When the notes do NOT flag restricted licensing, every
    brand-declared family is used unchanged and `substituted` is False.
    """
    license_notes = str(brand_type.get("license_notes", ""))
    notes_flag_paid = _license_notes_flag_paid(license_notes)
    roles = ("display", "body", "mono")
    field_names = {"display": "display_family", "body": "body_family", "mono": "mono_family"}

    resolved: dict[str, dict[str, Any]] = {}
    for role in roles:
        original = str(brand_type.get(field_names[role], "")).strip()
        if not notes_flag_paid:
            resolved[role] = {
                "primary": original,
                "original_family": original,
                "substituted": False,
                "reason": "license_notes clear; brand family used as-is",
            }
            continue

        if _family_explicitly_ofl(license_notes, original):
            resolved[role] = {
                "primary": original,
                "original_family": original,
                "substituted": False,
                "reason": (
                    f"license_notes flag restricted licensing, but the brief "
                    f"explicitly names '{original}' as OFL; brand family kept"
                ),
            }
            continue

        substitute = OFL_SUBSTITUTES.get(role, original)
        resolved[role] = {
            "primary": substitute,
            "original_family": original,
            "substituted": substitute != original,
            "reason": (
                f"license_notes flagged restricted licensing; "
                f"substituted '{original}' with OFL substitute '{substitute}'"
            ),
        }
    return resolved


def google_fonts_family_args(role: str, primary: str) -> str | None:
    """Return the `family=` URL argument for a Google Fonts request, or None
    if the family is not on the Google Fonts catalog and cannot be self-hosted
    here. Inter / Poppins / JetBrains Mono are the three families this project
    ships with webfont links for; anything else gets no link and is expected
    to arrive via the fallback chain (system fonts) — that path is supported
    by `_resolve_font_substitutions` mapping the two restricted candidates
    onto Inter so this function never emits a request for a paid face.
    """
    catalog = {
        "Inter": "Inter:wght@400;500;600;700",
        "Poppins": "Poppins:wght@400;500;600;700",
        "JetBrains Mono": "JetBrains+Mono:wght@400;600",
    }
    return catalog.get(primary)


def render_css(
    *,
    meta: dict[str, Any],
    colors: dict[str, str],
    ground: str = "light",
    neutrals: list[str],
    families: dict[str, str],
    scale_ratio: int | float,
    type_steps: list[int | float],
    spacing: list[int | float],
    radius: list[int | float],
    shadows: list[dict[str, Any]],
) -> str:
    lines = [
        "/**",
        " * Canonical design tokens.",
        f" * Generated by synthesize_tokens.py at {meta['generated_at']}.",
        " * See ../PROVENANCE.md before redistributing font assets.",
        " */",
        ":root {",
    ]
    for name in ("primary", "secondary", "accent"):
        lines.append(f"  --color-{name}: {colors[name]};")
    for index, value in enumerate(neutrals):
        lines.append(f"  --color-neutral-{index}: {value};")

    # SEMANTIC foreground/background, chosen by MEASURED LUMINANCE.
    #
    # Consumers previously assumed --color-neutral-0 was the darkest neutral and
    # used it as body text. That assumption is not safe: the brand brief's
    # neutrals[] array has no guaranteed ordering. One brand's neutral-0 was
    # #0b0c0d (near-black, fine); another's was #FBF7E9 (near-white cream),
    # which rendered headings at 1.07:1 on white — effectively invisible.
    #
    # So derive them instead of trusting position, and guarantee WCAG AA. If the
    # brand's own neutrals cannot reach 4.5:1, fall back to near-black/near-white
    # and record it, rather than shipping illegible text in the brand's name.
    _lum_sorted = sorted(neutrals, key=_relative_luminance)
    fg, bg = _lum_sorted[0], _lum_sorted[-1]
    fg_note = "darkest and lightest brand neutrals"

    # GROUND. Luminance tells us which neutral is darkest, not which one the
    # brand sits on. A brand whose identity is gold on dark green is a dark-
    # ground brand, and forcing it light has real consequences: its gold measures
    # 2.22:1 as text on cream but 4.94:1 on the dark green, and the opacity
    # ladder bottoms out at /70 instead of /55. Defaults to light so no existing
    # brand changes.
    if (ground or "light").lower() == "dark":
        fg, bg = bg, fg
        fg_note = "brand declares a DARK ground; lightest neutral is the ink"
    if _contrast_ratio(fg, bg) < 4.5:
        fg, bg = "#111111", "#ffffff"
        fg_note = ("brand neutrals could not reach 4.5:1 "
                   f"(best was {_contrast_ratio(_lum_sorted[0], _lum_sorted[-1])}:1); "
                   "substituted near-black on white")
    lines.append(f"  --color-fg: {fg};")
    lines.append(f"  --color-bg: {bg};")
    lines.append(f"  /* fg/bg chosen by luminance ({fg_note}); "
                 f"contrast {_contrast_ratio(fg, bg)}:1 */")

    # TEXT ON A FILLED BRAND SURFACE — same derivation, same reason.
    #
    # `--primary-foreground` was hardwired to --color-neutral-0, i.e. the exact
    # positional assumption fixed above, one layer up. On a brand whose
    # neutral-0 is a cream (#FBF7E9) and whose primary is a bright yellow
    # (#FFC517), every filled button rendered cream-on-yellow at 1.47:1 —
    # unreadable, and brand-dependent, so it passed on the first brand tested
    # and failed on the second.
    #
    # Pick whichever of the derived fg/bg contrasts better against the fill, and
    # fall back to black/white if neither brand colour reaches AA.
    for _role, _fill in (("primary", colors.get("primary")),
                         ("accent", colors.get("accent"))):
        if not _fill:
            continue
        _best = max((fg, bg), key=lambda c: _contrast_ratio(c, _fill))
        _ratio = _contrast_ratio(_best, _fill)
        if _ratio < 4.5:
            _best = max(("#111111", "#ffffff"), key=lambda c: _contrast_ratio(c, _fill))
            _ratio = _contrast_ratio(_best, _fill)
        lines.append(f"  --color-{_role}-text: {_best};")
        lines.append(f"  /* text on --color-{_role} ({_fill}); "
                     f"contrast {_ratio}:1 */")
    lines.append("")
    # Emit each font-family token as a real fallback chain, not a bare name.
    # A single-family declaration breaks silently when the primary face fails
    # to load, so the role-specific system-font chain is appended here.
    for role in ("display", "body", "mono"):
        lines.append(
            f"  --typography-font-family-{role}: {css_family_chain(families[role], role)};"
        )
    lines.append(f"  --typography-scale-ratio: {scale_ratio:g};")
    for index, value in enumerate(type_steps):
        lines.append(f"  --typography-font-size-{index}: {value:g}px;")
    lines.append("")
    for value in spacing:
        lines.append(f"  --spacing-{number_label(value)}: {value:g}px;")
    lines.append("")
    for value in radius:
        label = "full" if value >= 9999 else number_label(value)
        lines.append(f"  --radius-{label}: {value:g}px;")
    lines.append("")
    for index, item in enumerate(shadows):
        label = str(item.get("level", index)).replace(" ", "-").lower()
        lines.append(f"  --shadow-{label}: {item['value']};")
    lines.extend(["}", ""])
    return "\n".join(lines)


def markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_provenance(
    *,
    generated_at: str,
    project_slug: str,
    brief_path: Path,
    reference_dir: Path,
    rows: list[tuple[str, str, str]],
    license_notes: str,
    font_substitutions: dict[str, dict[str, Any]] | None = None,
) -> str:
    table = [
        "| Token group | Source | Detail |",
        "|---|---|---|",
    ]
    for group, source, detail in rows:
        table.append(
            f"| {markdown_cell(group)} | `{source}` | {markdown_cell(detail)} |"
        )
    parts = [
        "# Token provenance",
        "",
        f"- Project: `{project_slug}`",
        f"- Generated at: `{generated_at}`",
        f"- Brand brief: `{brief_path.resolve()}` (schema validated before use)",
        f"- Reference tokens: `{reference_dir.resolve()}`",
        "- Evidence basis: `DOM+assets confirmed`",
        "",
        "The reference color inventory was intentionally not consumed. Brand colors and",
        "font families are authoritative; the reference contributes structure only.",
        "",
        *table,
        "",
        "## Font license notes (carried over verbatim from brand-brief)",
        "",
        license_notes.strip(),
        "",
        "Review these notes before vendoring or redistributing any font files. Paid or",
        "restricted fonts remain external until the project has the required license.",
        "",
    ]
    if font_substitutions:
        any_substituted = any(
            entry.get("substituted") for entry in font_substitutions.values()
        )
        if any_substituted:
            parts.extend(
                [
                    "## Font substitutions (paid -> OFL)",
                    "",
                    "The brand brief's `license_notes` flag restricted licensing, so every",
                    "role with a paid/commercial family is emitted as an OFL-licensed",
                    "substitute. The original family is preserved here for provenance; it",
                    "never appears as a live CSS `font-family` value, and no Google Fonts",
                    "request is emitted for it.",
                    "",
                    "| Role | Original (paid) | Substitute (OFL) | Reason |",
                    "|---|---|---|---|",
                ]
            )
            for role in ("display", "body", "mono"):
                entry = font_substitutions.get(role, {})
                original = markdown_cell(entry.get("original_family", ""))
                substitute = markdown_cell(entry.get("primary", ""))
                reason = markdown_cell(entry.get("reason", ""))
                parts.append(f"| {role} | {original} | {substitute} | {reason} |")
            parts.append("")
    parts.append("")
    return "\n".join(parts)


def synthesize(
    *,
    brief: dict[str, Any],
    brief_path: Path,
    reference_dir: Path,
    out_dir: Path,
    project_slug: str,
) -> None:
    palette = brief["palette_from_logo"]
    brand_type = brief["typography_recommendation"]

    reference_spacing = load_reference_file(reference_dir, "spacing")
    reference_radius = load_reference_file(reference_dir, "radius")
    reference_shadow = load_reference_file(reference_dir, "shadow")
    reference_type = load_reference_file(reference_dir, "typography")

    spacing = numeric_scale(reference_spacing)
    spacing_source = "reference-structure"
    spacing_detail = "spacing.json scale"
    if not spacing:
        spacing = DEFAULT_SPACING.copy()
        spacing_source = "computed-default"
        spacing_detail = "reference spacing scale unavailable or empty"

    radius = numeric_scale(reference_radius)
    radius_source = "reference-structure"
    radius_detail = "radius.json scale"
    if not radius:
        radius = DEFAULT_RADIUS.copy()
        radius_source = "computed-default"
        radius_detail = "reference radius scale unavailable or empty"

    shadows = shadow_scale(reference_shadow)
    shadow_source = "reference-structure"
    shadow_detail = "shadow.json elevations"
    if not shadows:
        shadows = [dict(item) for item in DEFAULT_SHADOWS]
        shadow_source = "computed-default"
        shadow_detail = "reference shadow elevations unavailable or empty"

    families = {
        "display": brand_type["display_family"].strip(),
        "body": brand_type["body_family"].strip(),
        "mono": brand_type["mono_family"].strip(),
    }

    # Apply paid-license substitution driven by the brief's `license_notes`.
    # This is the only place paid fonts are rewritten to OFL substitutes;
    # render_css() then turns each substitute into a real CSS fallback chain.
    # Every original brand-declared family is preserved in `font_substitutions`
    # for PROVENANCE.md / BUILD-REPORT.md provenance and for the composer to
    # read so the page never embeds a request for a paid family.
    font_substitutions = _resolve_font_substitutions(brand_type=brand_type)
    families = {role: entry["primary"] for role, entry in font_substitutions.items()}
    substituted_families = [
        entry["original_family"]
        for entry in font_substitutions.values()
        if entry["substituted"]
    ]

    ratio_value = brand_type.get("scale_ratio")
    ratio_source = "brand-brief"
    ratio_detail = "typography_recommendation.scale_ratio"
    if _valid_ratio(ratio_value):
        ratio: float = float(ratio_value)
    else:
        reference_ratio = reference_type.get("scale_ratio") if reference_type else None
        if (
            isinstance(reference_ratio, (int, float))
            and not isinstance(reference_ratio, bool)
            and math.isfinite(reference_ratio)
            and reference_ratio > 1
        ):
            ratio = float(reference_ratio)
            ratio_source = "reference-structure"
            ratio_detail = "brand ratio absent; used typography.json scale_ratio"
        else:
            ratio = 1.25
            ratio_source = "computed-default"
            ratio_detail = "brand and reference ratios unavailable or unusable"

    type_steps = brand_type.get("scale_steps")
    type_scale_source = "brand-brief"
    type_scale_detail = "typography_recommendation.scale_steps"
    if not isinstance(type_steps, list) or len(type_steps) < 2:
        type_steps = typography_scale_from_reference(reference_type)
        type_scale_source = "reference-structure"
        type_scale_detail = "brand steps absent; used observed reference font sizes"
        if len(type_steps) < 2:
            type_steps = [12, 14, 16, 20, 24, 32, 48, 64]
            type_scale_source = "computed-default"
            type_scale_detail = "brand and reference type steps unavailable"

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta = make_meta(
        generated_at=generated_at,
        project_slug=project_slug,
        brief_path=brief_path,
        reference_dir=reference_dir,
    )

    colors = {
        "primary": palette["primary"],
        "secondary": palette["secondary"],
        "accent": palette["accent"],
    }
    neutrals = list(palette["neutrals"])

    color_payload = {
        "meta": meta,
        "color": {
            **{name: {"value": value} for name, value in colors.items()},
            "neutral": {
                str(index): {"value": value} for index, value in enumerate(neutrals)
            },
        },
    }
    typography_payload = {
        "meta": meta,
        "typography": {
            "fontFamily": {
                role: {"value": family} for role, family in families.items()
            },
            "scaleRatio": {"value": ratio},
            "fontSize": {
                str(index): {"value": f"{value:g}px"}
                for index, value in enumerate(type_steps)
            },
        },
    }
    spacing_payload = {"meta": meta, "spacing": dimension_tokens(spacing)}
    radius_payload = {
        "meta": meta,
        "radius": dimension_tokens(radius, full_radius=True),
    }
    shadow_payload = {
        "meta": meta,
        "shadow": {
            str(item.get("level", index)): {"value": item["value"]}
            for index, item in enumerate(shadows)
        },
    }

    json_dir = out_dir / "tokens/json"
    dist_dir = out_dir / "tokens/dist"
    # Persist a Style-Dictionary-friendly sibling that strips the per-file `meta`
    # block. The per-file meta is still emitted to the standard layout for
    # downstream JSON consumers; the `sd/` directory is what the
    # style-dictionary.config.cjs in assets/ consumes (and avoids the
    # "Property Value Collisions" warning v3 emits when every source has an
    # identical `meta` block).
    write_json(json_dir / "color.json", color_payload)
    write_json(json_dir / "typography.json", typography_payload)
    write_json(json_dir / "spacing.json", spacing_payload)
    write_json(json_dir / "radius.json", radius_payload)
    write_json(json_dir / "shadow.json", shadow_payload)
    write_json(json_dir / "sd/color.json", {"color": color_payload["color"]})
    write_json(
        json_dir / "sd/typography.json",
        {"typography": typography_payload["typography"]},
    )
    write_json(json_dir / "sd/spacing.json", {"spacing": spacing_payload["spacing"]})
    write_json(json_dir / "sd/radius.json", {"radius": radius_payload["radius"]})
    write_json(json_dir / "sd/shadow.json", {"shadow": shadow_payload["shadow"]})

    css = render_css(
        meta=meta,
        colors=colors,
        # The brand declares which ground it sits on; luminance only tells us
        # which neutral is darkest, not which one the identity is built on.
        ground=(brief["palette_from_logo"].get("ground") or "light"),
        neutrals=neutrals,
        families=families,
        scale_ratio=ratio,
        type_steps=type_steps,
        spacing=spacing,
        radius=radius,
        shadows=shadows,
    )

    # ---- Output self-assertion (M6 self-verification) --------------------
    # The CSS we are about to write to disk is the canonical token
    # contract for every downstream renderer (composer, validation).
    # Before persisting it, every emitted font-family token MUST be a
    # valid CSS stack: >=2 comma-separated families, no whole-value
    # quoting, no character-splitting, and no paid family used as a
    # primary face. A single failure here used to ship (e.g. M3
    # char-split `Inter, s, y, s, t, e, m` regression); we now refuse.
    declarations = parse_css_variable_declarations(css)
    assertion_failures: list[str] = []
    for var_name, value in declarations.items():
        if "font-family" not in var_name:
            continue
        for err in validate_css_font_family(value):
            assertion_failures.append(f"{var_name}: {err}")
    if assertion_failures:
        for failure in assertion_failures:
            print(f"synthesize_tokens: OUTPUT ASSERTION FAILED: {failure}",
                  file=sys.stderr)
        raise OutputAssertionError(
            "synthesize_tokens refused to write tokens.css: "
            f"{len(assertion_failures)} font-family invariant violation(s). "
            f"See {out_dir / 'tokens/dist/tokens.css'} (NOT written). "
            "Inspect _output_assertions.validate_css_font_family for the "
            "exact rule and the offending value."
        )

    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "tokens.css").write_text(css, encoding="utf-8")

    tailwind = {
        "meta": meta,
        "theme": {
            "extend": {
                "colors": {
                    **colors,
                    "neutral": {
                        str(index): value for index, value in enumerate(neutrals)
                    },
                },
                "fontFamily": {role: [family] for role, family in families.items()},
                "spacing": {
                    number_label(value): f"{value:g}px" for value in spacing
                },
                "borderRadius": {
                    ("full" if value >= 9999 else number_label(value)): f"{value:g}px"
                    for value in radius
                },
                "boxShadow": {
                    str(item.get("level", index)): item["value"]
                    for index, item in enumerate(shadows)
                },
            }
        },
    }
    write_json(dist_dir / "tailwind-tokens.json", tailwind)

    provenance_rows = [
        ("Color", "brand-brief", "palette_from_logo; reference colors ignored"),
        (
            "Font families",
            "brand-brief + substitution",
            "typography_recommendation families, paid->OFL substitution applied",
        ),
        ("Type scale", type_scale_source, type_scale_detail),
        ("Type scale ratio", ratio_source, ratio_detail),
        ("Spacing", spacing_source, spacing_detail),
        ("Radius", radius_source, radius_detail),
        ("Shadow", shadow_source, shadow_detail),
    ]
    provenance = render_provenance(
        generated_at=generated_at,
        project_slug=project_slug,
        brief_path=brief_path,
        reference_dir=reference_dir,
        rows=provenance_rows,
        license_notes=brand_type["license_notes"],
        font_substitutions=font_substitutions,
    )
    (out_dir / "tokens/PROVENANCE.md").write_text(provenance, encoding="utf-8")

    # Sidecar: machine-readable record of every font-family substitution so the
    # composer can read it without re-parsing tokens.css. Authoritative for
    # "what families are emitted, and which were swapped for licensing".
    substitutions_sidecar = {
        "meta": meta,
        "font_substitutions": font_substitutions,
        "google_fonts_requested": [
            {
                "role": role,
                "primary": entry["primary"],
                "family_arg": google_fonts_family_args(role, entry["primary"]),
            }
            for role, entry in font_substitutions.items()
            if google_fonts_family_args(role, entry["primary"])
        ],
    }
    write_json(dist_dir / "font-substitutions.json", substitutions_sidecar)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fuse brand identity with reference structural token scales."
    )
    parser.add_argument("--brand-brief", required=True, help="Validated brand-brief.json path.")
    parser.add_argument(
        "--reference-tokens",
        required=True,
        help="Directory containing extract_tokens.py JSON outputs.",
    )
    parser.add_argument("-o", "--out", required=True, help="Output directory.")
    parser.add_argument(
        "--project-slug",
        help="Override project_slug from the brand brief for generated metadata.",
    )
    args = parser.parse_args(argv)

    brief_path = Path(args.brand_brief)
    reference_dir = Path(args.reference_tokens)
    out_dir = Path(args.out)
    schema_path = Path(__file__).resolve().with_name("brand_brief_schema.json")

    try:
        if not reference_dir.is_dir():
            raise InputError(f"reference tokens directory not found: {reference_dir}")
        brief = validate_brief(brief_path, schema_path)
        project_slug = args.project_slug or brief["project_slug"]
        if not isinstance(project_slug, str) or not project_slug.strip():
            raise InputError("project slug must be a non-empty string")
        synthesize(
            brief=brief,
            brief_path=brief_path,
            reference_dir=reference_dir,
            out_dir=out_dir,
            project_slug=project_slug.strip(),
        )
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OutputAssertionError as exc:
        # Self-verification caught a bad output before it was written.
        # The diagnostic was already printed above the raise; the exit
        # code is non-zero so verify.sh and CI fail loudly.
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except OSError as exc:
        print(f"error: could not write token outputs: {exc}", file=sys.stderr)
        return 3
    except (KeyError, TypeError, ValueError) as exc:
        print(f"error: token synthesis failed on invalid input: {exc}", file=sys.stderr)
        return 2

    print(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
