# Placeholder — M2+ content

This file is a placeholder for the brand-brief contract. The full JSON schema and
worked example will live here once M2 lands.

For now, see `research/workflow-design.md` §2.2 for the canonical schema and §5 for
the worked example (Pedicel Marketing redesign). The schema has these top-level keys:

- `schema_version`, `project_slug`, `fetched_at`, `research_scrapes_ids`
- `sources` — own_site, linkedin, instagram, reference
- `voice_and_tone` — register, favorite_words, banned_words, formality_score
- `palette_from_logo` — primary, secondary, accent, neutrals[]
- `typography_recommendation` — display_family, body_family, mono_family, license_notes
- `real_photo_inventory[]` — url, subject, license, use
- `service_facts[]` — name, description, price_range
- `social_highlights` — linkedin[], instagram[]
- `testimonials[]` — quote, attribution, source_url, license
- `brand_donts[]` — explicit guardrails
- `limitations[]` — what was *not* captured

Until M2, the web-designer skill's M1 scripts treat the brand-brief as out-of-scope —
the reference brief (the M1 deliverable) is the only artifact produced.
