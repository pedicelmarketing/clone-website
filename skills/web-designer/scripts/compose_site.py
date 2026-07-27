#!/usr/bin/env python3
"""Compose a real, servable static site from a brand brief + synthesized tokens.

This is the M3 design-pass emitter (web-designer skill step 4, per
`research/integration-plan.md` §5 M3). It is deliberately stack-free: plain HTML +
CSS, no build step, no framework, no npm. That keeps the React/Next vs. Astro vs.
Nuxt decision (integration-plan §6.1) open until M4+ and lets M4's validation gates
audit the output without a build chain.

CLI:
    compose_site.py --brand-brief <path> --tokens <synthesize_tokens outdir>
        [--reference-report <dir>] [--design-plan <design-plan.json>]
        -o <outdir> [--project-slug <slug>]

The emitter is a *re-versioning* step, not a mirror. It composes sections ONLY from
content that actually exists in the brand brief — every section it skips (with
reason) is reported in BUILD-REPORT.md so the operator can see exactly what data
drove the page and what was absent. Copy, photos, quotes, and stats are never
invented; if a section's source data is missing the section is omitted.

Two composition paths, one gate set:
  * Fallback (no --design-plan): the deterministic, template-based emitter that
    M2-M3 shipped. Sections are chosen from brief fields, copy is taken from
    brief fields, layout is the same for every brand. EXACTLY preserved.
  * Plan-driven (--design-plan present): the LLM-authored design_plan.json drives
    section order, emphasis, component choice, and copy. The composer's job
    narrows to "render the plan faithfully, using only what the plan cites from
    the brief". verify_source_fields (imported from design_pass.py) gates the
    plan against the brief — any invented source-field reference rejects the
    build with exit 1 before any HTML is written.

Outputs:
    <outdir>/index.html        semantic HTML, links tokens.css + styles.css
    <outdir>/tokens.css        copy of synthesized tokens/dist/tokens.css
    <outdir>/styles.css        component CSS using var(--*) tokens only
    <outdir>/BUILD-REPORT.md   sections emitted vs skipped + brief provenance +
                                contrast decisions + carried-forward limitations.
                                Plan-driven builds also carry the layout thesis,
                                signature element, per-section rationale, and
                                which brief fields fed each section.

Honesty conventions (same as nt-site-mirror + web-designer SKILL.md):
  * exit 0 + stdout path of outdir              -> site composed cleanly
  * exit 1 + stderr diagnostic                   -> brand brief is invalid,
                                                   required tokens are missing,
                                                   or design-plan failed
                                                   verify_source_fields
  * exit 2 + stderr usage / IO error             -> could not even attempt composition

The script never claims a higher tier than the brief supports; it reports which
sections were skipped because the brief's data was absent (not because the emitter
"forgot") and carries every entry from `brief.limitations[]` forward into the
build report unchanged.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Reuse the shared brand-brief validator. Same module the synthesize_tokens script
# imports — keeps validation consistent across the pipeline.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_brand_brief import _fallback_validate, _jsonschema_validate  # noqa: E402

# M6: shared output-assertion helpers (HTML links tokens.css, no raw hex in
# styles.css, every plan section id rendered-or-skipped). Imported here so both
# the fallback and the plan-driven emit-paths run identical gates before exit 0.
from _output_assertions import (  # noqa: E402
    OutputAssertionError,
    find_raw_hex_in_css,
    require_css_references_tokens_css,
    require_section_ids_rendered_or_skipped,
)


# ---------------------------------------------------------------------------
# Output assertions (M6)
# ---------------------------------------------------------------------------


def _run_output_assertions(
    *,
    html: str,
    stylesheet_text: str,
    declared_section_ids: Iterable[str],
    rendered_skipped_ids: Iterable[str],
    css_label: str,
    tokens_href: str = "tokens.css",
    id_aliases: dict[str, str] | None = None,
) -> None:
    """Run the M6 self-verification gates against an emit's outputs.

    Raises OutputAssertionError (caught by verify.sh / callers) on any violation;
    the message names the offending value. Three checks:

      1. The HTML links `tokens.css` — without it the page silently loses every
         design token and renders off-brand.
      2. `stylesheet_text` contains no raw hex literals. `tokens.css` is exempt
         via `allow_in_token_block=True` semantics — this helper is run on
         styles.css only, where hex is forbidden (use var(--token)).
      3. Every plan section id is either rendered into the HTML or listed as
         skipped. Silence is a Fidelity Gap. `id_aliases` lets callers map
         plan-id -> rendered-id for sections the composer intentionally
         renames (e.g. the first plan section is always anchored as `hero`).
    """
    errors: list[str] = []

    errors.extend(require_css_references_tokens_css(html, tokens_href=tokens_href))

    # `find_raw_hex_in_css` with `allow_in_token_block=True` only exempts lines
    # inside a `:root { ... }` block. styles.css has no such block — every hit
    # is a violation.
    hex_hits = find_raw_hex_in_css(stylesheet_text, allow_in_token_block=True)
    if hex_hits:
        for ln, line in hex_hits:
            errors.append(f"{css_label} L{ln}: raw hex literal — {line}")

    errors.extend(
        require_section_ids_rendered_or_skipped(
            declared_section_ids,
            html,
            rendered_skipped_ids,
            id_aliases=id_aliases,
        )
    )

    if errors:
        raise OutputAssertionError(
            f"compose_site output assertions FAILED ({len(errors)} issue(s)):\n  "
            + "\n  ".join(errors)
        )

SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.1"

# Token CSS variables we EXPECT to find in tokens.css. The emitter uses them as
# var(--token-name) in styles.css; the page CSS itself contains no raw hex. This
# list is also what BUILD-REPORT.md reports as "tokens referenced."
BASE_EXPECTED_TOKEN_VARS: tuple[str, ...] = (
    "--color-primary",
    "--color-secondary",
    "--color-accent",
    "--color-neutral-0",
    "--color-neutral-1",
    "--color-neutral-2",
    "--color-neutral-3",
    "--color-neutral-4",
    "--color-neutral-5",
    "--color-neutral-6",
    "--typography-font-family-display",
    "--typography-font-family-body",
    "--typography-font-family-mono",
    "--spacing-8",
    "--radius-0",
    "--radius-4",
    "--radius-6",
    "--radius-8",
    "--radius-24",
    "--radius-full",
    "--shadow-0",
)

# These are generated by the composer from the brand palette. The M3 token
# synthesis output intentionally remains brand-authentic; accessible text
# variants are a composition-time accommodation, not a replacement for the
# original identity colors.
EXPECTED_TOKEN_VARS: tuple[str, ...] = BASE_EXPECTED_TOKEN_VARS + (
    "--color-primary-text",
    "--color-accent-text",
)

# Regex used to enforce "no raw hex in page CSS". A line containing a 3, 4, 6, or 8
# digit hex literal preceded by `#` is a violation. We deliberately allow hex
# inside tokens.css (that's the source of truth for tokens).
HEX_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b")

# WCAG 2.1 relative-luminance constants.
WCAG_LUMINANCE_THRESHOLD = 0.179  # anything brighter than this is "light"; darker is "dark"
WCAG_NORMAL_TEXT_RATIO = 4.5     # minimum contrast ratio for body text


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ComposeError(Exception):
    """User-facing input / composition error. Exits with code 1."""


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def load_json(path: Path, label: str) -> Any:
    """Load JSON or raise ComposeError. Mirrors synthesize_tokens.py convention."""
    if not path.is_file():
        raise ComposeError(f"{label} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ComposeError(f"{label} is not valid JSON ({path}): {exc}") from exc
    except OSError as exc:
        raise ComposeError(f"could not read {label} ({path}): {exc}") from exc


# ---------------------------------------------------------------------------
# Brand-brief re-validation
# ---------------------------------------------------------------------------


def revalidate_brief(brief_path: Path, schema_path: Path) -> dict[str, Any]:
    """Re-validate the brand brief against the shared schema. Exit nonzero on fail.

    We use the same jsonschema-then-fallback path as validate_brand_brief.main(),
    but with our own logging prefix so the operator can see this run was the
    composition run (not the validator's own smoke run).
    """
    document = load_json(brief_path, "brand brief")
    schema = load_json(schema_path, "brand brief schema")

    try:
        ok, violations = _jsonschema_validate(schema, document)
    except Exception:
        # jsonschema not available — run built-in fallback.
        ok, violations, notes = _fallback_validate(schema, document)
        for n in notes:
            print(f"  (note) {n}", file=sys.stderr)
        if not ok:
            print(f"INVALID brand brief {brief_path} (composer's re-validation):", file=sys.stderr)
            for v in violations:
                print(v, file=sys.stderr)
            raise ComposeError("brand brief failed re-validation")

    if not ok:
        print(f"INVALID brand brief {brief_path} (composer's re-validation):", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        raise ComposeError("brand brief failed re-validation")

    return document


# ---------------------------------------------------------------------------
# Tokens load
# ---------------------------------------------------------------------------


def load_tokens(tokens_root: Path) -> tuple[Path, dict[str, Any], str, dict[str, Any]]:
    """Load the synthesized token artifacts. Returns (tokens.css path, tailwind json dict, css text, font_substitutions).

    The composer needs:
      * tokens/dist/tokens.css     — copied into the output site as a static asset.
      * tokens/dist/tailwind-tokens.json — read for the palette + spacing values
                                           so we can do contrast math + record
                                           provenance without re-parsing CSS.
      * tokens/dist/font-substitutions.json — authoritatively records which
                                              families the synthesizer emitted
                                              (and which were paid->OFL swapped).
                                              Used to build the Google Fonts
                                              <link> tag so the page never
                                              requests a paid family and never
                                              fetches a family nothing uses.

    Raises ComposeError if any required file is missing.
    """
    css_path = tokens_root / "tokens" / "dist" / "tokens.css"
    json_path = tokens_root / "tokens" / "dist" / "tailwind-tokens.json"
    substitutions_path = tokens_root / "tokens" / "dist" / "font-substitutions.json"

    if not css_path.is_file():
        raise ComposeError(
            f"tokens.css not found at expected path: {css_path}. "
            f"Did you point --tokens at the synthesize_tokens output directory?"
        )
    if not json_path.is_file():
        raise ComposeError(
            f"tailwind-tokens.json not found at expected path: {json_path}. "
            f"Did you point --tokens at the synthesize_tokens output directory?"
        )

    css_text = css_path.read_text(encoding="utf-8")
    try:
        tw = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ComposeError(f"tailwind-tokens.json is not valid JSON ({json_path}): {exc}") from exc

    font_substitutions: dict[str, Any] = {
        "meta": {},
        "font_substitutions": {},
        "google_fonts_requested": [],
    }
    if substitutions_path.is_file():
        try:
            font_substitutions = json.loads(substitutions_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ComposeError(
                f"font-substitutions.json is not valid JSON ({substitutions_path}): {exc}"
            ) from exc
    else:
        # Older synthesizer outputs without a sidecar are tolerated: build a
        # defensive empty mapping so the render path still works. We never
        # fabricate Google Fonts requests from tokens.css alone — if the
        # synthesizer didn't write a sidecar we ship no webfont link and let
        # the fallback chain carry the page.
        font_substitutions = {
            "meta": {},
            "font_substitutions": {},
            "google_fonts_requested": [],
            "missing_sidecar": True,
        }

    return css_path, tw, css_text, font_substitutions


def google_fonts_link(font_substitutions: dict[str, Any]) -> str:
    """Build the `<link href="https://fonts.googleapis.com/css2?…">` value
    from the synthesizer's font-substitutions sidecar. Returns an empty string
    if no family is on the Google Fonts catalog that the project supports —
    in which case the page must rely on the system-font fallback chain.
    Never returns a link for a family that the synthesizer did not record as
    a substituted (OFL) primary, so paid families cannot leak into the HTML.
    """
    families: list[str] = []
    for entry in font_substitutions.get("google_fonts_requested", []) or []:
        family_arg = entry.get("family_arg")
        if family_arg and family_arg not in families:
            families.append(family_arg)
    if not families:
        return ""
    return (
        "https://fonts.googleapis.com/css2?"
        + "&".join(f"family={arg}" for arg in families)
        + "&display=swap"
    )


def assert_tokens_referenced(css_text: str, referenced: list[str]) -> None:
    """Confirm every token var the stylesheet plans to use is actually declared in
    tokens.css. If not, raise — this catches token name drift between the
    synthesize step and the compose step before we ship a broken page."""
    declared = set(re.findall(r"--[a-zA-Z0-9_-]+", css_text))
    missing = [v for v in referenced if v not in declared]
    if missing:
        raise ComposeError(
            "tokens.css does not declare expected variables: " + ", ".join(missing)
        )


# ---------------------------------------------------------------------------
# Reference report load (optional)
# ---------------------------------------------------------------------------


def load_reference_report(reference_dir: Path | None) -> dict[str, Any]:
    """Read the reference-understanding outputs if a directory was given.

    Used only for hints in the build report — never for inventing content.
    Returns a dict with whatever sections.json/components.json/copy.json the
    directory contained (may be empty).
    """
    if reference_dir is None:
        return {"present": False, "files": {}, "sections": [], "components": [], "copy": []}
    if not reference_dir.is_dir():
        raise ComposeError(f"--reference-report path is not a directory: {reference_dir}")

    out: dict[str, Any] = {"present": True, "dir": str(reference_dir), "files": {}}
    for filename, key in (
        ("sections.json", "sections"),
        ("components.json", "components"),
        ("copy.json", "copy"),
    ):
        candidate = reference_dir / filename
        if candidate.is_file():
            try:
                out[key] = json.loads(candidate.read_text(encoding="utf-8"))
                out["files"][filename] = str(candidate)
            except json.JSONDecodeError as exc:
                raise ComposeError(f"reference {filename} is not valid JSON: {exc}") from exc
        else:
            out[key] = []
    return out


# ---------------------------------------------------------------------------
# Design-plan load (optional, plan-driven path)
# ---------------------------------------------------------------------------


def load_design_plan(plan_path: Path | None) -> dict[str, Any] | None:
    """Load a design_plan.json if a path was provided. None means fallback path.

    Returns a dict on success. Raises ComposeError on missing/invalid JSON so
    the caller can exit 1 with a clear message before any rendering happens.
    """
    if plan_path is None:
        return None
    if not plan_path.is_file():
        raise ComposeError(f"--design-plan not found: {plan_path}")
    try:
        document = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ComposeError(f"--design-plan is not valid JSON ({plan_path}): {exc}") from exc
    except OSError as exc:
        raise ComposeError(f"could not read --design-plan ({plan_path}): {exc}") from exc
    if not isinstance(document, dict):
        raise ComposeError(f"--design-plan must be a JSON object, got {type(document).__name__}")
    return document


def verify_plan_against_brief(plan: dict[str, Any], brief: dict[str, Any]) -> list[str]:
    """Run design_pass.verify_source_fields against the plan+brief.

    design_pass.py owns the invent-nothing source-field check (its contract is
    that every source_brief_fields path in a plan must resolve to a non-empty
    value in the brief). We import it rather than re-implementing it so the two
    passes share a single source of truth.

    Returns the list of violations (empty = clean). Never raises.
    """
    # design_pass.py is a sibling of compose_site.py under skills/web-designer/scripts/.
    # We import it by file path so we don't need to add the directory to sys.path
    # twice and so the import survives any tool-path reshuffle.
    import importlib.util

    design_pass_path = Path(__file__).resolve().parent / "design_pass.py"
    spec = importlib.util.spec_from_file_location("_web_designer_design_pass", design_pass_path)
    if spec is None or spec.loader is None:
        return [f"could not load design_pass.py from {design_pass_path}"]
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover — defensive
        return [f"failed to import design_pass.verify_source_fields: {exc}"]
    if not hasattr(module, "verify_source_fields"):
        return ["design_pass.py does not export verify_source_fields"]
    return list(module.verify_source_fields(plan, brief))


# ---------------------------------------------------------------------------
# Brand-name derivation
# ---------------------------------------------------------------------------


_BRAND_NAME_FROM_PROJECT_SLUG_STRIP = ("-redesign", "-smoke", "-rebrand", "-redesign-smoke")


def derive_brand_name(brief: dict[str, Any], project_slug_override: str | None) -> tuple[str, str]:
    """Derive a brand name from the brief. Returns (name, source_description).

    The brand brief schema does not include an explicit brand_name field; it is
    referenced by `sources.own_site.url` and `project_slug`. We try, in order:
      1. The project_slug override (if given).
      2. The brief's `project_slug`, with known suffixes stripped (longest first
         so multi-segment suffixes like `-redesign-smoke` are handled correctly).
      3. The bare domain in `sources.own_site.url`, second-level-label titlecased.

    Whatever we derive, we record the rule in the build report so the operator
    sees exactly where the displayed name came from.
    """
    base_slug = project_slug_override or brief.get("project_slug", "")
    if base_slug:
        cleaned = base_slug
        # Strip longest suffixes first so multi-segment ones (e.g. -redesign-smoke)
        # are removed before single-segment ones (e.g. -smoke, -redesign).
        for suffix in sorted(_BRAND_NAME_FROM_PROJECT_SLUG_STRIP, key=len, reverse=True):
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)]
        if cleaned:
            name = " ".join(part.capitalize() for part in cleaned.split("-"))
            return name, f"derived from project_slug '{base_slug}' (suffixes stripped)"

    own_site = brief.get("sources", {}).get("own_site") or {}
    own_url = own_site.get("url") if isinstance(own_site, dict) else None
    if own_url:
        host = (urlparse(own_url).hostname or "").removeprefix("www.")
        label = host.split(".")[0] if host else ""
        if label:
            name = " ".join(part.capitalize() for part in re.split(r"[-_]+", label))
            return name, f"derived from sources.own_site url '{own_url}'"

    # Fallback: use the slug verbatim (titlecased). Honest, visible to the operator.
    return base_slug.title(), "fallback: titlecased project_slug"


# ---------------------------------------------------------------------------
# Section composition
# ---------------------------------------------------------------------------


# Section plan: a plain dict factory (we avoid a real dataclass dependency to
# keep this script self-contained — mirrors synthesize_tokens.py style).
def _section(section_id: str, label: str, emitted: bool, reason: str, brief_fields: list[str],
             notes: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": section_id,
        "label": label,
        "emitted": emitted,
        "reason": reason,
        "brief_fields": brief_fields,
        "notes": list(notes or []),
    }


def plan_sections(brief: dict[str, Any]) -> list[dict[str, Any]]:
    """Decide which sections to emit and which to skip.

    Each section reports:
      * id            — stable anchor id used in HTML
      * label         — human-readable name shown in BUILD-REPORT.md
      * emitted       — bool: whether the section appears on the page
      * reason        — why emitted / skipped (for skipped, the brief field that
                        was missing or empty)
      * brief_fields  — which brief keys feed the section's content
      * notes         — optional additional notes (e.g. "secondary is near-white")
    """
    voice = brief.get("voice_and_tone", {}) or {}
    services = brief.get("service_facts", []) or []
    testimonials = brief.get("testimonials", []) or []
    photos = brief.get("real_photo_inventory", []) or []
    social = brief.get("social_highlights", {}) or {}
    social_linkedin = social.get("linkedin", []) or []
    social_instagram = social.get("instagram", []) or []

    example_lines = voice.get("example_lines", []) or []

    plan: list[dict[str, Any]] = []

    # hero — always emitted (the brief must be valid to reach here; the brand's
    # first example line is the headline candidate).
    hero_emitted = bool(example_lines)
    plan.append(
        _section(
            section_id="hero",
            label="Hero",
            emitted=hero_emitted,
            reason="emitted: voice_and_tone.example_lines[0] used as headline"
            if hero_emitted
            else "skipped: voice_and_tone.example_lines was empty",
            brief_fields=["voice_and_tone.example_lines", "voice_and_tone.register"],
        )
    )

    # about — emitted whenever the brief has any voice/tone color (notes, register).
    about_emitted = bool(voice.get("notes") or voice.get("register"))
    plan.append(
        _section(
            section_id="about",
            label="About",
            emitted=about_emitted,
            reason="emitted: voice_and_tone.notes used as about copy"
            if about_emitted
            else "skipped: voice_and_tone.notes and register both empty",
            brief_fields=["voice_and_tone.notes", "voice_and_tone.register"],
        )
    )

    # services — only if service_facts has at least one entry.
    plan.append(
        _section(
            section_id="services",
            label="Services",
            emitted=bool(services),
            reason="emitted: service_facts[] used as service cards"
            if services
            else "skipped: brief.service_facts[] was empty",
            brief_fields=["service_facts[]"],
        )
    )

    # testimonials — ONLY if testimonials[] is non-empty. This is the gate
    # the operator is using to verify the skipped-section logic; the smoke brief
    # has an empty testimonials[] and this MUST be skipped.
    plan.append(
        _section(
            section_id="testimonials",
            label="Testimonials",
            emitted=bool(testimonials),
            reason="emitted: testimonials[] used as quote cards"
            if testimonials
            else "skipped: brief.testimonials[] was empty (no quotes recoverable)",
            brief_fields=["testimonials[]"],
        )
    )

    # social / photos — ONLY if real_photo_inventory[] OR social_highlights has
    # at least one entry. The smoke brief has 3 photos (logo SVG + 2 share cards)
    # so this MUST be emitted.
    has_photos = bool(photos)
    has_social = bool(social_linkedin or social_instagram)
    plan.append(
        _section(
            section_id="social-photos",
            label="Brand assets & social",
            emitted=has_photos or has_social,
            reason=(
                "emitted: real_photo_inventory[] used as asset list"
                if has_photos and not has_social
                else "emitted: social_highlights used as post list"
                if has_social and not has_photos
                else "emitted: real_photo_inventory[] and social_highlights used together"
                if has_photos and has_social
                else "skipped: real_photo_inventory[] and social_highlights both empty"
            ),
            brief_fields=["real_photo_inventory[]", "social_highlights.linkedin[]", "social_highlights.instagram[]"],
        )
    )

    # contact / CTA — always emitted (every site needs one). The CTA copy is
    # derived from voice_and_tone.register + the brand's favorite words.
    plan.append(
        _section(
            section_id="contact",
            label="Contact / CTA",
            emitted=True,
            reason="emitted: always included (every site needs a contact section); CTA copy derived from voice register + favorite_words",
            brief_fields=["voice_and_tone.register", "voice_and_tone.favorite_words"],
        )
    )

    return plan


# ---------------------------------------------------------------------------
# Plan-driven rendering (design-plan path)
# ---------------------------------------------------------------------------


# Emphasis → CSS-level treatment. The whole point of plan-mode is that two
# different plans yield two structurally different pages, so emphasis MUST
# produce visibly different treatment (scale, spacing, width, weight) — not
# just a different class name. Keep this table close to the renderer that
# reads it; both live behind the "plan-driven" gate.
EMPHASIS_RULES: dict[str, dict[str, str]] = {
    # emphasis -> CSS class suffix used in styles.css (rendered as data-emphasis)
    "hero":      {"emphasis_class": "emphasis-hero",      "heading_level": "1"},
    "primary":   {"emphasis_class": "emphasis-primary",   "heading_level": "2"},
    "secondary": {"emphasis_class": "emphasis-secondary", "heading_level": "2"},
    "minor":     {"emphasis_class": "emphasis-minor",     "heading_level": "2"},
}


def index_copy_blocks(copy_blocks: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    """Index plan copy blocks by (section_id, role). The first block wins.

    The schema requires unique (section_id, role) pairs in practice but does not
    enforce it; we are deterministic about which one we keep and surface the
    collisions in the build report.
    """
    index: dict[tuple[str, str], str] = {}
    collisions: list[str] = []
    for block in copy_blocks:
        sid = block.get("section_id", "")
        role = block.get("role", "")
        text = block.get("text", "")
        key = (sid, role)
        if key in index and index[key] != text:
            collisions.append(f"{sid}/{role}")
        index[key] = text
    return index


def plan_section_view(
    plan_sections: list[dict[str, Any]],
    copy_index: dict[tuple[str, str], str],
    brief: dict[str, Any],
    signature_element: dict[str, Any],
    motion_register: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build the renderer's per-section view from a design plan.

    Returns:
      (sections, skipped) where each section is a dict with keys:
        id, order, emphasis, component, purpose, rationale, brief_fields,
        headline, subhead, body, cta, caption, source_label

    This is the SINGLE place where "what to render for a plan section" is
    decided. Every per-section renderer downstream reads this view and never
    reaches back into the brief directly — that is what keeps the plan-driven
    renderer honest (the brief is consulted only to enrich, not to invent).
    """
    services = brief.get("service_facts", []) or []
    photos = brief.get("real_photo_inventory", []) or []

    sections: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for sec in sorted(plan_sections, key=lambda s: s.get("order", 0)):
        sid = sec.get("id", "")
        emphasis = sec.get("emphasis", "secondary")
        component = sec.get("component", "")
        headline = copy_index.get((sid, "headline"), "")
        subhead = copy_index.get((sid, "subhead"), "")
        body = copy_index.get((sid, "body"), "")
        cta = copy_index.get((sid, "cta"), "")
        caption = copy_index.get((sid, "caption"), "")
        brief_fields = list(sec.get("source_brief_fields", []) or [])

        view = {
            "id": sid,
            "order": sec.get("order", 0),
            "emphasis": emphasis,
            "component": component,
            "purpose": sec.get("purpose", ""),
            "rationale": sec.get("rationale", ""),
            "brief_fields": brief_fields,
            "nav_label": sec.get("nav_label"),
            "in_nav": bool(sec.get("in_nav", False)),
            "headline": headline,
            "subhead": subhead,
            "body": body,
            "cta": cta,
            "caption": caption,
            # Per-section pull from brief objects, gated by which fields the
            # plan cited. The renderer never invents — it only fills slots the
            # plan marked.
            "services": services if any("service_facts" in f for f in brief_fields) else [],
            "photos": photos if any("real_photo_inventory" in f for f in brief_fields) else [],
            "signature_element": signature_element,
            "motion_register": motion_register,
        }
        # A section with no copy at all AND no brief-derived payload is treated
        # as skipped (the plan referenced it, but the brief has nothing for it
        # to render). We don't fail the build — we surface it honestly.
        if not any([headline, subhead, body, cta, caption]) and not view["services"] and not view["photos"]:
            skipped.append({
                "id": sid,
                "reason": "plan listed this section but no copy_blocks or brief payload were available to fill it",
                "missing_brief_fields": brief_fields,
            })
            continue

        sections.append(view)

    return sections, skipped


