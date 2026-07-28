# Brand Brief — Barcoop Bevy (project slug: leo-foods-redesign)

Date: 2026-07-28 (UTC)
Author: research-agent (this profile)
Reference site (for structure/typography only): https://stripe.com
Brand site fetched: https://barcoopbevy.com (HTTP 200, 440 KB HTML)
Images verified: 22 of 22 (all Webflow CDN, every URL returned 200 image/jpeg|image/png|image/svg+xml)

------------------------------------------------------------
HEADS-UP — design_brief vs live site do not match
------------------------------------------------------------
The operator's task described this brand as "International food & drink
wholesaler and cash & carry based in Marbella, Spain. B2B: sells to
restaurants, hotels, bars." The live site at barcoopbevy.com is a DIFFERENT
business: Barcoop Bevy, a B2C all-natural cocktail mixer brand, made in
Charleston, South Carolina, sold direct-to-consumer and through a small US
distributor network. There is no Spain / Marbella / EU / cash-and-carry
presence on the site. The brief below is grounded in the live site, not in
the design_brief. The web-designer must resolve this with the operator
before composing — listed as the first entry in `limitations`.

------------------------------------------------------------
WHO THEY ARE (one paragraph)
------------------------------------------------------------
Barcoop Bevy is a line of seven all-natural, non-alcoholic cocktail mixers
(Classic Margarita, Skinny Margarita, Bloody Mary, Cucumber Mojito, Ginger
Smash, Spicy Strawberry Margarita, Piña Colada) made by husband-and-wife
team Joe and MariElena Raya in Charleston, SC. The couple previously ran
one of Charleston's most renowned craft cocktail bars before launching the
mixer line. Barcoop Bevy sits alongside sister brands from the same
founders / family: Bittermilk, Tippleman's, and Drinkmanship Distillery.
The flagship Bloody Mary (Smoked Sea Salt + Chiles) won the 2024 Specialty
Food Association "Beverage Product of the Year" and a 2024 SOFI Gold.

------------------------------------------------------------
VOICE & TONE
------------------------------------------------------------
- Register: warm-practical-craft (B2C, conversational, slightly playful)
- Sentence case: yes (one intentional exception: "REAL Ingredients Only"
  uses all-caps as a typographic accent, not a sentence-case violation)
- Formality: 2/5 (low — bartender-to-drinker, not agency-to-CMO)
- Avg sentence: ~11 words; short, direct, no jargon
- Words they lean on: real, natural, all-natural, crafted, bartenders,
  simple, bevy, coop, easy, just, only
- Words to never use: synergy, delve, leverage, in today's, revolutionary,
  cutting-edge, best-in-class, world-class, elevate, unleash, game-changing,
  premium, luxury, artisanal, bespoke
- Example lines straight from the site:
    "A feel-good marg with real ingredients, little calories and grande flavor."
    "A perfect mix of bold and juicy flavors, you'll be a morning person in no time!"
    "Just add spirit."
    "Made by bartenders. Made in Charleston, South Carolina."

------------------------------------------------------------
PALETTE  (method: CSS hex-grep on 440 KB of inline styles + Webflow asset inspection)
------------------------------------------------------------
- Primary:   #FFC517  (chicken-coop yellow — 111 inline-style hits, the dominant
                       brand color and the wordmark color)
- Secondary: #CDBD81  (warm khaki — 96 hits, used for tags and rule lines)
- Accent:    #259E7E  (teal-green — 85 hits, the single cool color, used
                       sparingly for links and CTAs; appears in 'real
                       ingredients' context, not on the primary yellow)
- Neutrals:  #FBF7E9 (body cream, 80 hits), #765F2C (warm brown, 56 hits),
             #3D3D3D (text dark), #FFF7C5 (light cream, 70 hits, card backdrop),
             #95CC7D (light green tint, 38 hits)
- No image logo exists. The wordmark is rendered as a styled <div
  class="logo"> with 'Barcoop Bevy' in the display face, 'vy' in a distinct
  span. The logo IS the typography.

------------------------------------------------------------
TYPOGRAPHY
------------------------------------------------------------
- Display:  Recoleta (paid, Klim) — DO NOT vendor. Substitute Fraunces (OFL)
            or a similar humanist serif for production.
- Body:     Inter (SIL OFL 1.1)
- Mono:     JetBrains Mono (OFL) — used in nav for "RECIPES" tags
- Scale:    ratio 1.250, steps [12, 14, 16, 20, 24, 32, 48, 64]
- License notes: do not copy the live site's variable display face. Do not
  use Inter for the display role — "Inter everywhere" is the agency-website
  look this brand is NOT.

------------------------------------------------------------
REAL PHOTO INVENTORY  (22 verified URLs, all 200 OK)
------------------------------------------------------------
Home / lifestyle:
  - https://cdn.prod.website-files.com/6614094ec46a8c211ee3efac/674f29033ad974dbf3d87d61_BarcoopBevy-CLW-156.jpg
      (Charleston Local Works feature — hero on home page)
