# pedicelmarketing.ch — Swiss site, design

6 Oct 2026. Approved in chat by the operator, section by section.

## Goal
A Swiss version of the Pedicel website on **pedicelmarketing.ch**, in **German (default), French and English**, selling the
services we sell today (the six pillars in `Pedicel AI/research/offering.md`, Hub included). It is the first step
of the Swiss go-to-market in `Pedicel AI/research/competitors/ch/summary.md`. pedicelmarketing.com is not touched.

## Decisions (operator, 6 Oct 2026)
| Topic | Decision |
|---|---|
| Domain | **pedicelmarketing.ch** (RDAP 404 + no NS on 6 Oct = looks unregistered). Not bought yet. |
| Build route | **Copy of the current site** (the Webflow mirror) with rewritten copy. No new framework. |
| Languages | `/` = German (Swiss: `ss`, never `ß`; "Sie"), `/fr/` = French (Swiss; "vous"), `/en/` = English. |
| Prices | **None on the site.** Every call to action → free AI audit or contact. |
| Legal entity | Launch with the Estonian company. Swiss address/+41 added later. |
| People imagery | AI-generated, Swiss-looking people in work scenes, no AI label. **Never** as named fake staff, fake testimonials or fake client quotes (UWG: misleading). |
| Case studies | **Keep all 4** (COEO, ISN Medical, La Taberna Fantástica, SANA). **Remove every number** (all four reused the same 10.8 % / 250 % / 300+). Fix leftover wrong names ("Vanguard Medical Solutions" on ISN, "Benahavis Bistro" on LTF). Add real ISN facts. |
| Blog | Dropped for launch (31 posts, mostly Nigeria). Nav link removed. |

## Pages (each in DE / FR / EN)
| Page | Source page in mirror | Change |
|---|---|---|
| Home | `_/index.html` | New positioning + 6 pillars + Hub + audit CTA |
| Services overview | `services/` | 6 pillars |
| Outbound | `service-lead-generation/` | LinkedIn, consented email, calls, WhatsApp + Hub CRM |
| AI content & motion video | `service-brand-presence/` | hook database, motion graphics, voiceover DE/FR/EN |
| Web & tracking | `service-web-development/` | sites, landing pages, GA4, Consent Mode, CAPI, PostHog |
| Paid ads | `service-social-media/` | Meta + Google, spend paid direct, no markup |
| SEO + AI visibility (GEO) | copy of a service page | technical SEO, Google Business Profile, monthly AI-answer tracking |
| The Hub | copy of a service page | Requests, Approvals, Analytics, Brand score, Inspiration; learning loop |
| Free audit | `audit/` | free AI audit: AI visibility, competitors, their ads/search, ~5 fixes + short video |
| About | `about-our-marketing-agency/` | rewritten; AI scene imagery |
| Contact | `contact-us/` | kept |
| Portfolio + 4 case studies | `our-marketing-portfolio/`, `projects/*` | numbers removed, names fixed |
| **Impressum** | new (copy of a simple page) | see Legal |
| **Datenschutz** | new | nDSG privacy notice |
| 404 | `404.html` | translated |

Copy claims must stay inside `offering.md`'s "Do not claim" lines (no conversion lifts, no "#1 on Maps", no
persona-panel performance claims, no in-house film crew, no cold email at scale).

## Positioning (from the 5 research gaps)
One trilingual team for Swiss SMEs (DE/FR/EN) · AI motion video · outbound (LinkedIn + WhatsApp) as a service ·
transparency via the Hub (live approvals, no lock-in) · visibility in AI answers (GEO). Target search terms:
"KI Marketing Agentur", "agence marketing IA".

## Legal
**Impressum:** Pedicel Marketing OÜ · Lõõtsa tn 5, 11415 Tallinn, Estonia · Registry code 16104440 (e-Business
Register) · Board member: Sergio Andres Palacio Martinez · info@pedicelmarketing.com · +34 677 196 547. No VAT
number (EE102324118 inactive since 14 Jun 2025 — FACTS.md).
**Datenschutz:** controller, data collected (forms, analytics), purposes, processors and cross-border transfers
(Supabase, email provider, analytics), retention, rights under nDSG (and GDPR), contact. Marked as a draft for
counsel review in the repo; not legal advice.

## Build
- Folder: `pedicelmarketing-ch/` in this repo (branch `feat/pedicelmarketing-ch`).
- **Input:** the built mirror at `pedicelmarketing/mirror/` (git-ignored, 128 MB, 122 MB of it `_external/`).
  The CH build reads it; it is not copied into git.
- **Text layer:** `pedicelmarketing-ch/strings/{en,de,fr}.json` — one key per text node per page.
  `extract.py` pulls text from the EN pages; `build.py` writes `dist/` (DE at root, `fr/`, `en/`) by replacing
  text nodes, `<html lang>`, `<title>`, meta description and og tags.
- Page structure edits (new pages, removed blog/number blocks, nav changes) are made once on the EN template
  pages in `pedicelmarketing-ch/pages/`, then text goes through the string files.
- Added to every page: language switcher in the nav, `hreflang` alternates + `x-default` (→ DE), canonical
  URL on pedicelmarketing.ch. Plus `sitemap.xml` and `robots.txt`.
- **Images:** AI people/scene images generated on Comfy (Z-Image or a partner model; Google image key returned
  402 on 6 Oct), ~CHF 1–3 total, saved into `pedicelmarketing-ch/assets/`.
- **Forms:** same handler (`pedicelmarketing/deploy/form_handler.py`). CH forms post to `/api/forms/ch-audit`
  and `/api/forms/ch-contact`; the handler gets two new specs whose labels end in "(CH)" so CH leads are
  tagged in the Hub CRM. .com behaviour unchanged.

## Hosting
spire nginx: new server block for `pedicelmarketing.ch` + `www` → `/var/www/pedicelmarketing-ch`, same
security snippet and `/api/forms/` proxy as .com; TLS via certbot. DNS A record → 62.210.212.199.
**Blocked on buying the domain** (Hostinger connector failed to connect on 6 Oct — operator buys or reconnects).
Until then the site is previewed locally.

## Checks (all must pass before publishing)
1. Screenshots of every page × 3 languages × desktop (1440) + phone (390); no horizontal scroll on phone.
2. Link check on `dist/`: no internal 404s; no link to `/blog/`.
3. Language check: no `ß` anywhere; no leftover English sentences in DE/FR pages (string-file coverage = 100 %).
4. Number check: none of `10.8%`, `250%`, `300+`, "Vanguard", "Benahavis Bistro" in `dist/`; no price strings (`CHF`, `€`).
5. One test submit of each form per language reaches the handler and the CRM with the "(CH)" label (test lead deleted after).
6. hreflang/canonical present and pointing at pedicelmarketing.ch on every page.

## Out of scope
Swiss address/+41 number, prices, blog, Italian, paid ads for the launch, cold email.
