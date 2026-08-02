# v2.0 — changes from the client's video review

Source of the brief: `examples/riki-coach/Assets/new_recording_-_8_1_2026,_6_06_24_pm_v1 (540p).mp4`
(5:48 screen recording, reviewed 2026-08-01). Transcribed locally with Whisper
(medium, `--language es`); each comment was tied to the on-screen element by
extracting frames at the matching timestamp and reading cursor position.

**v1.0 is unchanged and still live.** v2.0 is a separate build on its own tunnel:

| | Build | Origin | URL |
| --- | --- | --- | --- |
| v1.0 | `site/` | `127.0.0.1:8614` | `https://immigrants-energy-marine-abstract.trycloudflare.com` |
| v2.0 | `site-v2/` | `127.0.0.1:8615` | `https://full-logging-barrier-berlin.trycloudflare.com` |

## Two findings that change how the feedback reads

**1. He was viewing the site machine-translated.** The nav read "Start / Clubs /
Camps / Contact" against our "Inicio / Clubs / Camps / Contacto", and Chrome's
translate icon is visible in the address bar. The site is Spanish; he saw
Google's English rendering of it. Any reaction to *wording* is a reaction to
that translation, not to the copy as written. Worth telling him he can turn it
off — the Spanish is the deliverable.

**2. The video file was truncated on first read.** ffmpeg reported
`partial file` and the first audio extraction stopped at 180s of 348s, which
would have silently lost every comment about Camps and Contacto. Re-extracted
with `-err_detect ignore_err -fflags +genpts+igndts`, which recovered the full
348.5s. The change list below covers the whole recording.

## Applied

| # | Timestamp | He said | Change |
| --- | --- | --- | --- |
| 1 | 0:06 | *"aquí tienes la AA Academy… ese logo hay que mirarlo"* | The supplied artwork misspells the name. Only the monogram is used as an image now; the wordmark is set in type — correct, crisp at any size, and readable by screen readers. The original file is no longer referenced anywhere. |
| 2 | 0:39 | *"estás repitiendo mucho el tema del Premium… las cosas Premium son escasas"* | "Premium" removed from body copy and section headings; kept only where it is the brand. Home went from 19 occurrences to 12, all of them the company name. |
| 3 | 1:03 / 2:36 | *"aquí lo suyo es que este también tuviese algo"* · *"aquí hay una parte vacía"* | Same issue — Juampi Vanella's column was blank while Riki had two bullets. Cursor position at 2:36 confirmed it. **Marked placeholder, not invented copy** — see Deliberately not done. |
| 4 | 1:32 | *"Match Classes… eso qué significa exactamente… lo quitaría"* | He highlighted this bullet four separate times. "Clases partido con análisis real" → "Partidos dirigidos con análisis de vídeo." |
| 5 | 2:00 | *"esto debería estar en el medio, en vez de aquí al lado"* | Cursor was on a card's "+ info" button; all three were left-aligned. Now centred. |
| 6 | 2:06 | *"Learn more, en vez de más info"* | "+ info" → "Saber más" on all three cards. |
| 7 | 2:14 | *"le falta un poco de movimiento… se ve muy estática"* | Blocks rise and fade in as they enter; hero imagery drifts at 12% of scroll speed. No library — ~70 lines. Fully disabled under `prefers-reduced-motion`. |
| 8 | 2:44 | *"esta foto no me gusta"* (Clubs hero) | It was an aerial photograph taken from an aircraft — unrelated to padel. Replaced with the aerial of the club's own courts. |
| 9 | 2:59 | *"para que no seas tú y tú… haciendo algo muy parecido en ambas"* | Two programme cards used near-identical action shots of the same person. Re-assigned so they are no longer adjacent. |
| 10 | 3:10 | *"esta foto es muy fea"* | Generic stock photograph of hands over paperwork on the Consultancy card. Dropped from the build entirely. |
| 11 | 3:52 | *"initial diagnosis… ponerle como un círculo"* | The five numbered steps now sit in outlined circles. |
| 12 | 4:03 | *"estos textos no me gustan… mucho mejor si estos son como unos cuadritos"* | "Programas 100% personalizados" was three slabs of large centred prose. Now three cards matching the rest of the system, label first, claim second, each cut to one sentence. |
| 13 | 4:52 | *"lo suyo es que estuviese 1, 2 y 3, la gente no lee"* | The Camps methodology paragraph named three pillars in prose. Split into numbered **1 Técnico / 2 Táctico / 3 Físico**. |
| 14 | 4:58 | *"metes los emojis… no pega, hay disonancia"* | The four 🎾🏆☀️⚙️ emoji replaced with line icons in circular holders. Zero emoji remain. |
| 15 | 3:26 | *"los textos… suena todo muy pesado"* | Hero and Clubs lead copy tightened, using his own framing (*"aprende de los mejores"*). |
| 16 | 5:20 | *"hay que añadir… testimonios"* | Section built, matching the card system. **Placeholders — see below.** |