Founders (about):
  - https://cdn.prod.website-files.com/6614094ec46a8c211ee3efac/666b5ae0df9ff76766b7e532_about-craftsmen.jpg
      (alt: "Joe and MariElena Raya")
  - https://cdn.prod.website-files.com/6614094ec46a8c211ee3efac/666b5ae00326da1700b407ed_about-ingredients.jpg
      ("Made with real ingredients" pillar)
  - https://cdn.prod.website-files.com/6614094ec46a8c211ee3efac/666b5ae1c2211cb9d644c482_about-easy.jpg
      ("Easy to use and even easier to enjoy" pillar)
Product bottle shots (1L, drop-shadow, all 200 OK):
  - Classic Margarita, Skinny Margarita, Bloody Mary, Cucumber Mojito,
    Ginger Smash, Spicy Strawberry Margarita, Piña Colada
  (URLs in brand-brief.json; each cdn.prod.website-files.com/66154e3e740024a5542c8310/...
   ending in -bottle-shadow.png)
Cocktail / recipe photos (finished-drink JPGs):
  - Bloody Mary, Dark and Stormy, Lite Limeade (mocktail), Skinny Margarita,
    Virgin Piña Colada, Vodka Gimlet, Spicy Strawberry Lime Soda (mocktail),
    Bloody Maria, Michelada, Virgin Bloody Mary
Merch:
  - Barcoop Bevy hat (dark)

------------------------------------------------------------
WHAT THEY ACTUALLY SELL  (service_facts)
------------------------------------------------------------
1. Cocktail Mixers — 7 SKUs, $12 per 1L bottle, direct via Webflow shop.
2. Wholesale / off-premise retail — 7 US states (GA, SC, NC, TN, VA + gaps
   routed to Faire). No international or Spanish presence. drink@barcoopbevy.com
3. Recipes / cocktail library — 36+ recipes, free, the brand's SEO engine.
4. Merch — Barcoop Bevy Hat (Dark) at minimum.

The standard serve is 2 parts mixer : 1 part spirit (Bloody Mary is 4:1).
Every mixer is non-alcoholic and works with soda water for a mocktail.
Press contact: Ashley Mills, ashley@goldenword.co

------------------------------------------------------------
SOCIAL HIGHLIGHTS
------------------------------------------------------------
- LinkedIn: no presence on the site. Empty array.
- Instagram: handle @barcoopbevy verified on the site (home, about, contact,
  shop footers), but the grid was not opened via logged-in Cloak this run.
  The single social_highlights.instagram entry is a placeholder, not a
  fetched post.
- Twitter: @BarcoopBevy verified, not fetched.
- Facebook: facebook.com/barcoopbevy verified, not fetched.

------------------------------------------------------------
TESTIMONIALS
------------------------------------------------------------
Empty. The site has no on-page customer testimonials. Do not invent any.
The brand has press coverage (NYT Wirecutter, Boston Globe, Authority
Magazine, SFA, Golf.com, StyleBlueprint) — those are press hits, not
customer quotes, and the brief does not rewrite them as testimonials.

------------------------------------------------------------
BRAND DON'TS  (one line each — see brand-brief.json for the full list)
------------------------------------------------------------
- No invented testimonials. The site has none. The empty array is honest.
- No B2B / cash-and-carry / Marbella voice. The site is B2C, Charleston, US.
- No B2B-SaaS / agency boilerplate ("leverage", "synergy", "world-class").
- No "artisanal", "craft" (alone), or "premium". The brand uses "crafted",
  "made by bartenders", and "real".
- No purple-gradient / SaaS-startup aesthetic. The brand is sunny yellow +
  cream + teal — warm, not cool.
- No Inter for the display role. Serif display + neutral sans pairing.
- No stock photography of generic bars or beaches. Real products, real
  founders, real cocktails.

------------------------------------------------------------
LIMITATIONS  (what I could NOT recover)
------------------------------------------------------------
1. The design_brief vs live site do not match — see top of this file.
2. No Supabase scrapes persisted (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
   absent from this profile's .env). Raw HTML is at /tmp/barcoop-{home,about,
   shop,bm}.html and is reproducible from the URLs above.
3. LinkedIn, Instagram, Twitter, Facebook — handles verified but content
   not fetched this run.
4. Stripe.com reference content was truncated at the data_pipeline section.
   The reference is for structure and confident typography, not visual
   identity (per the operator).
5. Wholesale price ranges not listed on the site. The PDF press kit
   (https://cdn.prod.website-files.com/6614094ec46a8c211ee3efac/666ca14fc85a42f3d50669f6_BarcoopBevy_PressKit.pdf)
   is binary and was not parsed in this run.
6. /faq on the live site returns 404; the actual FAQ lives at /about#faq.

------------------------------------------------------------
VALIDATOR
------------------------------------------------------------
python3 skills/web-designer/scripts/validate_brand_brief.py \
  reports/brand-leofoods/brand-brief.json
→ VALID reports/brand-leofoods/brand-brief.json