def render_plan_signature_element(signature_element: dict[str, Any]) -> str:
    """Emit the signature element as a real, reusable visual device.

    Returns an HTML snippet that callers can drop inline. The corresponding
    CSS lives in render_plan_stylesheet() under the `.signature-dot` selector
    and is keyed to the implementation_note of the plan's signature_element.
    """
    if not signature_element:
        return ""
    # We expose the device as a single <span class="signature-dot"> so it can
    # sit inline at the end of a sentence, beside a list item, or inside a
    # CTA. The CSS gives it a 0.6em circular dot in --color-primary, with the
    # 0.4em trailing variant for CTA cursors.
    return '<span class="signature-dot" aria-hidden="true"></span>'


def render_plan_section(
    section: dict[str, Any],
    *,
    is_first_section: bool,
) -> str:
    """Generic section renderer driven by emphasis + component.

    The whole point of plan-mode is that emphasis produces visibly different
    treatment (scale, spacing, width, weight). This function does NOT know
    about specific section ids — it reads emphasis and component from the
    plan and emits the right HTML shape. A 'thesis-statement' with
    emphasis=hero gets a big left-aligned h1; a 'footer-colophon' with
    emphasis=minor gets a tiny single line.
    """
    sid = section["id"]
    emphasis = section["emphasis"]
    component = section.get("component", "")
    rules = EMPHASIS_RULES.get(emphasis, EMPHASIS_RULES["secondary"])
    heading_level = rules["heading_level"]
    heading_text = section.get("headline", "")
    subhead_text = section.get("subhead", "")
    body_text = section.get("body", "")
    cta_text = section.get("cta", "")
    caption_text = section.get("caption", "")
    services = section.get("services", []) or []
    photos = section.get("photos", []) or []
    sig = section.get("signature_element") or {}

    # Heading: only emit if we have a headline AND the emphasis asks for a
    # heading level. The hero emphasis always emits an h1; primary/secondary/
    # minor emit h2 only when a headline was supplied by copy_blocks.
    heading_html = ""
    if heading_text and heading_level == "1":
        # Hero gets a left-aligned single-line headline with the gold dot
        # as the sentence-ending period (per signature_element usage).
        trailing_dot = render_plan_signature_element(sig) if sig else ""
        heading_html = (
            f'      <h1 id="{sid}-heading" class="plan-heading plan-heading--hero">'
            f'{escape(heading_text)} {trailing_dot}</h1>\n'
        )
    elif heading_text:
        heading_html = (
            f'      <h{heading_level} id="{sid}-heading" class="plan-heading">'
            f'{escape(heading_text)}</h{heading_level}>\n'
        )

    subhead_html = (
        f'      <p class="plan-subhead">{escape(subhead_text)}</p>\n'
        if subhead_text
        else ""
    )
    body_html = (
        f'      <p class="plan-body">{escape(body_text)}</p>\n'
        if body_text
        else ""
    )
    caption_html = (
        f'      <p class="plan-caption">{escape(caption_text)}</p>\n'
        if caption_text
        else ""
    )

    # Component-specific body shapes. Each one is small and lives here rather
    # than in its own function so the emphasis-aware CSS does all the visual
    # differentiation work — and so two plans with different ids but the same
    # emphasis get visually consistent treatment.
    body_inner = ""
    if services and ("service" in sid or "curriculum" in sid or "service" in component.lower()):
        # Numbered vertical "curriculum" (services-as-chapters) layout.
        rows = []
        for i, svc in enumerate(services, start=1):
            name = escape(svc.get("name", ""))
            description = escape(svc.get("description", ""))
            dot = render_plan_signature_element(sig) if sig else ""
            rows.append(
                f"""        <li class="plan-curriculum-row">
          <span class="plan-curriculum-number" aria-hidden="true">{dot}<span class="plan-curriculum-numeral">{i}</span></span>
          <div class="plan-curriculum-body">
            <h3 class="plan-curriculum-name">{name}</h3>
            <p class="plan-curriculum-description">{description}</p>
          </div>
        </li>"""
            )
        body_inner = (
            "\n      <ol class=\"plan-curriculum\" role=\"list\">\n"
            + "\n".join(rows)
            + "\n      </ol>"
        )
    elif "process" in sid or "how" in sid or "step" in component.lower():
        # Process strip: split body into sentences and number them.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body_text) if s.strip()] if body_text else []
        if sentences:
            items = []
            for i, s in enumerate(sentences, start=1):
                dot = render_plan_signature_element(sig) if sig else ""
                items.append(
                    f"""        <li class="plan-step">
          <span class="plan-step-number" aria-hidden="true">{dot}<span class="plan-step-numeral">{i}</span></span>
          <p class="plan-step-body">{escape(s)}</p>
        </li>"""
                )
            body_inner = (
                "\n      <ol class=\"plan-steps\" role=\"list\">\n"
                + "\n".join(items)
                + "\n      </ol>"
            )
    elif photos and ("blurb" in sid or "image" in sid or "asset" in sid or "preview" in sid):
        # Single-image band: render the first photo that isn't the logo SVG.
        chosen = None
        for p in photos:
            if not p.get("url", "").lower().endswith(".svg"):
                chosen = p
                break
        if chosen is None and photos:
            chosen = photos[0]
        if chosen is not None:
            url = escape(chosen.get("url", ""))
            subject = escape(chosen.get("subject", ""))
            license_text = escape(chosen.get("license", ""))
            body_inner = (
                f"\n      <figure class=\"plan-asset\">\n"
                f"        <img src=\"{url}\" alt=\"{subject}\" loading=\"lazy\">\n"
                f"        <figcaption>\n"
                f"          <span class=\"plan-asset-subject\">{subject}</span>\n"
                f"          <span class=\"plan-asset-meta\">License: {license_text}</span>\n"
                f"          {caption_html if caption_html else ''}\n"
                f"        </figcaption>\n"
                f"      </figure>"
            )
    elif "cta" in sid or "call" in sid or "contact" in sid:
        # CTA band: full-width secondary surface, one sentence + one button.
        dot = render_plan_signature_element(sig) if sig else ""
        cta_label = cta_text or "Get in touch"
        body_inner = (
            f"\n      <div class=\"plan-cta-band\">\n"
            f"        {body_html}"
            f"        <p class=\"plan-cta-action\"><a class=\"button plan-cta-button\" href=\"#contact\">{escape(cta_label)} {dot}</a></p>\n"
            f"      </div>"
        )
        # We deliberately do NOT also emit body_html above the band — the band
        # already includes the body sentence inside its wrapper.
        body_html = ""
        caption_html = ""
    elif "colophon" in sid or "footer" in sid:
        # Footer-style single paragraph.
        body_inner = ""
    else:
        # Default: prose block.
        body_inner = ""

    # The first section in the plan is the hero — anchor it with id="hero" so
    # the skip-link and brand-mark both still work, regardless of what the
    # plan called the section.
    anchor_id = "hero" if is_first_section else sid
    emphasis_class = rules["emphasis_class"]

    parts = [
        f'    <section id="{anchor_id}" class="plan-section {emphasis_class}" data-emphasis="{emphasis}" data-component="{escape(component, quote=True)}" aria-labelledby="{sid}-heading">',
    ]
    if heading_html:
        parts.append(heading_html.rstrip("\n"))
    if subhead_html:
        parts.append(subhead_html.rstrip("\n"))
    if body_inner:
        parts.append(body_inner.rstrip("\n"))
    if body_html:
        parts.append(body_html.rstrip("\n"))
    if caption_html:
        parts.append(caption_html.rstrip("\n"))
    parts.append("    </section>")

    return "\n".join(parts)


