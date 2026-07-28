#!/usr/bin/env python3
"""Shared output-validation helpers for the web-designer pipeline scripts.

These are the "every script validates its own output" primitives called out
by the M6 self-verification harness. They are intentionally small, pure
stdlib, and importable from synthesize_tokens.py, compose_site.py, and
the verify.sh driver without dragging in Playwright or any external
dependency.

The governing principle: a script that emits CSS, HTML, or design-plan
artifacts MUST refuse to exit 0 if its output violates a documented
invariant. The two original failure modes this module exists to prevent
are:

  1. synthesize_tokens.py emitting `font-family: Inter, s, y, s, t, e, m, ...`
     because some code iterated a string character-by-character. The fix is
     a parser that splits on commas only outside quoted segments, then
     validates each family is non-empty and >=2 characters (so a stray
     "s" can't pass).

  2. compose_site.py shipping styles.css that contains raw hex literals
     (`color: #efad2b;`) instead of `var(--color-primary)`. The fix is a
     scanner that flags every hex literal in any *.css file the script
     wrote that is NOT tokens.css.

If you add a new script that emits an artifact, import the helpers here
and call them at the bottom of the script's main() before returning 0.
"""
from __future__ import annotations

import re
from typing import Iterable


# A hex color literal we want to keep out of non-token CSS. Same shape
# browsers use for color values; deliberately permissive about case so we
# catch #EFAD2B, #efad2b, and #EfAd2B alike.
_HEX_LITERAL = re.compile(r"#[0-9A-Fa-f]{3,8}\b")

# Family names we refuse to emit as a LIVE CSS value. These are the
# paid/commercial faces the synthesizer MUST substitute out per
# `synthesize_tokens._resolve_font_substitutions`. They must NEVER appear
# as the primary face in tokens.css, the page <style>, or any stylesheet.
# The list is conservative: it covers the well-known offenders we
# historically saw in brand briefs and the short-lived M6 regression
# where Switzer leaked into a live CSS rule.
PAID_FACE_NAMES: tuple[str, ...] = (
    "switzer",
    "neue haas grotesk",
    "neue-haas-grotesk",
    "akzidenz grotesk",
    "akzidenz-grotesk",
    "din pro",
    "din-pro",
    "futura pt",
    "futura-pt",
    "avenir next",
    "avenir-next",
    "trade gothic",
    "trade-gothic",
    "sentinel",
    "charter",
    "caslon",
    "itc franklin gothic",
    "ff mark",
    "ff-mark",
    "gt america",
    "gt-america",
    "tp architect",
    "tp-architect",
)


def _split_css_font_family(value: str) -> list[str]:
    """Split a CSS `font-family` declaration value into individual family parts.

    Splits on commas that are NOT inside double-quoted segments. Strips
    surrounding whitespace. Drops empty parts. Resolves backslash escape
    sequences (``\\\\`` -> ``\\``, ``\\"`` -> ``"``) so a family name with
    embedded double quotes (rare but legal in CSS) is reported as the
    intended token, not as raw escape bytes.

    >>> _split_css_font_family('Inter, system-ui, sans-serif')
    ['Inter', 'system-ui', 'sans-serif']
    >>> _split_css_font_family('"JetBrains Mono", ui-monospace, monospace')
    ['JetBrains Mono', 'ui-monospace', 'monospace']
    >>> _split_css_font_family('"Bogus\\\\"Family", sans-serif')
    ['Bogus"Family', 'sans-serif']
    """
    families: list[str] = []
    current: list[str] = []
    in_quote = False
    escape = False
    for ch in value:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_quote = not in_quote
            # Drop the quote itself from the family token; we only care
            # about whether the contents were non-empty.
            continue
        if ch == "," and not in_quote:
            families.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        families.append(tail)
    return families


def validate_css_font_family(value: str) -> list[str]:
    """Validate a single CSS `font-family` declaration value.

    Returns a list of error messages (empty if valid). The checks are:

      * >= 2 comma-separated families (a single-family declaration has no
        fallback and breaks silently when the face fails to load).
      * every family is non-empty.
      * no family is a single character (catches the char-by-char split
        bug that once emitted `Inter, s, y, s, t, e, m, ...`).
      * the whole value is not wrapped in literal quotes (catches the
        `css_family()` helper that did `json.dumps(value)` and produced
        `"Inter, system-ui, sans-serif"` as ONE quoted family name).
      * no nested/escaped-quoted family that contains a `,` (would mean
        the parser missed a quote boundary).
      * no paid face appears as a family in a LIVE CSS declaration. Paid
        faces belong in provenance only.

    >>> validate_css_font_family('Inter, system-ui, sans-serif')
    []
    >>> validate_css_font_family('Inter')
    ['font-family has 1 part(s); a real fallback chain has >= 2']
    >>> errors = validate_css_font_family('Inter, s, y, s, t, e, m')
    >>> all("char-split bug" in e for e in errors) and len(errors) >= 5
    True
    >>> errors = validate_css_font_family('"Inter, system-ui, sans-serif"')
    >>> errors[0]
    'font-family value is wrapped in literal quotes; only individual family names with embedded spaces should be quoted'
    >>> errors = validate_css_font_family('Switzer, system-ui, sans-serif')
    >>> errors[0]
    "font-family uses restricted/paid face 'Switzer'; use OFL substitute (see synthesize_tokens.OFL_SUBSTITUTES)"
    """
    errors: list[str] = []

    stripped = value.strip()
    if stripped.startswith('"') and stripped.endswith('"') and stripped.count('"') == 2:
        errors.append(
            "font-family value is wrapped in literal quotes; only individual "
            "family names with embedded spaces should be quoted"
        )

    families = _split_css_font_family(stripped)
    if len(families) < 2:
        errors.append(
            f"font-family has {len(families)} part(s); a real fallback chain has >= 2"
        )

    for family in families:
        if not family:
            errors.append("font-family has an empty part (stray comma)")
            continue
        if len(family) <= 1:
            errors.append(
                f"font-family part {family!r} is too short ({len(family)} chars); "
                f"likely char-split bug"
            )
        if "," in family:
            errors.append(
                f"font-family part {family!r} contains a comma; "
                f"parser likely missed a quote boundary"
            )
        if family.lower() in PAID_FACE_NAMES:
            errors.append(
                f"font-family uses restricted/paid face {family!r}; "
                f"use OFL substitute (see synthesize_tokens.OFL_SUBSTITUTES)"
            )

    return errors


