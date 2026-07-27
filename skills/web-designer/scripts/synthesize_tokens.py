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


def render_css(
    *,
    meta: dict[str, Any],
    colors: dict[str, str],
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
    lines.append("")
    for role in ("display", "body", "mono"):
        lines.append(f"  --typography-font-family-{role}: {css_family(families[role])};")
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
) -> str:
    table = [
        "| Token group | Source | Detail |",
        "|---|---|---|",
    ]
    for group, source, detail in rows:
        table.append(
            f"| {markdown_cell(group)} | `{source}` | {markdown_cell(detail)} |"
        )
    return "\n".join(
        [
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
    )


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
        neutrals=neutrals,
        families=families,
        scale_ratio=ratio,
        type_steps=type_steps,
        spacing=spacing,
        radius=radius,
        shadows=shadows,
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
        ("Font families", "brand-brief", "typography_recommendation families"),
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
    )
    (out_dir / "tokens/PROVENANCE.md").write_text(provenance, encoding="utf-8")


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