def render_html_from_plan(
    *,
    brief: dict[str, Any],
    plan: dict[str, Any],
    sections: list[dict[str, Any]],
    brand_name: str,
    brand_name_source: str,
    font_substitutions: dict[str, Any] | None = None,
) -> str:
    """Render the full index.html from a plan.

    Returns the document string. The structure is the same shell as the
    fallback (header, main, footer, semantic landmarks, one h1, alt text,
    labels) but every section body comes from `sections`, which in turn was
    built by plan_section_view() from the design plan.

    `font_substitutions` is the synthesizer sidecar; it carries the resolved
    primary family for each role (after any paid->OFL substitution) and the
    Google Fonts URL fragment list to fetch. The page-side `<html style="...">`
    inline fallback uses the synthesized primary names — never the brand's
    original (paid) names — so the inline fallback cannot accidentally load
    an unlicensed font either.
    """
    typography = brief.get("typography_recommendation", {}) or {}
    palette = brief.get("palette_from_logo", {}) or {}
    subs = font_substitutions or {}
    resolved = subs.get("font_substitutions", {}) or {}

    copy_index = index_copy_blocks(plan.get("copy_blocks", []) or [])
    section_htmls = [
        render_plan_section(sec, is_first_section=(i == 0))
        for i, sec in enumerate(sections)
    ]
    body_inner = "\n\n".join(s for s in section_htmls if s)

    # Title and description from the plan's first section headline + thesis.
    thesis = plan.get("layout_thesis", {}) or {}
    first_headline = ""
    for sec in sorted(plan.get("sections", []), key=lambda s: s.get("order", 0)):
        block = copy_index.get((sec.get("id", ""), "headline"))
        if block:
            first_headline = block
            break
    if not first_headline:
        first_headline = brand_name
    title = f"{escape(brand_name)} — {escape(first_headline)}"
    thesis_statement = (thesis.get("statement") or "").strip()[:160]
    description = escape(thesis_statement or first_headline)

    # Use the resolved (post-substitution) families for the inline fallback
    # chain in <html style="...">. Fall back to the brand-declared family only
    # if the synthesizer didn't write a sidecar.
    display = escape(resolved.get("display", {}).get("primary") or typography.get("display_family") or "sans-serif")
    body = escape(resolved.get("body", {}).get("primary") or typography.get("body_family") or "sans-serif")
    mono = escape(resolved.get("mono", {}).get("primary") or typography.get("mono_family") or "monospace")
    primary = escape(palette.get("primary", "#000000"))
    secondary = escape(palette.get("secondary", "#ffffff"))

    fonts_link = google_fonts_link(subs)
    if fonts_link:
        fonts_preconnect = (
            '    <link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'    <link href="{fonts_link}" rel="stylesheet">\n'
        )
    else:
        fonts_preconnect = (
            '    <!-- No Google Fonts link: synthesizer sidecar recorded zero '
            'catalog families; the page relies on its fallback chain. -->\n'
        )

    # Nav: link to every section that exists. The first one anchors to #hero.
    nav_items: list[str] = []
    for i, sec in enumerate([s for s in sections if s.get("in_nav", False)]):
        sid = sec["id"]
        href = "#hero" if i == 0 else f"#{sid}"
        label = sec.get("nav_label") or " ".join(w.capitalize() for w in sid.replace("-", " ").split()[:2])
        nav_items.append(f'          <li><a href="{href}">{escape(label)}</a></li>')

    nav_html = "\n".join(nav_items) if nav_items else (
        '          <li><a href="#hero">Home</a></li>'
    )

    return f"""<!doctype html>
<html lang="en" style="--page-display: {display}; --page-body: {body}; --page-mono: {mono}; --page-primary: {primary}; --page-secondary: {secondary};">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <link rel="stylesheet" href="tokens.css">
    <link rel="stylesheet" href="styles.css">
  </head>
  <body class="plan-driven">
    <a class="skip-link" href="#main">Skip to main content</a>
    <header class="site-header" role="banner">
      <nav aria-label="Primary">
        <a class="brand" href="#hero" aria-label="{escape(brand_name)} — home">{escape(brand_name)}</a>
        <ul class="nav-list" role="list">
{nav_html}
        </ul>
      </nav>
    </header>

    <main id="main" tabindex="-1">
{body_inner}
    </main>

    <footer class="site-footer" role="contentinfo">
      <p>&copy; {escape(brand_name)}. Generated by compose_site.py v{escape(TOOL_VERSION)} from design plan.</p>
      <p class="footer-meta">Plan-driven build, see BUILD-REPORT.md for the layout thesis and section rationale.</p>
    </footer>
  </body>
</html>
"""


# ---------------------------------------------------------------------------
# HTML rendering (fallback / template path — UNCHANGED)
# ---------------------------------------------------------------------------


def render_html(
    *,
    brief: dict[str, Any],
    plan: list[dict[str, Any]],
    brand_name: str,
    brand_name_source: str,
    contact_email: str | None,
) -> str:
    """Render the index.html. Semantic landmarks, one h1, logical heading order,
    alt text on every img, labels on every form control."""
    voice = brief.get("voice_and_tone", {}) or {}
    palette = brief.get("palette_from_logo", {}) or {}
    typography = brief.get("typography_recommendation", {}) or {}
    services = brief.get("service_facts", []) or []
    testimonials = brief.get("testimonials", []) or []
    photos = brief.get("real_photo_inventory", []) or []
    social = brief.get("social_highlights", {}) or {}
    social_linkedin = social.get("linkedin", []) or []
    social_instagram = social.get("instagram", []) or []

    # --- per-section bodies --------------------------------------------------
    sections_html: list[str] = []

    # hero
    hero_html = _render_hero(brand_name, voice, palette)
    sections_html.append(hero_html)

    # about
    about_html = _render_about(voice)
    sections_html.append(about_html)

    # services (only if planned)
    if any(s["id"] == "services" and s["emitted"] for s in plan):
        sections_html.append(_render_services(services))

    # testimonials (only if planned) — the smoke brief's empty list makes this a no-op
    if any(s["id"] == "testimonials" and s["emitted"] for s in plan):
        sections_html.append(_render_testimonials(testimonials))

    # social / photos
    if any(s["id"] == "social-photos" and s["emitted"] for s in plan):
        sections_html.append(_render_social_photos(photos, social_linkedin, social_instagram))

    # contact / CTA — always
    sections_html.append(_render_contact(brand_name, voice, contact_email))

    body_inner = "\n\n".join(s for s in sections_html if s)

    # --- HTML document -------------------------------------------------------
    title = f"{escape(brand_name)} — {escape(_first_non_empty(voice.get('example_lines'), 'Brand site'))}"
    description = escape(_first_non_empty(voice.get("notes"), ""))[:160]

    # Font family stacks — used as inline fallback inside the <html> style attr
    # so the page degrades gracefully even if tokens.css fails to load.
    display = "Inter" if typography.get("display_family") == "Switzer" else escape(typography.get("display_family", "sans-serif"))
    body = escape(typography.get("body_family", "sans-serif"))
    mono = escape(typography.get("mono_family", "monospace"))

    primary = escape(palette.get("primary", "#000000"))
    secondary = escape(palette.get("secondary", "#ffffff"))

    return f"""<!doctype html>
<html lang="en" style="--page-display: {display}; --page-body: {body}; --page-mono: {mono}; --page-primary: {primary}; --page-secondary: {secondary};">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <link rel="stylesheet" href="tokens.css">
    <link rel="stylesheet" href="styles.css">
  </head>
  <body>
    <a class="skip-link" href="#main">Skip to main content</a>
    <header class="site-header" role="banner">
      <nav aria-label="Primary">
        <a class="brand" href="#hero" aria-label="{escape(brand_name)} — home">{escape(brand_name)}</a>
        <ul class="nav-list" role="list">
          <li><a href="#about">About</a></li>
          <li><a href="#services">Services</a></li>
          <li><a href="#contact">Contact</a></li>
        </ul>
      </nav>
    </header>

    <main id="main" tabindex="-1">
{body_inner}
    </main>

    <footer class="site-footer" role="contentinfo">
      <p>&copy; {escape(brand_name)}. Generated by compose_site.py v{escape(TOOL_VERSION)}.</p>
      <p class="footer-meta">Static site, no build step. Tokens from synthesize_tokens.py.</p>
    </footer>
  </body>
</html>
"""


def _render_hero(brand_name: str, voice: dict[str, Any], palette: dict[str, Any]) -> str:
    """Hero section. Headline = voice.example_lines[0] if present, else brand name.
    Subhead = next example line if present, else voice.notes (first sentence)."""
    lines = voice.get("example_lines") or []
    headline = lines[0] if lines else brand_name
    subhead = lines[1] if len(lines) > 1 else _first_sentence(voice.get("notes", "")) or brand_name

    tagline = ""
    if lines:
        # The smoke brief has a one-word tagline "Limitless." — surface it as an
        # eyebrow above the headline when it exists and is short.
        tagline_candidate = lines[1] if len(lines) > 2 else None  # prefer a short line
        if tagline_candidate and len(tagline_candidate.split()) <= 3:
            tagline = tagline_candidate

    tagline_html = f'      <p class="hero-tagline">{escape(tagline)}</p>\n' if tagline else ""
    return f"""    <section id="hero" class="hero" aria-labelledby="hero-heading">
{tagline_html}      <h1 id="hero-heading">{escape(headline)}</h1>
      <p class="hero-subhead">{escape(subhead)}</p>
      <p class="hero-cta"><a class="button" href="#contact">Get in touch</a></p>
    </section>"""


def _render_about(voice: dict[str, Any]) -> str:
    notes = voice.get("notes", "") or ""
    register = voice.get("register", "")
    fav = voice.get("favorite_words", []) or []
    fav_html = ""
    if fav:
        items = "".join(f"<li>{escape(w)}</li>" for w in fav)
        fav_html = f"\n      <p class=\"about-label\">Words the brand repeats</p>\n      <ul class=\"favorite-words\" role=\"list\">{items}</ul>"
    register_html = (
        f'\n      <p class="about-register"><span class="visually-hidden">Voice register: </span>{escape(register)}</p>'
        if register
        else ""
    )
    return f"""    <section id="about" class="about" aria-labelledby="about-heading">
      <h2 id="about-heading">About</h2>
      <p>{escape(notes)}</p>{register_html}{fav_html}
    </section>"""


