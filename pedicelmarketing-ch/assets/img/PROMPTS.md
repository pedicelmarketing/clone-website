# Scene images — prompts and slots

AI-generated scene imagery for pedicelmarketing.ch (Task 5, 2026-10-06). People shown are not real and are not staff; never caption them with a name or use them as testimonials.

**Model:** Z-Image Turbo (`z_image_turbo_bf16.safetensors`) on Comfy Cloud via a hand-built API workflow: UNETLoader → ModelSamplingAuraFlow (shift 3) → KSampler (8 steps, cfg 1, euler/simple), CLIPLoader `qwen_3_4b.safetensors` (type `lumina2`), VAELoader `ae.safetensors`, ConditioningZeroOut as negative, EmptySD3LatentImage, SaveImage. No paid API nodes; GPU time only.

**Post-processing:** Pillow → WebP q82 (method 6), downscaled to ~2x the rendered slot width. Small pseudo-logos on laptop lids were blurred out by hand in `team-strategy-whiteboard`, `team-content-video-shoot` and on the bezel in `about-remote-video-call`.

Rendered sizes measured with Playwright at 1440 px wide (`/en/`, `/en/about/`).

## Slots

| Page / slot | Before | Rendered | After | File size px | Seed | Intent |
|---|---|---|---|---|---|---|
| about `/about/` — "The team" tile 1 (Strategy & ads) | `Team 3.webp (600x660 stock portrait)` | 361x397 | `team-strategy-whiteboard.webp` | 720x796 | 101 | Strategy work at a whiteboard |
| about — "Three disciplines, one Hub" tile 2 (Content & motion video) | `Team 4.webp (600x660 stock portrait)` | 361x397 | `team-content-video-shoot.webp` | 720x796 | 201 | Small video shoot, camera on tripod |
| about — "Three disciplines, one Hub" tile 3 (Web, search & data) | `Team 5.webp (600x660 stock portrait)` | 361x397 | `team-web-data-review.webp` | 720x796 | 201 | Reviewing performance charts on a screen |
| about — "How it all started" gallery left | `image 30.png (blurred person, brand gradient)` | 566x547 | `about-remote-video-call.webp` (v2, fix round 1) | 1024x992 | 401 (homeoffice-v2) | 2020: companies move online — video call from home office |
| about — "How it all started" gallery right | `image 31.png (street billboard, passer-by)` | 566x547 | `about-wireframe-sketching.webp` | 1024x992 | 201 | Early days: two people sketching wireframes |
| about — "Today ... Swiss SMEs" gallery left | `image 27.webp (two women with a phone)` | 566x451 | `about-client-meeting.webp` | 1132x906 | 302 | Client meeting at a table |
| about — "Today ... Swiss SMEs" gallery right | `image 26.webp (hands on laptop)` | 566x451 | `about-content-review.webp` | 1132x906 | 201 | Reviewing content on a screen |
| about — "Giving back" gallery left | `pexels-cottonbro-studio-5082575 1.webp (stock: people with food)` | 566 wide (grid half, cover) | `about-still-school-supplies.webp` (fix round 1, objects only) | 1132x906 | 501 (still-school-supplies) | Still life, no people |
| about — "Giving back" gallery right | `dwq.webp (classroom of children)` | 566 wide (grid half, cover) | `about-still-tea-notebook.webp` (fix round 1, objects only) | 1132x906 | 401 (still-tea-notebook) | Still life, no people |
| home `/` — services tab "Outbound" (also `/services/` same tab) | `new ones-29.png (man with headphones)` | 473x487 (home), 574 max (services) | `home-outbound-desk.webp` | 946x976 | 201 | Outreach: reading a reply on a laptop |

Skipped on purpose: brand mockups and client work (`first section-19..23`, Yiza billboard), process/tab images that show only hands, the brand-film thumbnail (`lightbox-pedicel`), logos, icons. Audit and contact pages have no people photos.

## Shared style suffix (appended to every prompt)

> Photorealistic candid editorial photograph, natural soft daylight from large windows, modern Swiss office interior with light oak wood, pale concrete and white walls, calm neutral colour grade with cool whites and a subtle lavender accent, 35mm lens, shallow depth of field, natural skin texture, relaxed genuine expressions, nobody looks at the camera. Laptops and screens are plain and unbranded. No text, no lettering, no logos, no signs, no flags.

## Prompts

### team-strategy — 912x1008

> A woman in her mid forties with shoulder-length light brown hair, wearing a grey knit sweater, stands at a large whiteboard in a bright Zurich office and draws arrows between simple empty boxes with a marker, plain pastel sticky notes without writing next to them. A younger colleague with short dark-blond hair, seated at a light oak table beside her with an open laptop, watches and thinks. Through the window, soft city rooftops.

### team-content — 912x1008

> A small video shoot in a bright studio in Lausanne. In the foreground a man in his thirties with short dark-blond hair and a trimmed beard, wearing a navy t-shirt, looks at the flip screen of a mirrorless camera mounted on a tripod. He is filming a woman with auburn hair in a cream blouse who sits on a wooden stool in the background and speaks naturally, lit by a soft LED light panel. Large windows behind, with a faint hint of a lake and hills far away.