## Deliberately not done, and why

**Invented testimonials.** He said *"eso se inventa y ya está"* — just make them
up. Testimonials are statements attributed to identifiable people; writing them
for players who never said them would be fabricating reviews on a commercial
site. The section is built and styled, with three cards that are visibly
unfilled: dashed borders, a "PENDIENTE" tag, and grey placeholder text. It
cannot be mistaken for real quotes if the preview is shared. Three short real
ones from actual players and it is finished — the markup does not change.

**A biography for Juampi Vanella.** Nothing about his background is published
anywhere we can source, and he is a named real person. Two placeholder lines
mark where his trajectory and coaching focus go. Needs two sentences from him.

**Renaming the company.** He said the name *"lo hace ver barato"*. That is his
own brand, on his own logo and domain. The repetition is fixed; the name is a
decision for him, not a change to make unprompted.

## Photography — a real constraint

After dropping the two images he rejected, exactly **one** high-resolution
landscape photograph remains (`hero-home`, 2000×1125) for three hero slots. The
rest of the set is 1170px wide **at source** — that is the resolution in his Wix
account, not something this pipeline degraded. He noticed:
*"la foto esta tiene muy poca resolución."*

He is right, and no processing fixes it. Current assignment uses the best
available image per slot, but **full-resolution originals from his own camera
roll are the only real fix** for the hero bands.

## Validation

Same gates as v1.0, plus the new behaviour:

```
layout audit          8/8 cells clean  (0 sub-15px, 0 overflow, 0 overlap,
                                        0 h-scroll, 0 page errors, 0 4xx/5xx)
route x viewport      12/12 passed     (reports/viewports-v2/)
reveal-on-scroll      8/8 cells        every block opaque when scrolled to
JS disabled           4/4 pages        0 elements stuck invisible
prefers-reduced-motion               0 hidden, hero transform none
mobile menu           4/4 routes       centred, 0px offset, Escape closes
live (real browser)   8/8 cells        email resolves, no old email/phone/Wix
```

### Two bugs found by these gates, both mine

- **Content could be permanently invisible without JavaScript.** `.reveal`
  started at `opacity: 0` and only became visible once JS added a class — so a
  JS failure would have hidden most of every page. Now gated behind a `js` class
  set before first paint, so the CSS floor keeps content visible if scripts
  never run.
- **A fast scroll could leave sections stuck hidden.** IntersectionObserver
  callbacks are batched, and a flick could carry a tall section past the
  viewport without firing. Threshold lowered to 0 and a sweep added to the
  scroll handler, so nothing can remain at `opacity: 0` once it has been passed.

### One correction to the audit itself

The gate was reporting phantom overflow: it measured element bounding boxes,
which do not shrink when an ancestor clips them, so the deliberately
over-scaled hero image looked like a horizontal-scroll bug. It now ignores
clipped elements and asserts the real condition — `documentElement.scrollWidth`
vs `clientWidth`. Re-run against the old v0 recreation as a negative control, it
still reports its 43 sub-15px nodes and 68×140px image overlap, so the fix
removed false positives without weakening it.

---

# v2.1 — second round

Three further requests from the annotated screenshot.

## 1. "¿Qué incluye la experiencia?" centred

The four feature blocks were left-aligned inside their columns. Now centred —
icon, heading and copy — with the paragraph capped at 30ch and centred in its
column so the ragged edges stay symmetrical.

Also fixed while there: the *Descubre Marbella* and *Programas personalizados*
icons were nearly identical, both reading as a sun. The second is now a sliders
mark, which also says "adjustable / made to measure" rather than repeating a
decorative glyph.

## 2. More movement, at different speeds and directions

The previous pass used one uniform rise on every block, which is what made it
feel mechanical. Replaced with a small system:

**Entrances** — elements carry `data-anim` and differ in direction, distance
and duration:

| variant | movement | duration |
| --- | --- | --- |
| `up` / `up-far` | 46px / 82px rise | 1.15s / 1.45s |
| `left` / `right` | 56px lateral + slight lift | 1.3s |
| `scale` | 0.93 → 1 with a short rise | 1.35s |
| `blur` | 7px defocus clearing as it rises | 1.3s |
| `rise` | short 30px lift | 0.95s |
| `fade` | opacity only | 1.5s |

Split sections alternate: on one the copy arrives from the left and the image
from the right, on the next it reverses, so consecutive sections do not repeat
the same gesture.