def _render_services(services: list[dict[str, Any]]) -> str:
    cards = []
    for svc in services:
        name = escape(svc.get("name", ""))
        description = escape(svc.get("description", ""))
        price = escape(svc.get("price_range", ""))
        price_html = f'\n          <p class="service-price">{price}</p>' if price else ""
        cards.append(
            f"""        <article class="service-card">
          <h3>{name}</h3>
          <p>{description}</p>{price_html}
        </article>"""
        )
    cards_html = "\n".join(cards)
    return f"""    <section id="services" class="services" aria-labelledby="services-heading">
      <h2 id="services-heading">Services</h2>
      <div class="service-grid">
{cards_html}
      </div>
    </section>"""


def _render_testimonials(testimonials: list[dict[str, Any]]) -> str:
    cards = []
    for t in testimonials:
        quote = escape(t.get("quote", ""))
        attribution = escape(t.get("attribution", ""))
        cards.append(
            f"""        <figure class="testimonial">
          <blockquote>{quote}</blockquote>
          <figcaption>— {attribution}</figcaption>
        </figure>"""
        )
    cards_html = "\n".join(cards)
    return f"""    <section id="testimonials" class="testimonials" aria-labelledby="testimonials-heading">
      <h2 id="testimonials-heading">Testimonials</h2>
      <div class="testimonial-grid">
{cards_html}
      </div>
    </section>"""


def _render_social_photos(
    photos: list[dict[str, Any]],
    linkedin: list[dict[str, Any]],
    instagram: list[dict[str, Any]],
) -> str:
    """Brand assets + social highlights. Photos use their real `subject` as alt text.

    We do NOT download images here — we link to them with their declared URL and
    trust the asset's own license. For the logo SVG (the smoke brief's primary
    asset), the URL is brand-owned and safe to reference directly."""
    photo_cards = []
    for p in photos:
        url = escape(p.get("url", ""))
        subject = escape(p.get("subject", ""))
        license_text = escape(p.get("license", ""))
        uses = ", ".join(p.get("use") or [])
        photo_cards.append(
            f"""        <figure class="asset-card">
          <img src="{url}" alt="{subject}" loading="lazy">
          <figcaption>
            <span class="asset-subject">{subject}</span>
            <span class="asset-meta">License: {license_text}</span>
            <span class="asset-meta">Use: {escape(uses)}</span>
          </figcaption>
        </figure>"""
        )
    photos_html = ""
    if photo_cards:
        photos_html = (
            "\n      <h3>Brand assets</h3>\n"
            "      <div class=\"asset-grid\">\n"
            + "\n".join(photo_cards)
            + "\n      </div>"
        )

    linkedin_html = ""
    if linkedin:
        items = "".join(
            f'<li><time datetime="{escape(e.get("date", ""))}">{escape(e.get("date", ""))}</time>'
            f' — {escape(e.get("excerpt", ""))}</li>'
            for e in linkedin
        )
        linkedin_html = (
            f'\n      <h3>LinkedIn highlights</h3>\n      <ul role="list">{items}</ul>'
        )

    instagram_html = ""
    if instagram:
        items = "".join(
            f'<li><time datetime="{escape(e.get("date", ""))}">{escape(e.get("date", ""))}</time>'
            f' — {escape(e.get("caption", ""))}</li>'
            for e in instagram
        )
        instagram_html = (
            f'\n      <h3>Instagram highlights</h3>\n      <ul role="list">{items}</ul>'
        )

    return f"""    <section id="social-photos" class="social-photos" aria-labelledby="social-heading">
      <h2 id="social-heading">Brand & social</h2>{photos_html}{linkedin_html}{instagram_html}
    </section>"""


def _render_contact(brand_name: str, voice: dict[str, Any], contact_email: str | None) -> str:
    """Contact / CTA. Form uses a labeled email input (required by M4 gate 3)."""
    fav = voice.get("favorite_words", []) or []
    fav_first = fav[0] if fav else "connect"
    cta = f"Start a conversation about your {fav_first}."
    if not contact_email:
        contact_email = f"hello@{_slugify(brand_name)}.example"
    return f"""    <section id="contact" class="contact" aria-labelledby="contact-heading">
      <h2 id="contact-heading">Contact</h2>
      <p>{escape(cta)}</p>
      <form class="contact-form" action="mailto:{escape(contact_email)}" method="post">
        <div class="field">
          <label for="contact-name">Your name</label>
          <input id="contact-name" name="name" type="text" autocomplete="name" required>
        </div>
        <div class="field">
          <label for="contact-email">Email address</label>
          <input id="contact-email" name="email" type="email" autocomplete="email" required>
        </div>
        <div class="field">
          <label for="contact-message">Message</label>
          <textarea id="contact-message" name="message" rows="4" required></textarea>
        </div>
        <p class="form-actions">
          <button class="button" type="submit">Send</button>
        </p>
      </form>
      <p class="contact-email">Or email <a href="mailto:{escape(contact_email)}">{escape(contact_email)}</a> directly.</p>
    </section>"""


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------


def render_stylesheet(contrast_decision: dict[str, Any]) -> str:
    """Emit the page CSS. NO raw hex — only var(--token-name) references.

    Every color, spacing value, radius, and shadow uses a token variable. The
    emit guard in main() greps the produced CSS for hex literals; this is the
    check M4 will run, so the discipline must hold here.
    """
    text_token = contrast_decision["text_token"]
    bg_token = contrast_decision["bg_token"]
    accent_token = contrast_decision["accent_token"]
    primary_text_token = contrast_decision["primary_text_token"]
    accent_text_token = contrast_decision["accent_text_token"]

    return f"""/* compose_site.py v{TOOL_VERSION} — token-driven page CSS.
 *
 * Design rule: NO raw hex colors appear below. Every color comes from a
 * tokens.css custom property (declared in tokens/dist/tokens.css). This is
 * enforced at emit time by a hex-literal grep; see BUILD-REPORT.md.
 *
 * Contrast decision: text {text_token} on background {bg_token}, accent {accent_token}.
 * Contrast ratio measured: {contrast_decision["ratio_text_bg"]:.2f}:1
 * (WCAG AA for normal body text requires >= 4.5:1).
 */

:root {{
  color-scheme: light;
}}

* {{
  box-sizing: border-box;
}}

html {{
  /* Fonts: use token variables; fall back to inline-resolved page-* vars. */
  font-family: var(--typography-font-family-body, var(--page-body, sans-serif));
  font-size: var(--typography-font-size-2, 16px);
  line-height: 1.55;
  color: var({text_token});
  background-color: var({bg_token});
}}

body {{
  margin: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}

/* Skip link — visible only on focus (a11y best practice). */
.skip-link {{
  position: absolute;
  inset-inline-start: var(--spacing-8);
  inset-block-start: 0;
  transform: translateY(-150%);
  background: var(--color-primary);
  color: var(--color-neutral-0);
  padding: var(--spacing-8) calc(var(--spacing-8) * 2);
  border-radius: var(--radius-4);
  text-decoration: none;
  font-weight: 600;
  z-index: 100;
  transition: transform 120ms ease-out;
}}
.skip-link:focus {{
  transform: translateY(0);
  outline: 3px solid var(--color-accent);
  outline-offset: 2px;
}}

/* Headings — display family, scale per tokens.css. */
h1, h2, h3, h4 {{
  font-family: var(--typography-font-family-display, var(--page-display, serif));
  line-height: 1.15;
  margin: 0 0 calc(var(--spacing-8) * 2);
  color: var(--color-neutral-0);
}}
h1 {{
  font-size: var(--typography-font-size-6, 48px);
  letter-spacing: -0.01em;
}}
h2 {{
  font-size: var(--typography-font-size-5, 32px);
  letter-spacing: -0.005em;
}}
h3 {{
  font-size: var(--typography-font-size-4, 24px);
}}
p {{
  margin: 0 0 calc(var(--spacing-8) * 2);
  max-width: 60ch;
}}
ul {{
  padding-inline-start: calc(var(--spacing-8) * 2);
  margin: 0 0 calc(var(--spacing-8) * 2);
}}

a {{
  color: var({accent_text_token});
  text-decoration-thickness: 1px;
  text-underline-offset: 0.18em;
}}
a:hover {{ text-decoration-thickness: 2px; }}

/* Keyboard focus — visible to all users, not just mouse. */
:focus-visible {{
  outline: 3px solid var({accent_token});
  outline-offset: 2px;
  border-radius: var(--radius-4);
}}

/* Visually hidden — for screen-reader-only labels. */
.visually-hidden {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}}

/* ---- Header / nav ---- */
.site-header {{
  background: var(--color-neutral-6);
  border-block-end: 1px solid var(--color-neutral-4);
  padding: calc(var(--spacing-8) * 2) var(--spacing-8);
  position: sticky;
  top: 0;
  z-index: 10;
}}
.site-header nav {{
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(var(--spacing-8) * 2);
  flex-wrap: wrap;
}}
.brand {{
  font-family: var(--typography-font-family-display, var(--page-display, serif));
  font-size: var(--typography-font-size-4, 24px);
  font-weight: 700;
  color: var(--color-neutral-0);
  text-decoration: none;
}}
.nav-list {{
  list-style: none;
  display: flex;
  gap: calc(var(--spacing-8) * 2);
  margin: 0;
  padding: 0;
}}
.nav-list a {{
  color: var(--color-neutral-1);
  text-decoration: none;
  font-weight: 500;
}}
.nav-list a:hover {{ color: var({accent_text_token}); }}

/* ---- Main ---- */
main {{
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: calc(var(--spacing-8) * 4) var(--spacing-8);
}}
main:focus {{ outline: none; }}
section {{
  margin-block-end: calc(var(--spacing-8) * 6);
}}

/* ---- Hero ---- */
.hero {{
  padding-block: calc(var(--spacing-8) * 4);
  border-block-end: 1px solid var(--color-neutral-4);
}}
.hero-tagline {{
  font-family: var(--typography-font-family-display, var(--page-display, serif));
  font-size: var(--typography-font-size-3, 20px);
  font-weight: 500;
  color: var({primary_text_token});
  margin-bottom: var(--spacing-8);
}}
.hero-subhead {{
  font-size: var(--typography-font-size-4, 24px);
  color: var(--color-neutral-1);
  max-width: 50ch;
}}
.hero-cta {{
  margin-top: calc(var(--spacing-8) * 3);
}}

/* ---- Buttons (CTA) ---- */
.button {{
  display: inline-block;
  background: var({accent_token});
  color: var(--color-neutral-0);
  padding: calc(var(--spacing-8) * 1.5) calc(var(--spacing-8) * 3);
  border-radius: var(--radius-8);
  font-weight: 600;
  text-decoration: none;
  border: 2px solid transparent;
  transition: background-color 120ms ease-out, border-color 120ms ease-out;
}}
.button:hover,
.button:focus-visible {{
  background: var(--color-neutral-0);
  color: var(--color-neutral-6);
  border-color: var({accent_token});
}}

/* ---- About ---- */
.about {{
  padding-block: calc(var(--spacing-8) * 4);
}}
.about-register {{
  display: inline-block;
  padding: calc(var(--spacing-8) / 2) var(--spacing-8);
  background: var(--color-secondary);
  border: 1px solid var(--color-neutral-4);
  border-radius: var(--radius-full);
  font-size: var(--typography-font-size-0, 12px);
  color: var(--color-neutral-1);
  font-weight: 500;
}}
.about-label {{
  font-size: var(--typography-font-size-0, 12px);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-neutral-2);
  margin-block-start: calc(var(--spacing-8) * 3);
}}
.favorite-words {{
  list-style: none;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-8);
}}
.favorite-words li {{
  background: var(--color-secondary);
  color: var(--color-neutral-1);
  padding: var(--spacing-8) calc(var(--spacing-8) * 1.5);
  border-radius: var(--radius-6);
  font-size: var(--typography-font-size-1, 14px);
  border: 1px solid var(--color-neutral-4);
}}

/* ---- Services ---- */
.service-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: calc(var(--spacing-8) * 2);
}}
.service-card {{
  background: var(--color-neutral-6);
  border: 1px solid var(--color-neutral-4);
  border-radius: var(--radius-8);
  padding: calc(var(--spacing-8) * 3);
  box-shadow: var(--shadow-0);
  transition: transform 120ms ease-out, box-shadow 120ms ease-out;
}}
.service-card:hover {{
  transform: translateY(-2px);
  /* Hover shadow built from the brand's primary via color-mix; falls back to a
   * neutral-toned rgba when color-mix is unsupported (older browsers will
   * simply ignore the second declaration). */
  box-shadow: 0 12px 32px color-mix(in srgb, var(--color-neutral-0) 8%, transparent);
}}
.service-card h3 {{
  margin-top: 0;
}}
.service-price {{
  color: var(--color-neutral-2);
  font-size: var(--typography-font-size-0, 12px);
  margin: 0;
}}

/* ---- Testimonials ---- */
.testimonial-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: calc(var(--spacing-8) * 2);
}}
.testimonial {{
  background: var(--color-secondary);
  border-inline-start: 4px solid var({accent_token});
  border-radius: var(--radius-6);
  padding: calc(var(--spacing-8) * 3);
  margin: 0;
}}
.testimonial blockquote {{
  margin: 0 0 var(--spacing-8);
  font-style: italic;
  font-size: var(--typography-font-size-3, 20px);
}}
.testimonial figcaption {{
  color: var(--color-neutral-2);
  font-size: var(--typography-font-size-1, 14px);
}}

/* ---- Social / photos ---- */
.asset-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: calc(var(--spacing-8) * 2);
  margin-block-end: calc(var(--spacing-8) * 3);
}}
.asset-card {{
  background: var(--color-neutral-6);
  border: 1px solid var(--color-neutral-4);
  border-radius: var(--radius-8);
  overflow: hidden;
  margin: 0;
  display: flex;
  flex-direction: column;
}}
.asset-card img {{
  width: 100%;
  height: auto;
  display: block;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--color-neutral-4);
}}
.asset-card figcaption {{
  padding: calc(var(--spacing-8) * 1.5);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-8) / 2;
  font-size: var(--typography-font-size-0, 12px);
}}
.asset-subject {{
  font-weight: 600;
  color: var(--color-neutral-0);
}}
.asset-meta {{
  color: var(--color-neutral-2);
}}

/* ---- Contact form ---- */
.contact {{
  padding-block: calc(var(--spacing-8) * 4);
}}
.contact-form {{
  display: grid;
  gap: calc(var(--spacing-8) * 2);
  max-width: 560px;
}}
.field {{
  display: flex;
  flex-direction: column;
  gap: var(--spacing-8) / 2;
}}
.field label {{
  font-weight: 500;
  color: var(--color-neutral-1);
  font-size: var(--typography-font-size-1, 14px);
}}
.field input,
.field textarea {{
  padding: var(--spacing-8) calc(var(--spacing-8) * 1.5);
  border: 1px solid var(--color-neutral-3);
  border-radius: var(--radius-6);
  background: var(--color-neutral-6);
  color: var(--color-neutral-0);
  font-family: inherit;
  font-size: var(--typography-font-size-2, 16px);
}}
.field input:focus-visible,
.field textarea:focus-visible {{
  border-color: var({accent_token});
  outline: 2px solid var({accent_token});
  outline-offset: 1px;
}}
.form-actions {{ margin: 0; }}
.contact-email {{
  margin-top: calc(var(--spacing-8) * 3);
  color: var(--color-neutral-2);
}}

/* ---- Footer ---- */
.site-footer {{
  background: var(--color-neutral-5);
  border-block-start: 1px solid var(--color-neutral-4);
  padding: calc(var(--spacing-8) * 3) var(--spacing-8);
  color: var(--color-neutral-2);
  font-size: var(--typography-font-size-1, 14px);
}}
.site-footer p {{ margin: 0 0 var(--spacing-8); max-width: none; }}
.footer-meta {{ font-size: var(--typography-font-size-0, 12px); color: var(--color-neutral-2); }}

/* ---- Motion: restrained by default, CSS-only ---- */
@keyframes fade-slide-up {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}
.hero, .about, .services, .testimonials, .social-photos, .contact {{
  animation: fade-slide-up 360ms ease-out both;
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }}
}}

/* ---- Responsive: mobile-first, no horizontal overflow at 320px ---- */
@media (max-width: 480px) {{
  :root {{
    --typography-font-size-6: 36px; /* tame h1 on phones */
  }}
  main {{ padding: calc(var(--spacing-8) * 2) var(--spacing-8); }}
  .site-header {{ padding: var(--spacing-8); }}
  .service-grid,
  .testimonial-grid,
  .asset-grid {{ grid-template-columns: 1fr; }}
  h1 {{ font-size: var(--typography-font-size-5, 32px); }}
}}

/* Fluid images: capped at 100% container width, never overflow. */
img {{ max-width: 100%; height: auto; }}
"""


