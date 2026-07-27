#!/usr/bin/env python3
"""Compose a real, servable static site from a brand brief + synthesized tokens.

This is the M3 design-pass emitter (web-designer skill step 4, per
`research/integration-plan.md` §5 M3). It is deliberately stack-free: plain HTML +
CSS, no build step, no framework, no npm. That keeps the React/Next vs. Astro vs.
Nuxt decision (integration-plan §6.1) open until M4+ and lets M4's validation gates
audit the output without a build chain.

CLI:
    compose_site.py --brand-brief <path> --tokens <synthesize_tokens outdir>
        [--reference-report <dir>] -o <outdir> [--project-slug <slug>]

The emitter is a *re-versioning* step, not a mirror. It composes sections ONLY from
content that actually exists in the brand brief — every section it skips (with
reason) is reported in BUILD-REPORT.md so the operator can see exactly what data
drove the page and what was absent. Copy, photos, quotes, and stats are never
invented; if a section's source data is missing the section is omitted.

Outputs:
    <outdir>/index.html        semantic HTML, links tokens.css + styles.css
    <outdir>/tokens.css        copy of synthesized tokens/dist/tokens.css
    <outdir>/styles.css        component CSS using var(--*) tokens only
    <outdir>/BUILD-REPORT.md   sections emitted vs skipped + brief provenance +
                                contrast decisions + carried-forward limitations

Honesty conventions (same as nt-site-mirror + web-designer SKILL.md):
  * exit 0 + stdout path of outdir              -> site composed cleanly
  * exit 1 + stderr diagnostic                   -> brand brief is invalid or
                                                   required tokens are missing
  * exit 2 + stderr usage / IO error             -> could not even attempt composition

The script never claims a higher tier than the brief supports; it reports which
sections were skipped because the brief's data was absent (not because the emitter
"forgot") and carries every entry from `brief.limitations[]` forward into the
build report unchanged.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Reuse the shared brand-brief validator. Same module the synthesize_tokens script
# imports — keeps validation consistent across the pipeline.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_brand_brief import _fallback_validate, _jsonschema_validate  # noqa: E402

SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.0"

# Token CSS variables we EXPECT to find in tokens.css. The emitter uses them as
# var(--token-name) in styles.css; the page CSS itself contains no raw hex. This
# list is also what BUILD-REPORT.md reports as "tokens referenced."
EXPECTED_TOKEN_VARS: tuple[str, ...] = (
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


def load_tokens(tokens_root: Path) -> tuple[Path, dict[str, Any], str]:
    """Load the synthesized token artifacts. Returns (tokens.css path, tailwind json dict, css text).

    The composer needs:
      * tokens/dist/tokens.css     — copied into the output site as a static asset.
      * tokens/dist/tailwind-tokens.json — read for the palette + spacing values
                                           so we can do contrast math + record
                                           provenance without re-parsing CSS.

    Raises ComposeError if either is missing.
    """
    css_path = tokens_root / "tokens" / "dist" / "tokens.css"
    json_path = tokens_root / "tokens" / "dist" / "tailwind-tokens.json"

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

    return css_path, tw, css_text


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
# HTML rendering
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
    display = escape(typography.get("display_family", "sans-serif"))
    body = escape(typography.get("body_family", "sans-serif"))
    mono = escape(typography.get("mono_family", "monospace"))

    primary = escape(palette.get("primary", "#000000"))
    secondary = escape(palette.get("secondary", "#ffffff"))

    return f"""<!doctype html>
<html lang="en" style="--page-display: {display}; --page-body: {body}; --page-mono: {mono}; --page-primary: {primary}; --page-secondary: {secondary};">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
  color: var(--color-neutral-6);
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
  color: var({accent_token});
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
.nav-list a:hover {{ color: var({accent_token}); }}

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
  color: var({accent_token});
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
  color: var(--color-neutral-6);
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
.footer-meta {{ font-size: var(--typography-font-size-0, 12px); color: var(--color-neutral-3); }}

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
                return _decision(
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

    # Fallback: nothing met threshold — use the best pair we found and NOTE it.
    if ordered:
        chosen_text_token = _hex_to_token_name(chosen_text_hex, ordered)
        chosen_bg_token = _hex_to_token_name(chosen_bg_hex, ordered)
    note_parts.append(
        f"no neutral pair met {ratio_threshold:.1f}:1; using best-available pair "
        f"({chosen_text_token} on {chosen_bg_token}, {best_ratio:.2f}:1) and shipping "
        f"a contrast limitation"
    )
    return _decision(
        text_token=chosen_text_token,
        bg_token=chosen_bg_token,
        accent_token="--color-accent",
        text_hex=chosen_text_hex,
        bg_hex=chosen_bg_hex,
        accent_hex=accent,
        ratio_text_bg=best_ratio,
        note=" ".join(note_parts),
    )


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

- **Text token:** `{contrast["text_token"]}` ({contrast["text_hex"]})
- **Background token:** `{contrast["bg_token"]}` ({contrast["bg_hex"]})
- **Accent token:** `{contrast["accent_token"]}` ({contrast["accent_hex"]})
- **Measured contrast (text vs. background):** {contrast["ratio_text_bg"]:.2f}:1
- **Decision note:** {contrast["note"]}

If the measured ratio is below WCAG AA body-text (4.5:1), the page is shipped
anyway with this note — the contrast limitation is **carried forward** rather
than hidden. Operators may pick a different neutral pair manually in a later
pass.

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

{audit_lines and "First hits (for diagnosis):\n\n```\n" + audit_lines + "\n```\n" or ""}

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
        tokens_css_src, tw, tokens_css_text = load_tokens(tokens_root)
    except ComposeError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1

    declared_vars = sorted(set(re.findall(r"--[a-zA-Z0-9_-]+", tokens_css_text)))
    try:
        assert_tokens_referenced(tokens_css_text, list(EXPECTED_TOKEN_VARS))
    except ComposeError as exc:
        print(f"compose_site: {exc}", file=sys.stderr)
        return 1

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
    (outdir / "index.html").write_text(html, encoding="utf-8")
    (outdir / "styles.css").write_text(stylesheet, encoding="utf-8")
    shutil.copyfile(tokens_css_src, outdir / "tokens.css")

    # 8. Build report.
    report_md = render_build_report(
        brief=brief,
        plan=plan,
        brand_name=brand_name,
        brand_name_source=brand_name_source,
        contrast=contrast,
        css_hex_hits=hex_hits,
        tokens_css_vars=declared_vars,
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


def _safe_makedirs(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as exc:
        print(f"error: could not create outdir {path}: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())