**Parallax** — `data-parallax="<rate>"` per element, so within a single section
the photograph (0.05–0.06), the copy column (0.02) and the hero card (0.03) all
travel at different speeds. Hero imagery drifts at 0.14. The four Camps features
each carry their own rate (0.03–0.07) so the row breathes instead of sliding as
one slab.

**Smoothness** — a single shared easing curve
(`cubic-bezier(.16,.84,.34,1)`) and long durations, with staggered children
alternating 44px/68px so a row assembles rather than arriving flat.

Below 860px every horizontal entrance becomes vertical — a 56px sideways slide
is most of a phone's width and was pushing content past the viewport edge
before it settled. The layout audit caught that.

## 3. Reviews section

Large section on its own band: centred header, an aggregate score panel, and a
six-card grid with star rows, quote, avatar, name and club. Cards lift slightly
on hover. Two columns on tablet, one on mobile.

**The six cards and the aggregate score are unfilled, on purpose.** A review is
a statement attributed to an identifiable person, and a star average with a
review count is a factual claim about the business — writing either would be
manufacturing evidence, not designing a page. Every slot is visibly pending:
dashed border, outlined stars, a "PENDIENTE" tag, and `—` where the score goes.
Nothing here can be mistaken for a real review if the preview is shared.

Filling one is a five-minute job per card and the markup does not change:
replace the quote, set name and club, put their initial in `.review-avatar`,
adjust the star count, then delete `is-placeholder` and the pending tag. Update
the score and count in the summary panel to match what the real reviews say.

## Validation (v2.1)

```
layout audit        8/8 clean      route x viewport   12/12
reveal-on-scroll    8/8            JS disabled        0 stuck invisible
reduced-motion      0 hidden       mobile menu        0px centre offset
live (browser)      6 review cards, 6 pending, 8 entrance variants,
                    5 parallax layers, 0 stuck, 0 page errors
```

---

# v2.2 — coaches parity, upscaled media, tennis removed

## Coaches section rebuilt

From Riki's voice note (2026-08-01 22:44):

> *"que pongan el texto que está debajo mío, hacer que suba ese texto y luego
> ponen los coaches"* … *"no quiero que haya… el currículum mío… quiero que
> englobe el texto, la idea, hacia los dos"*

The NAC / M3 Academy credentials sat under Riki's photograph, which made him
read as the principal and Juampi as an assistant — and left Juampi's column
empty, the "parte vacía" from the earlier review. Both problems have the same
fix:

- the credentials moved **above** the pair and are written in the **plural**, so
  they describe the academy rather than one person's CV
- both columns are now structurally identical — photo, role, name, flag — with
  nothing under either
- **both labelled `Head Coach`**, which also settles the contradiction on the
  source site, where the eyebrow said "HEAD COACH" but the heading said
  "Premium Coach's"
- national flags as inline SVG (Spain / Argentina). Not emoji — he had already
  rejected emoji elsewhere as clashing with the positioning

Measured parity, desktop and mobile: both columns `512x781` and `350x544`
respectively, identical child counts, identical role labels.

## Media

| Slot | Supplied file | Verdict |
| --- | --- | --- |
| `hero-camps` | `Marbella Upscaled.jpeg` | **Accepted.** 1170×1170 vs 1170×656 — 1.37 MP against 0.77 MP, and a squarer crop carrying more of the scene. Perceptual diff 55/256 confirms it is a different framing, not just a resample. |
| `camps-method` | `riqui upscaled.jpeg` | **Rejected.** Perceptual diff 6/256 — the same photograph, same aspect ratio, at 600×1024 (0.61 MP) against the 1170×1994 (2.33 MP) already on the site. Despite the filename it is roughly a quarter of the pixels. The higher-resolution original was kept. |

Note on the accepted one: the width is unchanged at 1170px, so a full-bleed
desktop hero gains no horizontal sharpness — the gain is vertical crop latitude.

## Tennis references removed

Three occurrences, rephrased rather than excised:

- *"la pasión por el **tenis y el** pádel"* → *"la pasión por el pádel"*
- *"experiencias internacionales de **tenis y** pádel"* → *"…de pádel"*
- *"la escuela de **tenis o** pádel"* → *"la escuela de pádel"*

Zero occurrences of `tenis`/`tennis` remain in any HTML, CSS, JS or JSON,
including alt text and metadata. These are the two lines previously restored for
fidelity; the client's instruction supersedes that, and the source site is now
the inconsistent one.

## Open question

The brief spelled the second coach **"juanmi"**; his own live site says
**"Juampi Vanella"**. The site's spelling was kept. Worth confirming.

## Validation

```
layout audit      8/8 clean        reveal-on-scroll   8/8
coach parity      identical geometry, desktop + mobile
tennis refs       0 across html/css/js/json
```