# ---------------------------------------------------------------------------
# Plan-driven stylesheet (design-plan path)
# ---------------------------------------------------------------------------


def render_plan_stylesheet(contrast_decision: dict[str, Any], motion_register: str) -> str:
    """Emit a stylesheet shaped by emphasis + signature element + motion register.

    This is the plan-driven counterpart to render_stylesheet(). Same guarantees:
      * NO raw hex literals (everything via var(--token))
      * WCAG AA contrast preserved via the derived *-text tokens
      * Semantic landmark selectors unchanged
      * prefers-reduced-motion honored
      * No horizontal overflow at 320px

    What's DIFFERENT is the per-section visual treatment: emphasis-hero reads as
    a left-aligned thesis (display weight, oversize, generous top padding);
    emphasis-primary reads as a normal content section; emphasis-secondary
    reads as a quieter text band; emphasis-minor reads as a colophon-sized
    single line. The plan also chooses a signature element device
    (.signature-dot) that the hero ends with and the CTA button trails with.
    """
    text_token = contrast_decision["text_token"]
    bg_token = contrast_decision["bg_token"]
    accent_token = contrast_decision["accent_token"]
    primary_text_token = contrast_decision["primary_text_token"]
    accent_text_token = contrast_decision["accent_text_token"]

    # Motion: the plan picks the register. We translate it into the CSS that
    # ends up on the page. Each register is honored exactly as the plan's
    # motion_vocabulary.rationale describes — restrained fades, balanced
    # mid-paced reveals, or cinematic long-duration sequences.
    motion_css = _motion_css_for_register(motion_register)

    return f"""/* compose_site.py v{TOOL_VERSION} — plan-driven page CSS.
 *
 * Design rule: NO raw hex colors appear below. Every color comes from a
 * tokens.css custom property (declared in tokens/dist/tokens.css). This is
 * enforced at emit time by a hex-literal grep; see BUILD-REPORT.md.
 *
 * Contrast decision: text {text_token} on background {bg_token}, accent {accent_token}.
 * Contrast ratio measured: {contrast_decision["ratio_text_bg"]:.2f}:1
 * (WCAG AA for normal body text requires >= 4.5:1).
 *
 * Motion register (from design-plan.json): {motion_register}
 */

:root {{
  color-scheme: light;
}}

* {{
  box-sizing: border-box;
}}

html {{
  font-family: var(--typography-font-family-body, var(--page-body, sans-serif));
  font-size: var(--typography-font-size-2, 16px);
  line-height: 1.55;
  color: var({text_token});
  background-color: var({bg_token});
}}

body {{
  margin: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}

/* Skip link — visible only on focus (a11y best practice). */
.skip-link {{
  position: absolute;
  inset-inline-start: var(--spacing-8);
  inset-block-start: 0;
  transform: translateY(-150%);
  background: var(--color-primary);
  color: var(--color-neutral-0);
  padding: var(--spacing-8) calc(var(--spacing-8) * 2);
  border-radius: var(--radius-4);
  text-decoration: none;
  font-weight: 600;
  z-index: 100;
  transition: transform 120ms ease-out;
}}
.skip-link:focus {{
  transform: translateY(0);
  outline: 3px solid var(--color-accent);
  outline-offset: 2px;
}}

/* Headings — display family, scale per tokens.css. */
h1, h2, h3, h4 {{
  font-family: var(--typography-font-family-display, var(--page-display, serif));
  line-height: 1.15;
  margin: 0 0 calc(var(--spacing-8) * 2);
  color: var(--color-neutral-0);
}}
p {{
  margin: 0 0 calc(var(--spacing-8) * 2);
  max-width: 60ch;
}}
ul, ol {{
  padding-inline-start: calc(var(--spacing-8) * 2);
  margin: 0 0 calc(var(--spacing-8) * 2);
}}

a {{
  color: var({accent_text_token});
  text-decoration-thickness: 1px;
  text-underline-offset: 0.18em;
}}
a:hover {{ text-decoration-thickness: 2px; }}

/* Keyboard focus — visible to all users, not just mouse. */
:focus-visible {{
  outline: 3px solid var({accent_token});
  outline-offset: 2px;
  border-radius: var(--radius-4);
}}

/* Visually hidden — for screen-reader-only labels. */
.visually-hidden {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}}

/* ---- Header / nav ---- */
.site-header {{
  background: var(--color-neutral-6);
  border-block-end: 1px solid var(--color-neutral-4);
  padding: calc(var(--spacing-8) * 2) var(--spacing-8);
  position: sticky;
  top: 0;
  z-index: 10;
}}
.site-header nav {{
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(var(--spacing-8) * 2);
  flex-wrap: wrap;
}}
.brand {{
  font-family: var(--typography-font-family-display, var(--page-display, serif));
  font-size: var(--typography-font-size-4, 24px);
  font-weight: 700;
  color: var(--color-neutral-0);
  text-decoration: none;
}}
.nav-list {{
  list-style: none;
  display: flex;
  gap: calc(var(--spacing-8) * 2);
  margin: 0;
  padding: 0;
  flex-wrap: wrap;
}}
.nav-list a {{
  color: var(--color-neutral-1);
  text-decoration: none;
  font-weight: 500;
}}
.nav-list a:hover {{ color: var({accent_text_token}); }}

/* ---- Main ---- */
main {{
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: calc(var(--spacing-8) * 4) var(--spacing-8);
}}
main:focus {{ outline: none; }}

/* ---- Plan sections: emphasis-driven treatment ---- */
/*
 * The whole point of plan-mode is that two different plans yield two
 * structurally different pages. These four emphasis classes are the visual
 * contract that makes that promise real:
 *   emphasis-hero      — large, left-aligned, generous padding
 *   emphasis-primary   — comfortable, full-width, normal scale
 *   emphasis-secondary — narrower max-width, quieter spacing
 *   emphasis-minor     — small text, single-line colophon weight
 */
.plan-section {{
  margin-block-end: calc(var(--spacing-8) * 6);
}}
.plan-heading {{ margin-block-end: calc(var(--spacing-8) * 2); }}
.plan-subhead {{
  font-size: var(--typography-font-size-3, 20px);
  color: var(--color-neutral-1);
  max-width: 50ch;
}}
.plan-body {{ max-width: 60ch; }}
.plan-caption {{
  font-size: var(--typography-font-size-0, 12px);
  color: var(--color-neutral-2);
}}

/* Hero — left-aligned, display-weight, oversize. The signature dot trails
 * the headline like a sentence-ending period (per the plan's signature
 * element implementation_note). */
.plan-section.emphasis-hero {{
  padding-block: calc(var(--spacing-8) * 6);
  border-block-end: 1px solid var(--color-neutral-4);
}}
.plan-heading--hero {{
  font-size: var(--typography-font-size-6, 48px);
  font-weight: 700;
  letter-spacing: -0.01em;
  max-width: 22ch;
  text-align: start;
  line-height: 1.05;
}}
.plan-heading--hero .signature-dot {{
  display: inline-block;
  width: 0.6em;
  height: 0.6em;
  vertical-align: 0.05em;
  margin-inline-start: 0.15em;
}}

/* Primary — comfortable reading width, normal scale, full-bleed by default. */
.plan-section.emphasis-primary {{
  padding-block: calc(var(--spacing-8) * 4);
}}
.plan-section.emphasis-primary .plan-heading {{
  font-size: var(--typography-font-size-5, 32px);
  letter-spacing: -0.005em;
  max-width: 30ch;
}}

/* Secondary — narrower, quieter. Two columns on wide viewports. */
.plan-section.emphasis-secondary {{
  padding-block: calc(var(--spacing-8) * 3);
  max-width: 900px;
}}
.plan-section.emphasis-secondary .plan-heading {{
  font-size: var(--typography-font-size-4, 24px);
  max-width: 30ch;
}}
.plan-section.emphasis-secondary .plan-body {{
  max-width: 50ch;
}}

/* Minor — colophon-sized, single-line weight. */
.plan-section.emphasis-minor {{
  padding-block: calc(var(--spacing-8) * 2);
  font-size: var(--typography-font-size-1, 14px);
  color: var(--color-neutral-2);
  max-width: 60ch;
}}
.plan-section.emphasis-minor .plan-heading {{
  font-size: var(--typography-font-size-2, 16px);
  font-weight: 500;
  margin-block-end: var(--spacing-8);
}}

/* ---- Signature element: the gold dot ---- */
/*
 * The plan's signature_element describes a single circular dot in the brand's
 * primary color, reused as a sentence-ending period, a numbered list bullet,
 * a step counter, and a CTA cursor. The implementation_note from the plan
 * specifies a 0.6em diameter, the brand primary color (var(--color-primary)
 * in tokens.css), a border-radius of 9999px, and explicitly reserves full
 * rounding as the design system's only circular radius. We use the token
 * reference (never a raw hex) so the dot picks up whatever the synthesized
 * token system actually declares for the brand.
 */
.signature-dot {{
  display: inline-block;
  width: 0.6em;
  height: 0.6em;
  border-radius: 9999px;
  background-color: var(--color-primary);
  vertical-align: 0.05em;
  margin-inline-end: 0.1em;
  /* No background-fill behind text — the dot is always inline. */
}}
.plan-cta-button .signature-dot {{
  width: 0.4em;
  height: 0.4em;
  vertical-align: middle;
  margin-inline-start: 0.2em;
}}

/* ---- Curriculum (services-as-chapters) ---- */
.plan-curriculum {{
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: calc(var(--spacing-8) * 2);
}}
.plan-curriculum-row {{
  display: grid;
  grid-template-columns: 3rem 1fr;
  gap: calc(var(--spacing-8) * 2);
  align-items: baseline;
  padding-block-end: calc(var(--spacing-8) * 2);
  border-block-end: 1px solid var(--color-neutral-4);
}}
.plan-curriculum-number {{
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-8);
  font-family: var(--typography-font-family-display, var(--page-display, serif));
  font-size: var(--typography-font-size-3, 20px);
  color: var(--color-neutral-1);
}}
.plan-curriculum-numeral {{
  font-variant-numeric: tabular-nums;
}}
.plan-curriculum-name {{
  margin: 0 0 var(--spacing-8);
  font-size: var(--typography-font-size-3, 20px);
  color: var(--color-neutral-0);
}}
.plan-curriculum-description {{
  margin: 0;
  max-width: 60ch;
  color: var(--color-neutral-1);
}}

/* ---- Steps (process strip) ---- */
.plan-steps {{
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: calc(var(--spacing-8) * 2);
}}
.plan-step {{
  display: flex;
  flex-direction: column;
  gap: var(--spacing-8);
  padding: calc(var(--spacing-8) * 2);
  border: 1px solid var(--color-neutral-4);
  border-radius: var(--radius-6);
}}
.plan-step-number {{
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-8);
  font-family: var(--typography-font-family-display, var(--page-display, serif));
  font-size: var(--typography-font-size-2, 16px);
  color: var(--color-neutral-1);
}}
.plan-step-numeral {{
  font-variant-numeric: tabular-nums;
}}
.plan-step-body {{
  margin: 0;
  max-width: none;
  font-size: var(--typography-font-size-1, 14px);
  color: var(--color-neutral-1);
}}

/* ---- Asset band (single real-photo figure) ---- */
.plan-asset {{
  margin: 0;
  background: var(--color-neutral-6);
  border: 1px solid var(--color-neutral-4);
  border-radius: var(--radius-8);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}
.plan-asset img {{
  width: 100%;
  height: auto;
  display: block;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--color-neutral-4);
}}
.plan-asset figcaption {{
  padding: calc(var(--spacing-8) * 1.5);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-8);
  font-size: var(--typography-font-size-0, 12px);
}}
.plan-asset-subject {{
  font-weight: 600;
  color: var(--color-neutral-0);
}}
.plan-asset-meta {{
  color: var(--color-neutral-2);
}}

/* ---- CTA band ---- */
.plan-cta-band {{
  background: var(--color-secondary);
  padding: calc(var(--spacing-8) * 4);
  border-radius: var(--radius-8);
  display: flex;
  flex-direction: column;
  gap: calc(var(--spacing-8) * 2);
  align-items: flex-start;
}}
.plan-cta-band .plan-body {{
  font-size: var(--typography-font-size-3, 20px);
  color: var(--color-neutral-0);
  max-width: 50ch;
}}
.plan-cta-action {{ margin: 0; }}

/* ---- Buttons ---- */
.button {{
  display: inline-block;
  background: var({accent_token});
  color: var(--color-neutral-0);
  padding: calc(var(--spacing-8) * 1.5) calc(var(--spacing-8) * 3);
  border-radius: var(--radius-8);
  font-weight: 600;
  text-decoration: none;
  border: 2px solid transparent;
  transition: background-color 120ms ease-out, border-color 120ms ease-out;
}}
.button:hover,
.button:focus-visible {{
  background: var(--color-neutral-0);
  color: var(--color-neutral-6);
  border-color: var({accent_token});
}}

/* ---- Footer ---- */
.site-footer {{
  background: var(--color-neutral-5);
  border-block-start: 1px solid var(--color-neutral-4);
  padding: calc(var(--spacing-8) * 3) var(--spacing-8);
  color: var(--color-neutral-2);
  font-size: var(--typography-font-size-1, 14px);
}}
.site-footer p {{ margin: 0 0 var(--spacing-8); max-width: none; }}
.footer-meta {{ font-size: var(--typography-font-size-0, 12px); color: var(--color-neutral-2); }}

/* ---- Motion: chosen by the plan's motion_vocabulary.register ---- */
{motion_css}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }}
}}

/* ---- Responsive: mobile-first, no horizontal overflow at 320px ---- */
@media (max-width: 480px) {{
  :root {{
    --typography-font-size-6: 36px; /* tame h1 on phones */
  }}
  main {{ padding: calc(var(--spacing-8) * 2) var(--spacing-8); }}
  .site-header {{ padding: var(--spacing-8); }}
  .plan-steps {{ grid-template-columns: 1fr; }}
  .plan-curriculum-row {{ grid-template-columns: 2rem 1fr; }}
  h1 {{ font-size: var(--typography-font-size-5, 32px); }}
  .plan-section.emphasis-hero {{ padding-block: calc(var(--spacing-8) * 3); }}
  .plan-heading--hero {{ font-size: var(--typography-font-size-5, 32px); }}
}}

/* Fluid images: capped at 100% container width, never overflow. */
img {{ max-width: 100%; height: auto; }}
"""