### team-web — 912x1008

> A man in his late fifties with short grey hair and thin-rimmed glasses and a young woman with a blonde ponytail sit side by side at a light oak desk in a quiet modern office, looking at a large monitor that shows abstract colourful line and bar charts without any readable labels. She points at the screen, he leans in with interest. A coffee cup and a notebook on the desk.

### started-homeoffice — 1024x992

> A woman in her mid thirties with dark brown hair tied back, wearing a soft lavender sweater, works from a bright home office on a laptop, taking part in a video call; the laptop screen faces away from the camera. Plants on the windowsill, a mug on the light wood table. Through the window, a distant view of green Alpine foothills.

### started-sketching — 1024x992

> A man and a woman in their early thirties sit at a light wood table in a small bright studio space and sketch simple website wireframe boxes on large sheets of paper, a laptop and coffee cups beside them. He has wavy medium-brown hair and rolled-up shirt sleeves, she has short ash-blonde hair and a denim shirt. Concentrated, collaborative, early morning light.

### today-client-meeting — 1280x1024

> A client meeting at a long light oak table in a modern meeting room in Zurich. A business owner in his sixties with white hair and a blue blazer listens while a female consultant in her forties with chestnut hair shows him something on a tablet, and a younger male colleague with dark hair takes notes in a paper notebook; a closed plain matte grey laptop without any emblem lies on the table. Glass wall and large window with soft daylight, a plant in the corner.

### today-content-review — 1280x1024

> A woman in her late twenties with light blonde hair in a loose bun, wearing a white shirt, sits at a tidy desk in a calm studio office and reviews a grid of colourful photo thumbnails on a large monitor, holding a cup of coffee, a colleague with curly dark hair leaning over her shoulder to look. The photos on screen are abstract and contain no text.

### giving-supplies — 1280x1024

> Volunteers sorting donated school supplies in a bright community hall: four adults of different ages, a grey-haired woman, a young man with a red-blond beard, a woman with black hair and a middle-aged man, place notebooks, pencils, rulers and small backpacks into plain unmarked cardboard boxes on long wooden tables. Friendly, busy, natural light from tall windows.

### giving-language-cafe — 1280x1024

> An informal language and culture evening in a bright community room: small groups of adults of different backgrounds sit at simple wooden tables with tea cups, chatting and laughing, one woman explains something with her hands. Warm late-afternoon daylight through large windows, plants, relaxed and welcoming atmosphere.

### outbound-desk — 1008x1040

> A woman in her late twenties with dark hair in a bun, wearing a light blue shirt, sits at a light oak desk in a bright Swiss office with wireless headphones around her neck, smiling as she reads a message on her laptop; the laptop screen faces away from the camera. A notebook and a glass of water on the desk, a window with a softly blurred lake view behind her.
Notes on prompt versions:
- `team-strategy` (seed 101) was the first test run, made before the sentence "Laptops and screens are plain and unbranded." was added to the style suffix.
- `today-client-meeting`: seed 201 used "...takes notes on a laptop." and was rejected (an Apple-style logo on the laptop lid). The prompt above is the revised one; seed 301 still showed a faint lid logo, seed 302 was used.

## Rejected

| Image | Why |
|---|---|
| today-client-meeting, seed 201 | Apple-style logo on the laptop lid |
| today-client-meeting, seed 301 | faint logo on the laptop lid again |

## Fix round 1 (review rulings, 2026-10-06)

Same model and workflow (Z-Image Turbo, 8 steps, cfg 1). Service-page scenes use a stronger Swiss style suffix (Central-European features, varied clothing, Zurich/Lausanne interiors and rooftops).

### New service-page slots

| Page(s) / slot | Before | Slot ratio | After | px | Seed |
|---|---|---|---|---|---|
| paid-ads — intro image (`.image`, max 600 px) | `Ebooks-5.webp` | 1200x1360 | `svc-paid-ads-cards.webp` | 960x1088 | 401 |
| paid-ads — wide image (`.image-project-big`) | `pexels-monstera-5273652-2-4.webp` (picnic) | 1404x800 | `svc-paid-ads-team-screen.webp` | 1404x804 | 401 (laptop-lid logo blurred out) |
| outbound + seo-ai-visibility — intro image | `image-26-3.webp` | 1200x1360 | `svc-outbound-headset.webp` | 960x1088 | 401 |
| ai-content-video + hub — intro image | `Ebooks.webp` | 1200x1360 | `svc-content-phone-gimbal.webp` | 960x1088 | 401 |
| ai-content-video + hub — wide image | `pexels-monstera-5273652 3.webp` | 1404x800 | `svc-content-video-edit.webp` | 1404x804 | 501 (monitor-bezel mark blurred out) |
| web-tracking — intro image | `Ebooks-4.webp` | 1200x1360 | `svc-web-tracking-screens.webp` | 960x1088 | 401 |