def parse_css_variable_declarations(css: str) -> dict[str, str]:
    """Extract `--name: value;` declarations from a CSS string.

    Handles multi-value declarations (the fallback chain after the colon
    is captured up to the terminating semicolon, including commas). The
    returned map is keyed by the variable name (no leading dashes).

    >>> parse_css_variable_declarations(':root { --color-primary: #efad2b; --font: Inter, sans-serif; }')
    {'color-primary': '#efad2b', 'font': 'Inter, sans-serif'}
    """
    out: dict[str, str] = {}
    pattern = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);")
    for match in pattern.finditer(css):
        out[match.group(1)] = match.group(2).strip()
    return out


def find_raw_hex_in_css(css: str, *, allow_in_token_block: bool = True) -> list[tuple[int, str]]:
    """Return `(line_number, line_text)` for every raw hex literal in `css`.

    If `allow_in_token_block` is True, lines inside a `:root { ... }` block
    are exempt — those are the legitimate hex tokens tokens.css defines.
    Use False when scanning a stylesheet that should NEVER contain raw
    hex (every color must be a `var(--token)`).
    """
    hits: list[tuple[int, str]] = []
    in_token_block = False
    brace_depth = 0
    for line_no, line in enumerate(css.splitlines(), start=1):
        stripped = line.strip()
        if allow_in_token_block:
            # Track `:root { ... }` blocks. Tokens.css emits exactly one
            # at the top, then sections separated by blank lines. We
            # accept any line inside a `:root` block as legitimate.
            if ":root" in stripped and "{" in stripped:
                in_token_block = True
                brace_depth = stripped.count("{") - stripped.count("}")
                continue
            if in_token_block:
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    in_token_block = False
                continue
        for match in _HEX_LITERAL.finditer(line):
            hits.append((line_no, line.rstrip()))
    return hits


def require_css_references_tokens_css(html: str, tokens_href: str = "tokens.css") -> list[str]:
    """Return error messages if `html` does not link to `tokens_href`.

    The check is presence-based: an emitted index.html that omits the
    <link rel="stylesheet" href="tokens.css"> reference will silently
    lose all design tokens and look like a different brand. Catch it
    here.
    """
    errors: list[str] = []
    if tokens_href not in html:
        errors.append(
            f"index.html does not reference {tokens_href!r}; "
            f"the design-token stylesheet is missing"
        )
    return errors


def require_section_ids_rendered_or_skipped(
    declared_ids: Iterable[str],
    rendered_html: str,
    skipped_ids: Iterable[str],
    id_aliases: dict[str, str] | None = None,
) -> list[str]:
    """Return error messages for every section id in `declared_ids` that
    is NEITHER rendered into the HTML NOR listed as skipped.

    Every plan section id is either rendered (`<section id="X">` or a link
    to `#X`) or recorded as skipped in BUILD-REPORT.md. There is no third
    option — a silently dropped section is a Fidelity Gap.

    `id_aliases` (optional) maps `plan_id -> rendered_id` for IDs that the
    renderer intentionally renames. Used by compose_site.py where the
    first plan section is forcibly aliased to ``hero`` regardless of what
    the plan called it. An alias counts as "rendered": if `plan_id == "cover"`
    and `id_aliases["cover"] == "hero"`, then the section is satisfied as
    long as `id="hero"` or `#hero` appears in the HTML.
    """
    errors: list[str] = []
    declared_set = {sid for sid in declared_ids if sid}
    skipped_set = set(skipped_ids)
    aliases = id_aliases or {}
    # We look for either a `<section id="X" ...>` block or any `href="X"` /
    # `#X` link in the rendered HTML. Nav links are sufficient evidence a
    # section exists (the section element itself is rendered just below the
    # nav). For aliased plan ids we look up the rendered form first.
    for sid in declared_set:
        if sid in skipped_set:
            continue
        render_id = aliases.get(sid, sid)
        section_present = (
            f'id="{render_id}"' in rendered_html
            or f"#{render_id}" in rendered_html
        )
        if not section_present:
            errors.append(
                f"section {sid!r} is declared in the design plan but is "
                f"neither rendered into index.html nor listed as skipped"
            )
    return errors


def section_ids_in_html(html: str) -> set[str]:
    """Return the set of section ids referenced via `id="..."` in `html`.

    Used by callers that want to cross-check the design plan against the
    rendered output without re-parsing the plan schema.
    """
    return set(re.findall(r'id="([a-zA-Z0-9_-]+)"', html))


class OutputAssertionError(RuntimeError):
    """Raised by scripts that detect their own emitted output is invalid.

    Scripts catch this at the top of main() and exit with a clear
    message naming the offending value. The verify.sh driver also
    catches it.
    """