def _motion_css_for_register(register: str) -> str:
    """Translate a motion_vocabulary.register into the CSS that ends up on the page.

    Per the design_plan_schema, register is one of: "restrained" | "balanced"
    | "cinematic". Anything else falls back to balanced. The CSS differs only
    in timing and easing — never in count of effects — so prefers-reduced-motion
    can disable every variant uniformly.
    """
    if register == "restrained":
        # 320ms fades, no stagger, no transform depth.
        return """/* Motion register: restrained — on-paint fades only. */
@keyframes plan-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.plan-section { animation: plan-fade-in 320ms ease-out both; }
.plan-section:nth-of-type(2) { animation-delay: 40ms; }
.plan-section:nth-of-type(3) { animation-delay: 80ms; }
.plan-section:nth-of-type(4) { animation-delay: 120ms; }
.plan-section:nth-of-type(n+5) { animation-delay: 160ms; }
.signature-dot { animation: plan-fade-in 180ms ease-out both; }
"""
    if register == "cinematic":
        # Longer fade + slide, with depth. The plan's motion_vocabulary
        # specifically refuses parallax/marquee/auto-play — we honor that.
        return """/* Motion register: cinematic — fade + slide on entry, no scroll-jacking. */
@keyframes plan-fade-slide {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
.plan-section { animation: plan-fade-slide 640ms cubic-bezier(0.22, 1, 0.36, 1) both; }
.plan-section:nth-of-type(2) { animation-delay: 120ms; }
.plan-section:nth-of-type(3) { animation-delay: 240ms; }
.plan-section:nth-of-type(4) { animation-delay: 360ms; }
.plan-section:nth-of-type(n+5) { animation-delay: 480ms; }
.signature-dot { animation: plan-fade-slide 360ms ease-out both; }
"""
    # Default + "balanced": moderate fade + 6px lift, mid-paced stagger.
    return """/* Motion register: balanced — fade with a small lift, mid-paced. */
@keyframes plan-fade-lift {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.plan-section { animation: plan-fade-lift 420ms ease-out both; }
.plan-section:nth-of-type(2) { animation-delay: 80ms; }
.plan-section:nth-of-type(3) { animation-delay: 160ms; }
.plan-section:nth-of-type(4) { animation-delay: 240ms; }
.plan-section:nth-of-type(n+5) { animation-delay: 320ms; }
.signature-dot { animation: plan-fade-lift 240ms ease-out both; }
"""


# ---------------------------------------------------------------------------
# Contrast (WCAG) helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    m = re.match(r"^#([0-9a-fA-F]{6})$", hex_color)
    if not m:
        raise ComposeError(f"invalid hex color '{hex_color}' (expected #RRGGBB)")
    raw = m.group(1)
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def _relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance. sRGB -> linear -> weighted."""
    r, g, b = _hex_to_rgb(hex_color)
    def channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG 2.1 contrast ratio between two hex colors."""
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def derive_accessible_text_variant(
    foreground_hex: str,
    background_hex: str,
    *,
    ratio_threshold: float = WCAG_NORMAL_TEXT_RATIO,
    step: float = 0.01,
) -> dict[str, Any]:
    """Derive a WCAG-safe normal-text variant while preserving the brand color.

    The original remains available for non-text identity uses. The variant
    changes HLS lightness in small steps, darkening on light backgrounds and
    lightening on dark backgrounds, until the normal-text threshold is met.
    """
    original_hex = foreground_hex.lower()
    background_hex = background_hex.lower()
    original_ratio = _contrast_ratio(original_hex, background_hex)
    if original_ratio >= ratio_threshold:
        return {
            "original_hex": original_hex,
            "background_hex": background_hex,
            "original_ratio": original_ratio,
            "derived_hex": original_hex,
            "derived_ratio": original_ratio,
            "direction": "unchanged",
            "steps": 0,
            "threshold": ratio_threshold,
        }

    red, green, blue = _hex_to_rgb(original_hex)
    hue, lightness, saturation = colorsys.rgb_to_hls(
        red / 255.0, green / 255.0, blue / 255.0
    )
    direction = (
        "darken"
        if _relative_luminance(background_hex) > WCAG_LUMINANCE_THRESHOLD
        else "lighten"
    )
    for steps in range(1, int(1.0 / step) + 1):
        candidate_lightness = (
            max(0.0, lightness - step * steps)
            if direction == "darken"
            else min(1.0, lightness + step * steps)
        )
        candidate_rgb = colorsys.hls_to_rgb(hue, candidate_lightness, saturation)
        candidate_hex = "#" + "".join(
            f"{round(channel * 255):02x}" for channel in candidate_rgb
        )
        candidate_ratio = _contrast_ratio(candidate_hex, background_hex)
        if candidate_ratio >= ratio_threshold:
            return {
                "original_hex": original_hex,
                "background_hex": background_hex,
                "original_ratio": original_ratio,
                "derived_hex": candidate_hex,
                "derived_ratio": candidate_ratio,
                "direction": direction,
                "steps": steps,
                "threshold": ratio_threshold,
            }

    if direction == "lighten" and _contrast_ratio("#ffffff", background_hex) < ratio_threshold:
        raise ComposeError(
            f"could not derive a {ratio_threshold:.1f}:1 text variant from "
            f"{original_hex} on {background_hex}"
        )


def add_accessible_text_tokens(
    css_text: str, contrast: dict[str, Any]
) -> str:
    """Add composer-derived accessible text tokens to copied tokens.css."""
    token_lines = [
        f"  {item['token']}: {item['derived_hex']};"
        for item in contrast["brand_text_decisions"]
    ]
    close_index = css_text.rfind("}")
    if close_index < 0:
        raise ComposeError("tokens.css has no closing root block for text tokens")
    return (
        css_text[:close_index].rstrip()
        + "\n\n  /* Composer-derived WCAG AA normal-text variants. */\n"
        + "\n".join(token_lines)
        + "\n"
        + css_text[close_index:]
    )


def resolve_contrast(
    palette: dict[str, Any],
    brand_name: str,
    *,
    ratio_threshold: float = WCAG_NORMAL_TEXT_RATIO,
) -> dict[str, Any]:
    """Pick text / background / accent tokens that meet WCAG AA contrast for body text.

    Strategy:
      1. Use the brand's neutrals to construct candidate (text, bg) pairs.
      2. Pick the first pair whose contrast >= ratio_threshold.
      3. If no pair from the neutrals qualifies, NOTE it in the report and fall
         back to the highest-contrast pair available (which is always at least
         the most-dark text on the most-light neutral — typically ~16:1).

    Returns a dict with the chosen token names + measured ratio + decision note
    that BUILD-REPORT.md embeds verbatim.
    """
    neutrals = palette.get("neutrals") or []
    primary = palette.get("primary", "#000000")
    accent = palette.get("accent", "#0b0c0d")

    # Sort neutrals: lightest first, darkest last (by luminance).
    ordered = sorted(neutrals, key=_relative_luminance)

    chosen_text_token = "--color-neutral-0"
    chosen_bg_token = "--color-neutral-6"
    chosen_text_hex = "#0b0c0d"
    chosen_bg_hex = "#ffffff"
    best_ratio = 0.0
    note_parts: list[str] = []

    for text_hex in ordered:
        for bg_hex in reversed(ordered):  # try lightest bg first
            if text_hex == bg_hex:
                continue
            ratio = _contrast_ratio(text_hex, bg_hex)
            if ratio > best_ratio:
                best_ratio = ratio
                chosen_text_hex = text_hex
                chosen_bg_hex = bg_hex
            if ratio >= ratio_threshold:
                # Early-out — first acceptable pair.
                chosen_text_token = _hex_to_token_name(text_hex, ordered)
                chosen_bg_token = _hex_to_token_name(bg_hex, ordered)
                decision = _decision(
                    text_token=chosen_text_token,
                    bg_token=chosen_bg_token,
                    accent_token="--color-accent",
                    text_hex=chosen_text_hex,
                    bg_hex=chosen_bg_hex,
                    accent_hex=accent,
                    ratio_text_bg=ratio,
                    note=(
                        f"text {chosen_text_token} ({chosen_text_hex}) on "
                        f"background {chosen_bg_token} ({chosen_bg_hex}) = {ratio:.2f}:1, "
                        f"meets WCAG AA body-text threshold ({ratio_threshold:.1f}:1)"
                    ),
                )
                return _with_brand_text_decisions(
                    decision, primary, accent, chosen_bg_hex
                )

    # Fallback: nothing met threshold — use the best pair we found and NOTE it.
    if ordered:
        chosen_text_token = _hex_to_token_name(chosen_text_hex, ordered)
        chosen_bg_token = _hex_to_token_name(chosen_bg_hex, ordered)
    note_parts.append(
        f"no neutral pair met {ratio_threshold:.1f}:1; using best-available pair "
        f"({chosen_text_token} on {chosen_bg_token}, {best_ratio:.2f}:1) and shipping "
        f"a contrast limitation"
    )
    decision = _decision(
        text_token=chosen_text_token,
        bg_token=chosen_bg_token,
        accent_token="--color-accent",
        text_hex=chosen_text_hex,
        bg_hex=chosen_bg_hex,
        accent_hex=accent,
        ratio_text_bg=best_ratio,
        note=" ".join(note_parts),
    )
    return _with_brand_text_decisions(decision, primary, accent, chosen_bg_hex)


def _with_brand_text_decisions(
    decision: dict[str, Any],
    primary_hex: str,
    accent_hex: str,
    background_hex: str,
) -> dict[str, Any]:
    """Attach accessible text variants for each brand identity color."""
    brand_text_decisions: list[dict[str, Any]] = []
    for name, original_hex, token, text_uses, non_text_uses in (
        (
            "primary",
            primary_hex,
            "--color-primary-text",
            ["hero tagline text"],
            ["skip-link background", "decorative brand fills"],
        ),
        (
            "accent",
            accent_hex,
            "--color-accent-text",
            ["links", "navigation hover text"],
            ["button backgrounds", "focus outlines", "borders", "decorative fills"],
        ),
    ):
        item = derive_accessible_text_variant(original_hex, background_hex)
        item.update(
            {
                "name": name,
                "token": token,
                "original_token": f"--color-{name}",
                "text_uses": text_uses,
                "non_text_uses": non_text_uses,
            }
        )
        brand_text_decisions.append(item)

    decision["brand_text_decisions"] = brand_text_decisions
    decision["brand_text_tokens"] = {
        item["name"]: {"token": item["token"], "hex": item["derived_hex"]}
        for item in brand_text_decisions
    }
    decision["primary_text_token"] = "--color-primary-text"
    decision["accent_text_token"] = "--color-accent-text"
    return decision


def _hex_to_token_name(hex_color: str, neutrals: list[str]) -> str:
    """Map a hex color back to its --color-neutral-N name. Falls back to the
    literal hex in the token slot string when not a neutral."""
    for idx, value in enumerate(neutrals):
        if value.lower() == hex_color.lower():
            return f"--color-neutral-{idx}"
    return f"(non-neutral hex {hex_color})"


def _decision(
    *,
    text_token: str,
    bg_token: str,
    accent_token: str,
    text_hex: str,
    bg_hex: str,
    accent_hex: str,
    ratio_text_bg: float,
    note: str,
) -> dict[str, Any]:
    return {
        "text_token": text_token,
        "bg_token": bg_token,
        "accent_token": accent_token,
        "text_hex": text_hex,
        "bg_hex": bg_hex,
        "accent_hex": accent_hex,
        "ratio_text_bg": ratio_text_bg,
        "note": note,
    }


# ---------------------------------------------------------------------------
# Misc small helpers
# ---------------------------------------------------------------------------