Kept as they are (per ruling): images showing only hands, the Oyiza billboard, the brand-film thumbnail, `new-26`, and the hands-on-laptop `pexels-monstera-5273667-*` wide images on outbound, SEO and web-tracking.

### Style suffix for service scenes

> Photorealistic candid editorial photograph, natural soft daylight, calm neutral colour grade with cool whites and a subtle lavender accent, 35mm lens, shallow depth of field, natural skin texture, relaxed genuine expressions, nobody looks at the camera. The people have Central-European features. Laptops, phones and screens are plain and unbranded and show only abstract shapes. No text, no lettering, no logos, no signs, no flags.

### Style suffix for still lifes

> Photorealistic still-life photograph, no people, no hands. Natural light, calm colour grade with cool whites and a subtle lavender accent, shallow depth of field. No text, no lettering, no logos, no labels.

### Prompts (final versions)

#### homeoffice-v2 — 1024x992

> A woman in her mid thirties with dark brown hair tied back, wearing a soft lavender sweater, sits at a light wood table in a bright home office during a video call. The camera is behind her laptop, so only the back of the plain laptop lid is visible, and we see her face from the front-left as she listens and smiles slightly, looking at her screen. Plants on the windowsill, a mug on the table. Through the window behind her, a distant view of green Alpine foothills.

#### still-school-supplies — 1280x1024

> A neat stack of new school exercise books with plain solid blue, green and yellow covers without any printing, sharpened pencils in a glass jar, a few erasers and a small plain navy backpack on a light oak table by a window, soft morning daylight.

#### still-tea-notebook — 1280x1024

> Two ceramic cups of tea, a simple glass teapot and an open notebook with blank pages and a pen on a wooden table, warm late-afternoon light through a window, a green plant softly blurred in the background.

#### svc-paid-ads — 960x1088

> A marketing manager in her early forties with short ash-blonde hair, wearing a navy blazer over a white t-shirt, stands at a high table by a large window in a Zurich office and compares two printed cards with colourful abstract ad designs, a laptop open beside her. Through the window, Zurich old-town rooftops with green copper roofs and church spires, softly out of focus.

#### svc-outbound-seo — 960x1088

> A man in his mid thirties with short light-brown hair and a neat beard, in a light grey button-down shirt, sits at a light oak desk in a bright Lausanne office wearing a small headset and writes notes in a notebook, a laptop open beside him. Behind him a large window with a view over terracotta rooftops down to Lake Geneva and distant mountains, softly blurred.

#### svc-content-hub — 960x1088

> A young woman with long straight dark-blonde hair, wearing a rust-coloured overshirt over a black top, films a ceramic coffee cup on a light wood table with a smartphone on a small handheld gimbal, in a bright Zurich studio with white-painted brick walls and a soft LED light panel at the side.

#### svc-web-tracking — 960x1088

> A woman in her fifties with a grey bob and round glasses, in a dark green linen shirt, stands at a standing desk with two monitors showing abstract website layouts and simple coloured charts and points at one screen, while a young man with a dark-blond undercut in a white t-shirt and denim jacket looks on. Modern office with an exposed concrete ceiling and large windows over Zurich rooftops.

#### svc-paid-ads-wide — 1536x880

> Three colleagues in a bright Zurich meeting room with floor-to-ceiling windows overlooking the city rooftops and a hint of the lake: a woman with red hair in a mustard blouse, a tall man in his forties with a shaved head in a black polo shirt and a young woman with brown curly hair in a blue striped shirt stand around a large wall screen showing abstract colourful tiles and bar charts and discuss them, all three looking at each other or at the screen; nobody holds a laptop and there are no laptops in the room.

#### svc-content-wide — 1536x880

> A video editing session in a creative studio in Lausanne: a man in his late twenties with tousled blond hair and a black t-shirt sits at a desk in front of a large monitor showing an abstract video timeline of coloured blocks, and a woman in her thirties with chestnut hair in a crisp white shirt leans in beside him and points at the screen, both of them looking at the monitor. The monitor shows only coloured blocks, no people and no video frames. A window shows rooftops sloping down toward Lake Geneva.

### Rejected in fix round 1

| Image | Why |
|---|---|
| svc-paid-ads-wide, seed 401 (original prompt) | Apple-style logo on a laptop. Kept anyway and blurred the logo out, after both retries were worse |
| svc-paid-ads-wide, seed 501 | the same man appears twice, plus laptop logos |
| svc-paid-ads-wide, seed 502 | laptop-lid logos on two laptops |
| svc-content-wide, seed 401 (original prompt) | woman stares into the camera; monitor shows people in the video preview |
| svc-content-wide, seed 502 | figure visible in the monitor preview |
| still-school-supplies, seed 401 (original prompt) | ruler with garbled digits; 'exercise books' read as printer paper |
| homeoffice-v2, seed 402 | fine, but seed 401 fits the slot better (front view, plain lid) |
| about-remote-video-call v1 (seed 201) | a second face looked out from the laptop screen (review ruling) |