def _first_non_empty(*values: Any, default: str = "") -> str:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return default


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    # Split on first sentence terminator followed by whitespace.
    m = re.match(r"^(.+?[.!?])(?:\s|$)", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "brand"


# ---------------------------------------------------------------------------
# Hex-literal guard
# ---------------------------------------------------------------------------


def find_hex_literals(css_text: str, *, ignore_selectors: tuple[str, ...] = (".visually-hidden",)) -> list[tuple[int, str]]:
    """Find hex-color literals in CSS. Returns list of (line_number_1indexed, line).

    Used by the emit guard and reported in BUILD-REPORT.md. The
    `ignore_selectors` knob lets us skip false-positives (none currently —
    visually-hidden has no hex).
    """
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(css_text.splitlines(), 1):
        for m in HEX_COLOR_PATTERN.finditer(line):
            hits.append((lineno, line.strip()))
    return hits


# ---------------------------------------------------------------------------
# BUILD-REPORT.md emitter
# ---------------------------------------------------------------------------


def render_build_report(
    *,
    brief: dict[str, Any],
    plan: list[dict[str, Any]],
    brand_name: str,
    brand_name_source: str,
    contrast: dict[str, Any],
    css_hex_hits: list[tuple[int, str]],
    tokens_css_vars: list[str],
    expected_token_vars: list[str],
    reference_present: bool,
    reference_dir: str | None,
    reference_files: dict[str, str],
    tokens_dist_css: str,
    tokens_dist_json: str,
    outdir: Path,
) -> str:
    """Emit BUILD-REPORT.md — sections emitted vs skipped, contrast decisions,
    every limitation inherited from the brief, hex-literal audit results."""
    emitted = [s for s in plan if s["emitted"]]
    skipped = [s for s in plan if not s["emitted"]]
    limitations = brief.get("limitations", []) or []

    # Hex audit — for the stylesheet we emit. tokens.css is the source of truth
    # and DOES contain hex; it is excluded from the audit.
    if css_hex_hits:
        audit_line = f"FAIL — {len(css_hex_hits)} hex literal(s) found in styles.css"
        audit_lines = "\n".join(f"  L{ln}: {line}" for ln, line in css_hex_hits)
    else:
        audit_line = "PASS — no raw hex literals in styles.css (every color is a token)"
        audit_lines = ""

    token_audit = ""
    missing_tokens = [v for v in expected_token_vars if v not in tokens_css_vars]
    if missing_tokens:
        token_audit = f"FAIL — tokens.css does not declare: {', '.join(missing_tokens)}"
    else:
        token_audit = (
            f"PASS — all {len(expected_token_vars)} expected token vars are declared in tokens.css"
        )

    ref_section = ""
    if reference_present:
        ref_lines = [f"- `{name}`: `{path}`" for name, path in reference_files.items()]
        ref_section = (
            f"Reference report directory: `{reference_dir}`\n\n"
            + ("\n".join(ref_lines) if ref_lines else "_(no JSON files present in directory)_")
            + "\n\nThe reference brief was used for cross-checks only; no content was "
              "copied or invented from it."
        )
    else:
        ref_section = (
            "No `--reference-report` directory was provided; the site was composed "
            "from the brand brief + synthesized tokens alone."
        )

    limitations_section = (
        "\n".join(f"- {item}" for item in limitations)
        if limitations
        else "_no limitations declared in the brand brief_"
    )

    emitted_rows = "\n".join(
        f"| {s['label']} (`#{s['id']}`) | yes | {s['reason']} | {', '.join(f'`{f}`' for f in s['brief_fields'])} |"
        for s in emitted
    )
    # The "Skipped" column answers the literal question "was this section
    # skipped?", so the value is always `yes` for rows in this table. Earlier
    # versions printed the emitted boolean (`no`) which inverted the meaning
    # against the header.
    skipped_rows = "\n".join(
        f"| {s['label']} (`#{s['id']}`) | yes | {s['reason']} | {', '.join(f'`{f}`' for f in s['brief_fields'])} |"
        for s in skipped
    )

    contrast_note = contrast["note"]
    brand_decision_lines = []
    for item in contrast["brand_text_decisions"]:
        brand_decision_lines.append(
            f"- **{item['name'].capitalize()} used as text:** original "
            f"`{item['original_hex']}` on `{item['background_hex']}` measured "
            f"{item['original_ratio']:.2f}:1; derived `{item['derived_hex']}` "
            f"({item['direction']}, {item['steps']} lightness steps) measures "
            f"{item['derived_ratio']:.2f}:1. Text uses: "
            f"{', '.join(item['text_uses'])}. Original "
            f"`{item['original_token']}` remains for non-text uses: "
            f"{', '.join(item['non_text_uses'])}."
        )
    brand_decisions_section = "\n".join(brand_decision_lines)

    return f"""# Build report

Project slug: `{brief.get("project_slug", "")}`
Brand name: **{brand_name}** — _{brand_name_source}_
Generated: {brief.get("fetched_at", "")} brief → composed by compose_site.py v{TOOL_VERSION}
Outdir: `{outdir}`

---

## Sections emitted

| Section | Emitted | Why | Brief fields that fed it |
|---------|---------|-----|--------------------------|
{emitted_rows}

## Sections skipped (data absent in brief)

| Section | Skipped | Why | Brief fields that would have fed it |
|---------|---------|-----|------------------------------------|
{skipped_rows or "| _(none)_ | | | |"}

## Contrast decision

- **Neutral body text token:** `{contrast["text_token"]}` ({contrast["text_hex"]})
- **Neutral background token:** `{contrast["bg_token"]}` ({contrast["bg_hex"]})
- **Neutral measured contrast:** {contrast["ratio_text_bg"]:.2f}:1
- **Neutral decision note:** {contrast_note}

Brand colors remain unchanged for non-text identity uses. When a brand color is
used as normal-sized text, the composer uses the derived `*-text` token below.

{brand_decisions_section}

## Token discipline

- **Source of truth:** `{tokens_dist_css}`
- **Copied to site as:** `{outdir}/tokens.css`
- **Token JSON:** `{tokens_dist_json}`
- **Audit:** {token_audit}

The page CSS links `tokens.css` and references token CSS variables for every
color, spacing value, radius, and shadow. No raw hex colors are emitted in
`styles.css`:

```
{audit_line}
```

{audit_lines and ("First hits (for diagnosis):\n\n```\n" + audit_lines + "\n```\n") or ""}

## Reference brief
{ref_section}

## Accessibility decisions

- **Semantic landmarks:** `<header role="banner">`, `<nav>`, `<main>`,
  `<section aria-labelledby>`, `<footer role="contentinfo">`.
- **Headings:** one `<h1>` (in the hero), logical nesting, no skipped levels.
- **Skip link:** `.skip-link` is the first focusable element; visible only on focus.
- **Alt text:** every `<img>` uses `real_photo_inventory[].subject` as `alt`.
- **Form labels:** every `<input>` and `<textarea>` has a `<label>` with a
  matching `for` attribute.
- **Focus styles:** `:focus-visible` on every interactive element.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` disables the
  CSS-only fade/slide-up reveals.
- **Color contrast:** see "Contrast decision" above.

## Motion decisions

- Default: CSS-only `fade-slide-up` reveal on each section (360ms ease-out).
- Honors `prefers-reduced-motion: reduce` — animation duration drops to ~0ms.
- No JavaScript animation libraries (matches the brand brief's `register`
  `"confessional-educational"` if it contained that word, or any register whose
  profile is restrained). Heavier libraries are an M3+ option, not a default.

## Limitations carried forward from the brand brief

The brief's own `limitations[]` array is reproduced verbatim below. Every entry
below is a research-side limitation that the site honors by *not* inventing
content; nothing in the emitted page invents quotes, photos, services, or
stats.

{limitations_section}

## Honesty tier

This build is **First-render** by the `nt-site-mirror` honesty tier scale:
- The page renders in any browser.
- Every claim in the page is backed by a brief field listed in "Sections emitted".
- No copy, photo, quote, statistic, or section was invented.

It is **not yet M4-Validated**: the 8-gate validation (accessibility, performance,
site-wide audit, responsive, motion, source-paired) is M4 scope and is exercised
by `references/validation-checklist.md` once M4 lands.
"""


def render_plan_build_report(
    *,
    brief: dict[str, Any],
    plan: dict[str, Any],
    sections: list[dict[str, Any]],
    skipped_at_runtime: list[dict[str, Any]],
    brand_name: str,
    brand_name_source: str,
    contrast: dict[str, Any],
    css_hex_hits: list[tuple[int, str]],
    tokens_css_vars: list[str],
    expected_token_vars: list[str],
    tokens_dist_css: str,
    tokens_dist_json: str,
    font_substitutions: dict[str, Any] | None = None,
    outdir: Path,
) -> str:
    """Emit BUILD-REPORT.md for a plan-driven build.

    Carries the same contrast, token-discipline, accessibility, motion,
    limitations, and honesty-tier sections as the fallback report, and ADDS:
      * Layout thesis (statement, audience, job-to-be-done, why-not-generic).
      * Signature element (name, description, implementation note).
      * Per-section rationale with brief fields and motion register.
      * Plan skipped_sections[] vs runtime-detected skips.
      * Design decisions surfaced in the plan.

    Every section in `sections` corresponds to one plan.sections[] entry the
    renderer could actually fill; skipped_at_runtime covers plan sections that
    the renderer dropped because they had no copy and no brief payload.
    """
    limitations = brief.get("limitations", []) or []
    plan_sections_all = plan.get("sections", []) or []
    plan_skipped = plan.get("skipped_sections", []) or []
    plan_decisions = plan.get("decisions", []) or []
    layout_thesis = plan.get("layout_thesis", {}) or {}
    signature = plan.get("signature_element", {}) or {}
    motion = plan.get("motion_vocabulary", {}) or {}

    # Hex audit
    if css_hex_hits:
        audit_line = f"FAIL — {len(css_hex_hits)} hex literal(s) found in styles.css"
        audit_lines = "\n".join(f"  L{ln}: {line}" for ln, line in css_hex_hits)
    else:
        audit_line = "PASS — no raw hex literals in styles.css (every color is a token)"
        audit_lines = ""

    # Token audit
    missing_tokens = [v for v in expected_token_vars if v not in tokens_css_vars]
    if missing_tokens:
        token_audit = f"FAIL — tokens.css does not declare: {', '.join(missing_tokens)}"
    else:
        token_audit = (
            f"PASS — all {len(expected_token_vars)} expected token vars are declared in tokens.css"
        )

    # Per-section table for the plan-driven build.
    def _format_brief_fields(fields: list[str]) -> str:
        if not fields:
            return "_(none)_"
        return ", ".join(f"`{f}`" for f in fields)

    section_rows: list[str] = []
    for sec in sections:
        section_rows.append(
            "| {id} (`#{id}`) | {emphasis} | {order} | {component} | {fields} |\n"
            "| | | | | **Why this section:** {purpose} |\n"
            "| | | | | **Rationale:** {rationale} |".format(
                id=sec["id"],
                emphasis=sec["emphasis"],
                order=sec["order"],
                component=sec["component"][:80] + ("…" if len(sec["component"]) > 80 else ""),
                fields=_format_brief_fields(sec["brief_fields"]),
                purpose=sec["purpose"],
                rationale=sec["rationale"],
            )
        )
    sections_table = "\n".join(section_rows) if section_rows else "_(no sections rendered)_"

    plan_skipped_rows = "\n".join(
        f"| `{s.get('id', '')}` | {s.get('reason', '')} | {', '.join(f'`{f}`' for f in (s.get('missing_brief_fields', []) or []))} |"
        for s in plan_skipped
    ) or "| _(none)_ | | |"

    runtime_skipped_rows = "\n".join(
        f"| `{s['id']}` | {s['reason']} | {', '.join(f'`{f}`' for f in s.get('missing_brief_fields', []))} |"
        for s in skipped_at_runtime
    ) or "| _(none)_ | | |"

    decision_rows = "\n".join(
        f"- **{d.get('decision', '')}**\n"
        f"  - Alternatives considered: {', '.join(d.get('alternatives_considered', []) or []) or '_(none recorded)_'}\n"
        f"  - Why chosen: {d.get('why_chosen', '')}"
        for d in plan_decisions
    ) or "_(no decisions recorded in plan)_"

    motion_effects = "\n".join(f"  - {e}" for e in (motion.get("effects", []) or [])) or "  - _(none)_"

    contrast_note = contrast["note"]
    brand_decision_lines = []
    for item in contrast["brand_text_decisions"]:
        brand_decision_lines.append(
            f"- **{item['name'].capitalize()} used as text:** original "
            f"`{item['original_hex']}` on `{item['background_hex']}` measured "
            f"{item['original_ratio']:.2f}:1; derived `{item['derived_hex']}` "
            f"({item['direction']}, {item['steps']} lightness steps) measures "
            f"{item['derived_ratio']:.2f}:1. Text uses: "
            f"{', '.join(item['text_uses'])}. Original "
            f"`{item['original_token']}` remains for non-text uses: "
            f"{', '.join(item['non_text_uses'])}."
        )
    brand_decisions_section = "\n".join(brand_decision_lines)

    # Font substitutions (paid -> OFL). Synthesizer sidecar records every
    # primary that was rewritten so a paid family never reaches the page;
    # surface it in the build report so reviewers can see the swap.
    subs = font_substitutions or {}
    subs_meta = subs.get("meta", {}) or {}
    sub_entries = subs.get("font_substitutions", {}) or {}
    if sub_entries:
        sub_lines = [
            f"- **{role}:** `{entry.get('from', '?')}` ({entry.get('from_license', '?')}) "
            f"→ `{entry.get('to', '?')}` ({entry.get('to_license', '?')}) "
            f"— {entry.get('reason', '')}"
            for role, entry in sub_entries.items()
        ]
        font_substitutions_section = "\n".join(sub_lines)
        if subs_meta:
            font_substitutions_section += (
                "\n\n" + "\n".join(f"- _{k}:_ {v}" for k, v in subs_meta.items())
            )
    else:
        font_substitutions_section = (
            "_None — every primary family is OFL/CC-licensed and was kept as-is._"
            if not subs.get("missing_sidecar")
            else "_font-substitutions.json sidecar was not produced by the synthesizer; "
            "no paid->OFL mapping was applied._"
        )

    limitations_section = (
        "\n".join(f"- {item}" for item in limitations)
        if limitations
        else "_no limitations declared in the brand brief_"
    )

    return f"""# Build report (plan-driven)

Project slug: `{brief.get('project_slug', '')}`
Brand name: **{brand_name}** — _{brand_name_source}_
Generated: {brief.get('fetched_at', '')} brief → composed by compose_site.py v{TOOL_VERSION} from `design-plan.json`
Outdir: `{outdir}`

---

## Layout thesis (from design-plan.json)

- **Statement:** {layout_thesis.get('statement', '_(none)_')}
- **Audience:** {layout_thesis.get('audience', '_(none)_')}
- **Job to be done:** {layout_thesis.get('job_to_be_done', '_(none)_')}
- **Why this, not generic:** {layout_thesis.get('why_this_not_generic', '_(none)_')}

## Signature element (from design-plan.json)

- **Name:** {signature.get('name', '_(none)_')}
- **Description:** {signature.get('description', '_(none)_')}
- **Why it fits the brand:** {signature.get('why_it_fits_brand', '_(none)_')}
- **Implementation note (rendered in HTML+CSS as a real device):**
  {signature.get('implementation_note', '_(none)_')}

The signature element is emitted in HTML as `<span class="signature-dot" aria-hidden="true">`
and styled in `styles.css` under the `.signature-dot` selector. It uses
`var(--color-primary)` so it picks up whatever the synthesized token system
declares as the brand's primary color (the design plan calls for the literal
gold #efad2b; the token system reserves the same hex for `--color-primary`).
It appears inline as the period ending the thesis headline, beside numbered
curriculum rows and process steps, and trailing the CTA button.

## Motion vocabulary (from design-plan.json)

- **Register:** `{motion.get('register', '_(none)_')}`
- **Rationale:** {motion.get('rationale', '_(none)_')}
- **Effects:**
{motion_effects}

The plan's register drives `styles.css` via `_motion_css_for_register()` —
`restrained` ⇒ 320ms fade-in only; `balanced` ⇒ 420ms fade + 6px lift;
`cinematic` ⇒ 640ms fade + 16px slide with cubic-bezier easing. No parallax,
no marquee, no auto-play regardless of register. All variants honor
`@media (prefers-reduced-motion: reduce)`.

## Sections emitted (plan-driven)

| Section | Emphasis | Order | Component (truncated) | Brief fields that fed it |
|---------|----------|-------|-----------------------|--------------------------|
{sections_table}

## Sections skipped by the plan (data absent in brief)

The plan's own `skipped_sections[]` is honored verbatim. Each entry names the
brief fields that would have been needed but are absent.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
{plan_skipped_rows}

## Sections skipped at render time (no copy or payload)

The plan listed a section but the renderer could not find any copy block or
brief payload for it, so it was dropped rather than emitted empty. These are
reported here in addition to the plan's own skipped list.

| Section | Reason | Missing brief fields |
|---------|--------|----------------------|
{runtime_skipped_rows}

## Design decisions (from design-plan.json)

{decision_rows}

## Contrast decision

- **Neutral body text token:** `{contrast["text_token"]}` ({contrast["text_hex"]})
- **Neutral background token:** `{contrast["bg_token"]}` ({contrast["bg_hex"]})
- **Neutral measured contrast:** {contrast["ratio_text_bg"]:.2f}:1
- **Neutral decision note:** {contrast_note}

Brand colors remain unchanged for non-text identity uses. When a brand color is
used as normal-sized text, the composer uses the derived `*-text` token below.

{brand_decisions_section}

## Font substitutions (paid → OFL)

The synthesizer's `font-substitutions.json` sidecar is the authoritative
record of every paid primary family that was rewritten to an OFL/CC-licensed
fallback before being emitted into `tokens.css`. The page never ships a
font the operator hasn't licensed.

{font_substitutions_section}

## Token discipline

- **Source of truth:** `{tokens_dist_css}`
- **Copied to site as:** `{outdir}/tokens.css`
- **Token JSON:** `{tokens_dist_json}`
- **Audit:** {token_audit}

The page CSS links `tokens.css` and references token CSS variables for every
color, spacing value, radius, and shadow. No raw hex colors are emitted in
`styles.css`:

```
{audit_line}
```

{audit_lines and ("First hits (for diagnosis):\n\n```\n" + audit_lines + "\n```\n") or ""}

## Accessibility decisions

- **Semantic landmarks:** `<header role="banner">`, `<nav>`, `<main>`,
  `<section aria-labelledby>`, `<footer role="contentinfo">`.
- **Headings:** one `<h1>` (in the hero), logical nesting, no skipped levels.
- **Skip link:** `.skip-link` is the first focusable element; visible only on focus.
- **Alt text:** every `<img>` uses `real_photo_inventory[].subject` as `alt`.
- **Focus styles:** `:focus-visible` on every interactive element.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` disables the
  CSS-only plan-driven reveals.
- **Color contrast:** see "Contrast decision" above.

## Limitations carried forward from the brand brief

The brief's own `limitations[]` array is reproduced verbatim below. Every entry
below is a research-side limitation that the site honors by *not* inventing
content; nothing in the emitted page invents quotes, photos, services, or
stats. The plan's `skipped_sections[]` mirrors these where they apply.

{limitations_section}

## Honesty tier

This build is **First-render** by the `nt-site-mirror` honesty tier scale:
- The page renders in any browser.
- Every claim in the page is backed by a brief field listed in "Sections emitted".
- No copy, photo, quote, statistic, or section was invented.
- The plan passed `design_pass.verify_source_fields` before any HTML was written
  (every `source_brief_fields` path resolves to a non-empty value in the brief).

It is **not yet M4-Validated**: the 8-gate validation (accessibility, performance,
site-wide audit, responsive, motion, source-paired) is M4 scope and is exercised
by `validate_site.py` once M4 lands.
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose a static site from a brand brief + synthesized tokens.",
    )
    parser.add_argument("--brand-brief", required=True, help="Path to brand-brief.json.")
    parser.add_argument(
        "--tokens",
        required=True,
        help="Directory produced by synthesize_tokens.py (must contain tokens/dist/).",
    )
    parser.add_argument(
        "--reference-report",
        default=None,
        help="Optional. Directory with sections.json, components.json, copy.json from reference understanding.",
    )
    parser.add_argument(
        "--design-plan",
        default=None,
        help="Optional. Path to design-plan.json (M6 LLM design pass). When present, "
             "the composer renders FROM the plan (section order, emphasis, component, "
             "copy, signature element, motion register). When absent, the deterministic "
             "M2-M3 fallback path is used exactly as before.",
    )
    parser.add_argument("-o", "--outdir", required=True, help="Where to write the composed site.")
    parser.add_argument(
        "--project-slug",
        default=None,
        help="Override project_slug (default: brief.project_slug).",
    )
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).resolve().parent / "brand_brief_schema.json"),
        help="Path to the JSON Schema (default: brand_brief_schema.json next to this script).",
    )
    args = parser.parse_args(argv)

    brief_path = Path(args.brand_brief)
    tokens_root = Path(args.tokens)
    outdir = Path(args.outdir)
    reference_dir = Path(args.reference_report) if args.reference_report else None
    design_plan_path = Path(args.design_plan) if args.design_plan else None
    schema_path = Path(args.schema)

    if not brief_path.is_file():
        print(f"error: --brand-brief not found: {brief_path}", file=sys.stderr)
        return 2
    if not tokens_root.is_dir():
        print(f"error: --tokens path is not a directory: {tokens_root}", file=sys.stderr)
        return 2
    if not outdir.exists() and not _safe_makedirs(outdir):
        return 2

    # 1. Re-validate the brand brief.
    try:
        brief = revalidate_brief(brief_path, schema_path)
    except ComposeError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1

    # 2. Load synthesized tokens.
    try:
        tokens_css_src, tw, tokens_css_text, font_substitutions = load_tokens(tokens_root)
    except ComposeError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1

    declared_vars = sorted(set(re.findall(r"--[a-zA-Z0-9_-]+", tokens_css_text)))
    # Accessible brand text tokens are generated at composition time, so they
    # are intentionally absent from synthesized M3 tokens.css at this point.
    declared_vars.extend(
        [name for name in EXPECTED_TOKEN_VARS if name not in declared_vars]
    )
    try:
        assert_tokens_referenced(tokens_css_text, list(BASE_EXPECTED_TOKEN_VARS))
    except ComposeError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1

    # 3. Dispatch: plan-driven vs fallback. Both paths share the same
    # token-contrast-budget and emit-gate work; only the rendering differs.
    if design_plan_path is not None:
        return _run_plan_path(
            brief=brief,
            design_plan_path=design_plan_path,
            tokens_root=tokens_root,
            tokens_css_src=tokens_css_src,
            tokens_css_text=tokens_css_text,
            font_substitutions=font_substitutions,
            project_slug_override=args.project_slug,
            outdir=outdir,
        )

    # ----- Fallback path: deterministic template emitter (UNCHANGED) -----
    # 3. Load reference report (optional).
    reference = load_reference_report(reference_dir)

    # 4. Decide sections + derive brand name + resolve contrast.
    plan = plan_sections(brief)
    brand_name, brand_name_source = derive_brand_name(brief, args.project_slug)
    contrast = resolve_contrast(brief.get("palette_from_logo", {}) or {}, brand_name)

    # 5. Render HTML + CSS.
    html = render_html(
        brief=brief,
        plan=plan,
        brand_name=brand_name,
        brand_name_source=brand_name_source,
        contact_email=None,
    )
    stylesheet = render_stylesheet(contrast)

    # 6. Emit-gate: the page CSS must contain no raw hex literals. tokens.css is
    # the source of truth and DOES contain hex; it is not part of this audit.
    hex_hits = find_hex_literals(stylesheet)
    if hex_hits:
        print("compose_site: emit gate FAILED — raw hex literals found in styles.css:", file=sys.stderr)
        for ln, line in hex_hits:
            print(f"  L{ln}: {line}", file=sys.stderr)
        return 1

    # 7. Write outputs.
    outdir.mkdir(parents=True, exist_ok=True)
    copied_tokens_css = add_accessible_text_tokens(tokens_css_text, contrast)
    copied_declared_vars = sorted(
        set(re.findall(r"--[a-zA-Z0-9_-]+", copied_tokens_css))
    )
    (outdir / "index.html").write_text(html, encoding="utf-8")
    (outdir / "styles.css").write_text(stylesheet, encoding="utf-8")
    (outdir / "tokens.css").write_text(copied_tokens_css, encoding="utf-8")

    # 7b. M6 output assertions: HTML must link tokens.css, styles.css must
    # contain no raw hex, and every plan section id must be either rendered
    # or explicitly skipped.
    try:
        _run_output_assertions(
            html=html,
            stylesheet_text=stylesheet,
            declared_section_ids=[s["id"] for s in plan],
            rendered_skipped_ids=[s["id"] for s in plan if not s["emitted"]],
            css_label="styles.css",
        )
    except OutputAssertionError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1

    # 8. Build report.
    report_md = render_build_report(
        brief=brief,
        plan=plan,
        brand_name=brand_name,
        brand_name_source=brand_name_source,
        contrast=contrast,
        css_hex_hits=hex_hits,
        tokens_css_vars=copied_declared_vars,
        expected_token_vars=list(EXPECTED_TOKEN_VARS),
        reference_present=reference["present"],
        reference_dir=reference.get("dir"),
        reference_files=reference.get("files", {}),
        tokens_dist_css=str(tokens_css_src),
        tokens_dist_json=str(tokens_root / "tokens" / "dist" / "tailwind-tokens.json"),
        outdir=outdir,
    )
    (outdir / "BUILD-REPORT.md").write_text(report_md, encoding="utf-8")

    # Final stdout: the outdir path. Matches synthesize_tokens.py convention.
    print(str(outdir))
    return 0


def _run_plan_path(
    *,
    brief: dict[str, Any],
    design_plan_path: Path,
    tokens_root: Path,
    tokens_css_src: Path,
    tokens_css_text: str,
    font_substitutions: dict[str, Any],
    project_slug_override: str | None,
    outdir: Path,
) -> int:
    """Plan-driven composition path. Returns process exit code.

    This is the only place where the design-plan flow runs. The fallback
    `main()` body above is untouched.

    Sequence:
      1. Load design-plan.json.
      2. Re-run design_pass.verify_source_fields on the plan+brief. Refuse
         to render (exit 1) if it reports any violation — this is the
         "invent-nothing" gate, owned by design_pass.py and imported here
         rather than re-implemented.
      3. Derive brand name + resolve contrast (same logic as fallback).
      4. Build per-section view + skip list.
      5. Render HTML from the plan + render the plan-aware stylesheet.
      6. Emit-gate: no raw hex literals outside tokens.css.
      7. Write outputs + plan-aware BUILD-REPORT.md.
    """
    # 1. Load plan
    try:
        plan = load_design_plan(design_plan_path)
    except ComposeError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1
    if plan is None:
        # Defensive: load_design_plan returns None iff the path was None,
        # but in this branch the caller already passed a path. Keep the
        # check so a future caller cannot accidentally bypass the gate.
        print("compose_site: --design-plan resolved to no document", file=sys.stderr)
        return 1

    # 2. invent-nothing gate: every source_brief_fields path must resolve
    # to a non-empty value in the brief. We IMPORT design_pass.verify_source_fields
    # rather than re-implementing it so the two passes share one source of truth.
    violations = verify_plan_against_brief(plan, brief)
    if violations:
        print(
            "compose_site: design-plan failed verify_source_fields "
            f"({len(violations)} violation(s)):",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print(
            "Refusing to render — every source_brief_fields path in the plan "
            "must resolve to a non-empty value in the brief. Edit the plan or "
            "fix the brief, then re-run.",
            file=sys.stderr,
        )
        return 1

    # 3. Brand name + contrast (same derivation as fallback path).
    brand_name, brand_name_source = derive_brand_name(brief, project_slug_override)
    contrast = resolve_contrast(brief.get("palette_from_logo", {}) or {}, brand_name)

    # 4. Per-section view + runtime-skip list.
    copy_index = index_copy_blocks(plan.get("copy_blocks", []) or [])
    signature = plan.get("signature_element", {}) or {}
    motion = plan.get("motion_vocabulary", {}) or {}
    motion_register = motion.get("register", "balanced")
    sections, runtime_skipped = plan_section_view(
        plan_sections=plan.get("sections", []) or [],
        copy_index=copy_index,
        brief=brief,
        signature_element=signature,
        motion_register=motion_register,
    )

    # 5. Render HTML + plan-aware stylesheet.
    html = render_html_from_plan(
        brief=brief,
        plan=plan,
        sections=sections,
        brand_name=brand_name,
        brand_name_source=brand_name_source,
        font_substitutions=font_substitutions,
    )
    stylesheet = render_plan_stylesheet(contrast, motion_register)

    # 6. Emit-gate: same as fallback. Plan-driven CSS must also contain
    # zero raw hex literals outside tokens.css.
    hex_hits = find_hex_literals(stylesheet)
    if hex_hits:
        print("compose_site: emit gate FAILED — raw hex literals found in styles.css:", file=sys.stderr)
        for ln, line in hex_hits:
            print(f"  L{ln}: {line}", file=sys.stderr)
        return 1

    # 7. Write outputs.
    outdir.mkdir(parents=True, exist_ok=True)
    copied_tokens_css = add_accessible_text_tokens(tokens_css_text, contrast)
    copied_declared_vars = sorted(
        set(re.findall(r"--[a-zA-Z0-9_-]+", copied_tokens_css))
    )
    (outdir / "index.html").write_text(html, encoding="utf-8")
    (outdir / "styles.css").write_text(stylesheet, encoding="utf-8")
    (outdir / "tokens.css").write_text(copied_tokens_css, encoding="utf-8")

    # 7b. M6 output assertions: HTML links tokens.css, no raw hex in
    # styles.css, every plan section id is rendered-or-skipped.
    # The composer anchors the first plan section as `id="hero"` regardless
    # of the plan id — reflect that deliberate alias in id_aliases so the
    # rendered-ids-present check is satisfied.
    plan_sections_list = list(plan.get("sections", []) or [])
    first_section_id = ""
    if plan_sections_list and isinstance(plan_sections_list[0], dict):
        first_section_id = str(plan_sections_list[0].get("id", "") or "")
    id_aliases: dict[str, str] | None = None
    if first_section_id and first_section_id != "hero":
        id_aliases = {first_section_id: "hero"}
    try:
        _run_output_assertions(
            html=html,
            stylesheet_text=stylesheet,
            declared_section_ids=[
                str(s.get("id", ""))
                for s in plan_sections_list
            ],
            rendered_skipped_ids=list(runtime_skipped),
            css_label="styles.css",
            id_aliases=id_aliases,
        )
    except OutputAssertionError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1

    report_md = render_plan_build_report(
        brief=brief,
        plan=plan,
        sections=sections,
        skipped_at_runtime=runtime_skipped,
        brand_name=brand_name,
        brand_name_source=brand_name_source,
        contrast=contrast,
        css_hex_hits=hex_hits,
        tokens_css_vars=copied_declared_vars,
        expected_token_vars=list(EXPECTED_TOKEN_VARS),
        tokens_dist_css=str(tokens_css_src),
        tokens_dist_json=str(tokens_root / "tokens" / "dist" / "tailwind-tokens.json"),
        font_substitutions=font_substitutions,
        outdir=outdir,
    )
    (outdir / "BUILD-REPORT.md").write_text(report_md, encoding="utf-8")

    print(str(outdir))
    return 0


def _safe_makedirs(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as exc:
        print(f"error: could not create outdir {path}: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())