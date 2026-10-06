# pedicelmarketing.ch — English copy deck

6 October 2026 · Task 4a (fix round 1 applied) · Source of the English template pages in `pages/`. DE/FR are translated from this (Task 4b).

## Positioning in 5 lines
1. Pedicel is an AI-first growth agency for Swiss SMEs.
2. One team works in German, French and English, so one partner covers both language regions.
3. Six services: AI content & motion video, paid ads, SEO + AI visibility (GEO), outbound (LinkedIn, plus WhatsApp to opted-in customers), web & tracking, and the client Hub.
4. Everything runs through one Hub: a manager checks every piece; the client approves content and ads (outreach messages are approved by our manager); the system learns from the client's decisions.
5. Every call to action is "Get a free AI audit" (`/audit`) or "Book a call" (`/contact`). No prices, no cold email.

## What was removed, and why
| Removed | Where | Why |
|---|---|---|
| "100% of the brands … within 6 months", "1000+ leads", "#3 / top 3 SEO rankings", "60%+ brand awareness" (the whole number block) | Home, Services, About, Contact | No source (offering.md §6: "no source"). Now in `checks.py` FORBIDDEN. |
| "over 30 years", "80+ successful projects" | Home, Services, Portfolio | No source. Now forbidden. |
| "Chelsey" | About (LISA) | No named staff who can't be shown; now "a team member". Sergio stays (founder, board member). |
| Hype and filler: "magic", "obsessed", "revolutionizing", "wizards", "digital symphony", "unprecedented heights", "leading provider", "construction giant" | All pages | Tone rules; also unprovable superlatives. |
| Outcome claims in case studies ("resulting in increased … repeat business", "measurable increase in ROI", "ascended to the forefront … industry leader", "propelled … to the forefront") | COEO, ISN, SANA | No numbers or lift claims in case studies; offering.md: "no conversion lifts". Case studies now say what the client asked for and what we did. |
| "within 48 hours" audit delivery | Audit | Not in any source. Now: "a team member reviews it before we email it" (form handler: pitch is sent after a manager's OK). |
| "free 30-minute consultation" | Footer CTA, Audit | Length not sourced; now "a free call" / "Book a call". |
| Old service names (Lead Generation, Brand Presence, Development, Social Media) | Tabs, cards, service pages | Replaced by the six pillars (offering.md §3 old → new). |
| Copy that promised email marketing | Home/Services tab 1 | Cold email is undecided; outbound copy mentions LinkedIn and WhatsApp only. |
| Phone calls in outbound | Home/Services tab 1, Outbound page, Portfolio card, meta | Ruling (fix round 1): Swiss rules on sales calls not checked yet. LinkedIn + WhatsApp (opted-in only) stay. |
| "proven hooks", "tested hooks", "analyzer" | AI content, Paid ads, Portfolio | Not proven by any result; now "analysed hooks" / "hook mechanics we have analysed" / "analysis tool". |
| "in Figma", "captions", "rendered in code", competitor ads "on Meta and Google" | Web, AI content, Paid ads | Not sourced; competitor-ad research is the Meta Ad Library only. |
| Efficacy verbs: "the better it fits", "every decision improves the next piece", "Every message is personal", "and next to whom", "so you show up well in local search", "Be found on Google…" | Hub, AI content, Outbound, SEO | Implied results; now "learns from your decisions", "your decisions guide the next piece", "written for the lead from a research brief", "Search and AI answers, handled". |
| "You approve everything" / "Nothing goes live without your OK" | Home, Hub | Client approval covers content and ads; outreach is approved by our manager. |
| Values "Trintegrity", "Fail fast", "Mistakes are fine", "Not everything will be perfect", "Sabai Sabai", "We walk our talk" | About | Tone for Swiss buyers; now Transparency, Care, Partnership, Clarity, Reliability. |

Also fixed: hours "Monday to Friday, 08:00–16:00 (CET)"; GEO explained once on the SEO page; British spelling; "Reach the people who buy" used in both places; portfolio "Six services" block now has all 6 cards (SEO + AI visibility and The Hub added); meta titles ≤ 60 and descriptions ≤ 155 characters; footer address "Lõõtsa tn 5", copyright "© 2026 Pedicel Marketing OÜ", "Kellog's" → "Kellogg's", form success/error and "Please wait..." texts, all meta titles and descriptions.

## Claims and their sources
| Claim on the site | Source |
|---|---|
| LinkedIn from the client's team profiles; a manager approves every send | offering.md §2.4 "Client gets" |
| WhatsApp reminders (bookings, reorders) | offering.md §2.4 "Client gets" |
| WhatsApp only to opted-in customers (no phone calls — ruling) | offering.md §5 "WhatsApp: opted-in customers only" |
| Research brief per lead, one CRM | offering.md §2.4 "Our edge" (Apollo + AI research brief, Hub Sales CRM) |
| 3,450 analysed hooks, 35 scored mechanics, reference clip, "the score ranks, it never forecasts" | offering.md §2.1 "Our edge" |
| Voiceover in German, French, English; motion graphics | offering.md §2.1 "Client gets" |
| An analysis tool rates the Inspiration feed (examples from brands we track) | offering.md §2.1 "Our edge"; MEM feed-sources-repair (tracked accounts) |
| Meta + Google Search, retargeting, budget paid direct, no markup | offering.md §2.2 "Client gets" |
| Competitor ads on Meta (Meta Ad Library sweep, days live); per-ad results to learn which hook won | offering.md §2.2 "Our edge" |
| ChatGPT Ads open in Switzerland; we *propose* a test (never claim we ran one) | offering.md §2.2 "ChatGPT Ads" + "Do not claim" |
| Technical SEO and speed, schema, Google Business Profile, monthly AI-answer tracking (ChatGPT, Gemini, Perplexity, Google AI), fixed question panel | offering.md §2.3 |
| GA4, Consent Mode, cookie consent, Meta CAPI, UTMs, PostHog; multilingual sites and landing pages | offering.md §2.5 |
| Hub: requests (files + voice, completeness check), approvals with video comments, calendar, analytics + AI copilot, brand score, inspiration feed; manager approves before the client sees anything; learning loop; brand rules scored | offering.md §2.6 |
| ISN: motion-graphic reels, explainers, 3D product film | offering.md §2.1 "Proof" |
| ISN: live Hub at hub.pedicelmarketing.com; 12-month audit of 730 posts (no lift claim) | offering.md §2.6 "Proof", §6; dispatch ruling 5 |
| One trilingual team for Swiss SMEs | competitors/ch/summary.md gap 1; operator-approved positioning |
| Free audit: AI visibility, competitors, their ads and search, ~5 fixes, short motion video; reviewed by a person before sending | spec "Free audit" row; `pedicelmarketing/deploy/form_handler.py` (`request_pitch`: "sent after a manager's OK") |
| Privacy: video embeds via YouTube/Embedly | page code (lightbox JSON: youtube.com, cdn.embedly.com, i.ytimg.com) |

Not used, on purpose: persona-panel predictions, brand-judge 95 %, any La Cabrera / Leo Foods audit figures (proposals, not clients), in-house film crew, "#1 on Maps", FAQ rich results.

## Open points for the operator
1. **Privacy policy is a draft for counsel review.** GDPR applies directly (Estonian controller); FADP for Swiss visitors. The notice:
   - names a legal basis per purpose (Art. 6(1)(b) forms and audit, (f) follow-up, security and analytics where no consent is needed, (a) consent where required, (c) legal records);
   - says audit requests are processed with AI model providers and company-data providers (categories only);
   - lists every tool the page code loads: Google Analytics/Google tag, **PostHog (US host `us.i.posthog.com`)**, **Meta Pixel**, the **Apollo.io website tracker** and **YouTube/Embedly** (video lightbox), plus Supabase and Brevo for the forms.

   There is no cookie banner, so the trackers fire without consent. Decide: remove PostHog/Meta/Apollo from the .ch pages, or add a consent banner (offering.md §5 "consent platform before any pixel").
   **For counsel:** real retention periods (now generic), the Supabase region (not verified, not stated), and whether the analytics basis holds without a banner.
2. **Footer "Offices: West Africa — Lagos, Abuja; Europe — Estonia"** kept from the .com. Confirm these are still true and wanted on a Swiss site.
3. **Phone hours** "Monday to Friday, 08:00–16:00 (CET)": the hours come from the .com; "CET" was added in fix round 1. Confirm.
4. **"One team in German, French and English"** is the approved positioning; the phone is a Spanish (+34) number. Make sure a German or French caller gets an answer.
5. **Phone calls removed from outbound** (fix-round ruling): Swiss rules on sales and cold calls have not been checked. Re-add calls only after that check.
6. About page keeps the 2020 founding story, the three community projects (Oyiza, Ukraine/Sergio, LISA). The values are new (Transparency, Care, Partnership, Clarity, Reliability). Confirm they still hold.

Key: **H1/H2/H3** headings · **H4** small headings · **Tab** tab label · **Card** project-card subtitle · **Label** category tag · **Button** link or button · *placeholder / data-wait / submit* form texts.

## Pages

### Home — `/`

*Meta title:* AI Marketing Agency for Swiss SMEs | Pedicel Marketing  
*Meta description:* AI-first marketing agency for Swiss SMEs: content, video, ads, SEO, AI visibility and outreach in one client Hub. German, French, English.

- **H1** AI-first growth for Swiss SMEs
- One team in German, French and English. Content, ads, search and outreach, run from one Hub that learns from every approval.
- **Button** Get a free AI audit
- **Tab** Outbound
- **Tab** Content & video
- **Tab** Web & tracking
- **Tab** Paid ads
- **Tab** SEO + AI
- **Tab** The Hub
- Reach the people who buy
- **H2** Outbound
- We find the companies and decision-makers you want to reach, then contact them on LinkedIn from your own team's profiles. A manager approves every message before it is sent. Where it fits, we add WhatsApp reminders for customers who have opted in.
- LinkedIn and WhatsApp outreach, run for you.
- **Button** Learn more
- Content people stop for
- **H2** AI content & motion video
- Short videos, motion graphics and posts for LinkedIn, Instagram and TikTok, with voiceover in German, French or English. Every opening uses a named hook mechanic from our database of 3,450 analysed hooks. You approve each piece in your Hub before it goes live.
- Video and posts, made faster with AI.
- **Button** Learn more
- Know where every enquiry comes from
- **H2** Web & tracking
- Fast websites and landing pages in German, French and English, built to turn visits into enquiries.
- We set up GA4, Consent Mode, cookie consent, the Meta Conversions API and UTMs, so you can see which channel brought each lead.
- Websites and landing pages that measure.
- **Button** Learn more
- Learn which ad wins
- **H2** Paid ads
- Meta and Google Search campaigns, with retargeting for people who already know you. We read the results ad by ad to learn which hook works, and use it in the next round.
- Your budget goes directly to the platforms. We add no markup.
- Meta and Google, plus an optional ChatGPT Ads test.
- **Button** Learn more
- Are you in the answer?
- **H2** SEO + AI visibility
- When someone asks ChatGPT, Gemini, Perplexity or Google for a company like yours, are you named?
- We fix technical SEO and page speed, keep your Google Business Profile current, and check every month how AI answers describe you, with the same set of questions.
- Google search and AI answers, in one service.
- **Button** Learn more
- Everything in one place
- **H2** The Hub
- Your own client portal. Send requests, approve or reject content and ads, see the calendar and the numbers, and ask the AI copilot about your results. The system learns from your decisions, and they guide the next draft.
- Your portal for requests and approvals.
- **Button** Learn more
- **H2** Senior judgement, AI speed
- Strategists, content makers and engineers who let AI do the repetitive work, so our time goes into ideas and decisions.
- We work in German, French and English, so one team can cover your whole market. You see every draft, every approval and every result in one place.
- **Button** See our services
- **H1** Selected work
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **H4** One team, three languages
- Strategy, content, ads and outreach in German, French and English. No hand-offs between agencies.
- **H4** You approve content and ads
- No post, video or ad goes live without your OK. Outreach messages are checked by a manager on our side.
- **H4** It learns from you
- Each approval and rejection becomes a pattern for the next piece, and every draft is checked against your brand rules.
- **H4** Get your free AI audit
- See how ChatGPT, Gemini, Perplexity and Google describe your business, what your competitors do in ads and search, and about five fixes you can make now. Plus a short motion-graphic video. Free.
- **Button** Get a free AI audit
- **H2** How we work
- **H4** Audit
- We start with your free AI audit: your visibility in search and AI answers, your competitors and their ads.
- **H4** Goals
- We agree on a few clear goals, such as enquiries, bookings or orders, and on how we will measure them.
- **H4** Plan
- We choose the channels that fit your market and language regions, and plan the first month in your Hub calendar.
- **H4** Make and approve
- We produce the content, ads and outreach. A manager checks every piece, and you approve content and ads in the Hub.
- **H4** Learn and improve
- Every approval, rejection and result feeds the next round. You see the numbers in the Hub and can ask the AI copilot about them.

### Services — `/services/`

*Meta title:* Marketing Services for Swiss SMEs | Pedicel Marketing  
*Meta description:* Six services, one team: AI content and video, paid ads, SEO and AI visibility, outbound, web and tracking, and the client Hub.

- **H1** Six services, one team
- Choose one service or combine them. Everything runs through your Hub, in German, French or English.
- **Tab** Outbound
- **Tab** Content & video
- **Tab** Web & tracking
- **Tab** Paid ads
- **Tab** SEO + AI
- **Tab** The Hub
- Reach the people who buy
- **H2** Outbound
- We find the companies and decision-makers you want to reach, then contact them on LinkedIn from your own team's profiles. A manager approves every message before it is sent. Where it fits, we add WhatsApp reminders for customers who have opted in.
- LinkedIn and WhatsApp outreach, run for you.
- **Button** Learn more
- Content people stop for
- **H2** AI content & motion video
- Short videos, motion graphics and posts for LinkedIn, Instagram and TikTok, with voiceover in German, French or English. Every opening uses a named hook mechanic from our database of 3,450 analysed hooks. You approve each piece in your Hub before it goes live.
- Video and posts, made faster with AI.
- **Button** Learn more
- Know where every enquiry comes from
- **H2** Web & tracking
- Fast websites and landing pages in German, French and English, built to turn visits into enquiries.
- We set up GA4, Consent Mode, cookie consent, the Meta Conversions API and UTMs, so you can see which channel brought each lead.
- Websites and landing pages that measure.
- **Button** Learn more
- Learn which ad wins
- **H2** Paid ads
- Meta and Google Search campaigns, with retargeting for people who already know you. We read the results ad by ad to learn which hook works, and use it in the next round.
- Your budget goes directly to the platforms. We add no markup.
- Meta and Google, plus an optional ChatGPT Ads test.
- **Button** Learn more
- Are you in the answer?
- **H2** SEO + AI visibility
- When someone asks ChatGPT, Gemini, Perplexity or Google for a company like yours, are you named?
- We fix technical SEO and page speed, keep your Google Business Profile current, and check every month how AI answers describe you, with the same set of questions.
- Google search and AI answers, in one service.
- **Button** Learn more
- Everything in one place
- **H2** The Hub
- Your own client portal. Send requests, approve or reject content and ads, see the calendar and the numbers, and ask the AI copilot about your results. The system learns from your decisions, and they guide the next draft.
- Your portal for requests and approvals.
- **Button** Learn more

### Outbound — `/outbound/`

*Meta title:* B2B Outbound: LinkedIn and WhatsApp | Pedicel Marketing  
*Meta description:* LinkedIn outreach from your team's profiles and WhatsApp reminders for opted-in customers. A manager approves every message.

- **Eyebrow** OUTBOUND
- **H1** Reach the people who buy
- LinkedIn and WhatsApp outreach, run by one team.
- **Button** Get a free AI audit
- **H2** Outbound
- We research your market and build a list of the companies and people you want to reach, with a short research brief on each one. Then we write to them on LinkedIn from your own team's profiles, at a steady daily pace. A manager approves every message before it is sent. We keep every lead and every reply in one CRM, so you always know where each conversation stands.
- **H4** From your own profiles
- Messages go out from your team's LinkedIn profiles, so prospects talk to you, not to an agency.
- **H4** Every message approved
- A manager checks each message before it goes out. No mass messages, no surprises.
- **H4** WhatsApp, opted-in only
- Where it fits, we add WhatsApp reminders, for example for bookings or reorders. They go only to customers who have opted in.
- **H2** Start with a free AI audit
- **Button** Get a free AI audit
- **H4** Not sure what you need?
- Book a call. We listen first, then suggest the services that fit your goals.
- **Button** Book a call
- **H1** Selected work
- Recent projects for clients in Europe and Africa.
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- **H2** How it works
- Three steps that repeat every week.
- **H3** 1. Research
- We define your ideal customer and build the list: companies, decision-makers and a short research brief on each one.
- **H3** 2. Reach out
- We connect and write on LinkedIn from your team's profiles. Each message is written for the lead, from a research brief.
- **H3** 3. Hand over
- When someone is interested, we pass the lead to you with the full conversation, ready for the next step.

### AI content & motion video — `/ai-content-video/`

*Meta title:* AI Content & Motion Video for SMEs | Pedicel Marketing  
*Meta description:* Short videos, motion graphics and posts in German, French and English, built on 3,450 analysed hooks. You approve each piece.

- **Eyebrow** AI CONTENT & MOTION VIDEO
- **H1** Content made for your audience
- Short videos, motion graphics and posts, in German, French and English.
- **Button** Get a free AI audit
- **H2** AI content & motion video
- **H2** Every opening has a reason
- We make short videos, motion graphics and posts for LinkedIn, Instagram and TikTok, with voiceover in German, French or English. Each opening uses a named hook mechanic from our database of 3,450 analysed hooks and 35 scored mechanics, with a reference clip. The score ranks ideas. It never promises views.
- **H4** Motion graphics
- Explainers and product films, clear and on brand.
- **H4** Built on analysed hooks
- Every opening names its hook mechanic and a reference clip, so you can see the idea behind it.
- **H4** Your voice, three languages
- Voiceover in German, French or English, checked against your brand rules.
- **H2** Start with a free AI audit
- **Button** Get a free AI audit
- **H4** Not sure what you need?
- Book a call. We listen first, then suggest the services that fit your goals.
- **Button** Book a call
- **H1** Selected work
- Recent projects for clients in Europe and Africa.
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- **H2** How it works
- From idea to approved post in four steps.
- **H3** 1. Inspiration
- We study what works. Our analysis tool rates example videos from brands we track, in the Inspiration feed of your Hub.
- **H3** 2. Script and hook
- We write the script and choose the hook. You see the idea before anything is produced.
- **H3** 3. Production
- We produce the video or post with AI tools and motion graphics.
- **H3** 4. Approval
- A manager checks it first. Then you approve, reject or comment in the Hub, and your decisions guide the next piece.

### Web & tracking — `/web-tracking/`

*Meta title:* Websites, Landing Pages & GA4 Tracking | Pedicel  
*Meta description:* Fast multilingual websites and landing pages, with GA4, Consent Mode, cookie consent, the Meta Conversions API and UTMs.

- **Eyebrow** WEB & TRACKING
- **H1** A website that shows what works
- Fast sites and landing pages, with tracking you can trust.
- **Button** Get a free AI audit
- **H2** Web & tracking
- We build fast websites and landing pages in German, French and English. Then we set up the measurement: GA4, Consent Mode, a cookie banner, the Meta Conversions API, UTMs and product analytics. So you can see which channel brought each enquiry.
- **H4** Fast and findable
- Clean code, quick load times and a structure that search engines and AI assistants can read.
- **H4** Multilingual
- German, French and English versions with the right language tags, so each region finds its own page.
- **H4** Measured properly
- GA4, Consent Mode, the Meta Conversions API and UTMs, so you can trace leads back to the channel that brought them.
- **H2** Start with a free AI audit
- **Button** Get a free AI audit
- **H4** Not sure what you need?
- Book a call. We listen first, then suggest the services that fit your goals.
- **Button** Book a call
- **H1** Selected work
- Recent projects for clients in Europe and Africa.
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- **H2** How it works
- Three steps from brief to a live, measured site.
- **H3** 1. Plan
- We map who your visitors are, what they need to find, and which actions count as a lead.
- **H3** 2. Design
- We design the pages, so you can review the layout before we build.
- **H3** 3. Build and measure
- We build the site, connect your tracking and consent tools, and check that every form and event reports correctly.

### Paid ads — `/paid-ads/`

*Meta title:* Google Ads & Meta Ads for SMEs | Pedicel Marketing  
*Meta description:* Meta and Google Search campaigns with retargeting. Your budget goes directly to the platforms, with no markup.

- **Eyebrow** PAID ADS
- **H1** Ads that learn what works
- Meta and Google campaigns, with your budget paid directly to the platforms.
- **Button** Get a free AI audit
- **H2** Paid ads
- We run Meta and Google Search campaigns, with pixel retargeting for people who already know you. Before we start, we look at the ads your competitors run on Meta, and how long they keep them live. During the campaign we read the results for each ad, learn which hook won and use it in the next round. Your ad budget is paid directly to Meta and Google. We add no markup.
- **H4** No markup
- Your budget is paid directly to the platforms. You see exactly what each campaign spends.
- **H4** Competitor research
- We check the Meta Ad Library to see which ads your competitors run and how long they keep them.
- **H4** Optional ChatGPT Ads test
- ChatGPT Ads are now open to advertisers in Switzerland. If they fit your market, we can propose a small test. It is optional.
- **H2** Start with a free AI audit
- **Button** Get a free AI audit
- **H4** Not sure what you need?
- Book a call. We listen first, then suggest the services that fit your goals.
- **Button** Book a call
- **H1** Selected work
- Recent projects for clients in Europe and Africa.
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- **H2** How it works
- Four steps, then we repeat what works.
- **H3** 1. Audience
- We define who should see your ads, by region, language and interest.
- **H3** 2. Competitor ads
- We review the ads your competitors run on Meta, and how long they keep them live.
- **H3** 3. Creative
- We build the ads from hook mechanics we have analysed, in German, French or English, and you approve them in the Hub.
- **H3** 4. Learn
- We read the results ad by ad, keep what wins and replace what does not.

### SEO + AI visibility — `/seo-ai-visibility/`

*Meta title:* SEO & AI Visibility (GEO) | Pedicel Marketing  
*Meta description:* Technical SEO, Google Business Profile and monthly tracking of how ChatGPT, Gemini, Perplexity and Google AI mention you.

- **Eyebrow** SEO + AI VISIBILITY
- **H1** Search and AI answers, handled
- Technical SEO, Google Business Profile and monthly AI-answer tracking.
- **Button** Get a free AI audit
- **H2** SEO + AI visibility
- Your customers look for suppliers on Google and in AI assistants. We work on both. The AI part is sometimes called GEO, generative engine optimisation. We fix the technical basics and page speed, keep your Google Business Profile up to date, and publish content that answers real questions. Every month we ask ChatGPT, Gemini, Perplexity and Google AI the same set of questions about your market, and report whether and how you appear.
- **H4** Technical SEO
- Speed, structure, schema markup and clean multilingual pages, so search engines can read every page.
- **H4** Google Business Profile
- A complete, current profile with regular posts.
- **H4** AI answer tracking
- A fixed panel of questions, asked every month in ChatGPT, Gemini, Perplexity and Google AI. You see whether you are named.
- **H2** Start with a free AI audit
- **Button** Get a free AI audit
- **H4** Not sure what you need?
- Book a call. We listen first, then suggest the services that fit your goals.
- **Button** Book a call
- **H1** Selected work
- Recent projects for clients in Europe and Africa.
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- **H2** How it works
- Three steps, repeated every month.
- **H3** 1. Baseline
- We measure where you stand today: technical issues, speed, rankings and your share of AI answers.
- **H3** 2. Fix and publish
- We fix what holds you back, update your Google Business Profile and publish pages that answer your customers' questions.
- **H3** 3. Track
- Each month we run the same questions and searches again, and report what changed.

### The Hub — `/hub/`

*Meta title:* The Hub: Client Portal with AI Copilot | Pedicel  
*Meta description:* Requests, approvals, calendar, analytics with an AI copilot, brand score and inspiration feed. It learns from your decisions.

- **Eyebrow** THE HUB
- **H1** Everything in one place
- A client portal where you request work, approve content and ads, and follow progress.
- **Button** Get a free AI audit
- **H2** The Hub
- **H2** See every step. Approve your content and ads.
- The Hub is your own portal for working with us. You send requests with files or a voice note. You approve, reject or comment on every content and ad draft, including comments on videos. You see the calendar, the analytics and your brand score, and you can ask the AI copilot about your results. Before anything reaches you, a manager on our side has approved it.
- **H4** It learns from you
- It learns from your decisions: every approval and rejection becomes a pattern that guides the next draft.
- **H4** Brand rules, checked
- Each draft is scored against your brand rules before you see it.
- **H4** Inspiration feed
- Rated examples from brands we track, so you can tell us what you like and why.
- **H2** Start with a free AI audit
- **Button** Get a free AI audit
- **H4** Not sure what you need?
- Book a call. We listen first, then suggest the services that fit your goals.
- **Button** Book a call
- **H1** Selected work
- Recent projects for clients in Europe and Africa.
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- **H2** How it works
- How a piece of work moves through the Hub.
- **H3** 1. Request
- Send a request with text, files or a voice note. The Hub checks that the brief is complete.
- **H3** 2. Create
- We produce the piece. A manager on our side approves it before it reaches you.
- **H3** 3. Approve
- You approve, reject or comment. When you reject, give a reason, and it guides the next draft.
- **H3** 4. Learn
- Your decisions become patterns for the next drafts, and the results show in your analytics.

### Free AI audit — `/audit/`

*Meta title:* Free AI Marketing Audit | Pedicel Marketing  
*Meta description:* Free AI audit: your visibility in ChatGPT, Gemini, Perplexity and Google, your competitors and their ads, about five fixes and a short video.

- **H1** Your free AI marketing audit
- Tell us about your business. We show you where you stand and what to fix first.
- **H2** Request your audit
- Thank you. We have your request and will send your audit by email.
- Sorry, the form could not be sent. Please try again, or email us at info@pedicelmarketing.com.
- **H2** How it works
- **H4** Fill in the form
- Your company, your website and how to reach you. That is all we need.
- **H4** We build your audit
- Our AI system prepares the audit, and a team member reviews it before we email it to you.
- **H2** What you get
- **H4** AI visibility
- How ChatGPT, Gemini, Perplexity and Google AI answers describe your business, and whether they name you at all.
- **H4** Competitors
- Who you compete with, and what they do in ads and search.
- **H4** Fixes and a video
- About five concrete fixes, plus a short motion-graphic video that sums them up. Free, with no obligation.
- *placeholder:* Company name
- *placeholder:* Company website
- *placeholder:* Your goals (optional)
- *placeholder:* Your name
- *placeholder:* Your role
- *placeholder:* Email
- *placeholder:* Phone (optional)
- *data-wait:* Sending...
- *submit button:* Request my audit

### About — `/about/`

*Meta title:* About Pedicel Marketing | AI-First Growth Agency  
*Meta description:* An AI-first growth agency: one team in German, French and English, working with companies in Europe and Africa since 2020.

- **H1** About Pedicel
- **H2** Mission
- Make good marketing faster, clearer and easier to control for small and mid-sized companies.
- First, we treat you as a partner. Your goals become our goals, and we work on them together.
- Second, we use AI for the repetitive work and people for the judgement. That keeps the work fast, and keeps it true to your brand.
- **H1** The team
- An international team that works in German, French and English.
- **H4** Strategy & ads
- **H4** Content & motion video
- **H4** Web, search & data
- **H2** Vision
- Our vision is to help our partners reach theirs, while making a positive difference for our team and the communities we work in.
- **H2** Our vision rests on three pillars:
- **H4** Partners
- Our partners come first. Their goals are the reason we exist.
- **H4** Team
- We invest in our team's professional and personal growth, and we expect everyone to keep learning.
- **H4** Community
- We want our work to have a positive impact on the world around us.
- **H4** Transparency
- You see what we do
- Every draft, approval and result is visible in your Hub.
- **H4** Care
- Your brand, treated as ours
- We take care with every piece of work that carries your name.
- **H4** Partnership
- Your goals are our goals
- We work on your goals with you, not just for you.
- **H4** Clarity
- Plain words, clear plans
- We explain what we do and why, without jargon.
- **H4** Reliability
- We keep our word
- We agree on what we deliver, and we deliver it.
- **H2** Why Pedicel?
- Because you can see what we do.
- Every draft, approval and result sits in your Hub, so you never have to ask what we did this month. We care about your brand as if it were our own, and we stay accountable for the work.
- **H2** Giving back.
- **H2** Three projects our team supports.
- Giving back is part of our vision, alongside our work for clients.
- **H4** Oyiza Helping Hands
- Nigeria is one of our main markets, so we support the Oyiza Helping Hands Initiative, which works to "take children from the streets to the classrooms". Education shaped our team, and we believe everyone deserves the chance to learn.
- **H4** Ukraine
- Our colleague Sergio spent three weeks volunteering in Ukraine. He came back with first-hand experiences that shaped him and our business.
- **Button** Read about his experience
- **H4** LISA
- Working across borders means adapting every day. That is why a team member launched an association that helps people from different backgrounds feel at home in a shared culture.
- **Button** Learn about the project
- **H2** How it all started
- In 2020, as the pandemic pushed companies online, our co-founders saw that many of them needed help to adapt.
- **H2** Since then, we have worked with companies in Europe and Africa. Today we bring that experience to Swiss SMEs, as an AI-first growth agency.
- Brands we have worked with

### Contact — `/contact/`

*Meta title:* Contact Pedicel Marketing | Book a Call  
*Meta description:* Talk to Pedicel Marketing in German, French or English. Book a call or send us a message about your marketing.

- **H1** Book a call
- Send us a short message, and we will reply to find a time.
- **H2** Send a message
- Thank you. Your message has arrived, and we will reply soon.
- Sorry, the form could not be sent. Please try again, or email us at info@pedicelmarketing.com.
- Location
- Lõõtsa tn 5, 11415 Tallinn,
- Estonia
- Phone
- +34 677 196 547
- Email
- info@pedicelmarketing.com
- Follow us
- **H2** Not sure yet?
- Start with the free AI audit. It shows where you stand, at no cost, and you decide what happens next.
- Or book a call, and we will tell you honestly whether we are the right fit.
- *placeholder:* Your name
- *placeholder:* Email
- *placeholder:* Phone (optional)
- *placeholder:* Your message
- *data-wait:* Sending...
- *submit button:* Send message

### Portfolio — `/portfolio/`

*Meta title:* Our Work and Case Studies | Pedicel Marketing  
*Meta description:* Selected client work: content and motion video, social media, brand strategy and a live client Hub.

- **H1** Our work
- A few projects for clients in Europe and Africa: what each client asked for, and what we did.
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H1** Medical devices, explained in video
- **Card** Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- Brands we have worked with
- **H4** Not sure where to start?
- Book a short call. We look at your market together and tell you honestly where we can help.
- **Button** Book a call
- **H2** Six services, one team
- Choose one service or combine them. Everything runs through your Hub, in German, French or English.
- Outbound
- LinkedIn outreach from your team's profiles, plus WhatsApp reminders for opted-in customers.
- **Button** Learn more
- Web & tracking
- Fast multilingual websites and landing pages, with GA4, Consent Mode and conversion tracking set up properly.
- **Button** Learn more
- SEO + AI visibility
- Technical SEO, Google Business Profile and a monthly check of how AI assistants describe you.
- **Button** Learn more
- AI content & motion video
- Short videos, motion graphics and posts in German, French and English, built on hook mechanics we have analysed.
- **Button** Learn more
- Paid ads
- Meta and Google Search campaigns. Your budget goes directly to the platforms, with no markup.
- **Button** Learn more
- The Hub
- Your client portal for requests, approvals, the calendar and analytics, with an AI copilot.
- **Button** Learn more

### Case study: COEO Hostels — `/projects/coeo/`

*Meta title:* COEO Hostels: Social Media Case Study | Pedicel  
*Meta description:* Content, community and review management for COEO Hostels, a pod-style hostel in Málaga.

- **H1** Social media for a hostel in Málaga
- Content, community and review management for COEO Hostels.
- **Label** Content & social
- **H2** The brief
- COEO asked us to run its social media: create the content, look after the community and respond to reviews.
- **H2** Goals
- Make the brand better known
- Grow and engage the audience
- Bring more visitors and bookings
- **H2** About the partner
- COEO Hostels offers pod-style rooms that combine the privacy of a hotel with the social feel of a hostel. Located in the centre of Málaga, it provides modern amenities, cultural activities and easy access to the city's main sights.
- **H2** We combined regular content, active community management and care for reviews.
- **H2** What we did
- Our work covered three areas:
- **H4** Regular content
- We planned and published content on a steady schedule, and answered followers to keep conversations going.
- **H4** Review management
- We monitored and answered reviews and feedback on social media.
- **H4** Data-led planning
- We tracked how each post performed and used it to plan the next ones.
- **H2** The aim throughout: a real relationship between COEO and its guests.
- **H2** More projects
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social

### Case study: ISN Medical — `/projects/isnmedical/`

*Meta title:* ISN Medical: Video, Content and Client Hub | Pedicel  
*Meta description:* Motion video, a 12-month audit of 730 social posts and a live client Hub for ISN Medical, a diagnostics supplier in Nigeria.

- **H1** Medical devices, explained in video
- Motion video, a social media audit and a live client Hub for ISN Medical.
- **Label** Content, video & Hub
- **H2** The brief
- ISN Medical supplies diagnostic equipment to laboratories and hospitals in Nigeria. We create its content and video, and it works with us through a live client Hub.
- **H2** Goals
- Educational content: share clear, useful content that shows ISN's expertise.
- Customer engagement: more interaction with customers, useful content and quick responses.
- Product showcase: present ISN's medical equipment and how it is used in healthcare.
- **H2** About the partner
- ISN Medical provides medical diagnostic solutions in Lagos, Nigeria. It supplies medical equipment and support services to laboratories and hospitals, in partnership with international manufacturers.
- **H2** Two things set this project apart: a live client Hub, and a full audit of a year of social media posts.
- **H2** What we did
- Our work covered three areas:
- **H4** Motion video
- Motion-graphic reels, explainer videos and a 3D product film for ISN's equipment.
- **H4** A live client Hub
- ISN works with us through its own Hub at hub.pedicelmarketing.com: requests, approvals, calendar and analytics in one place.
- **H4** A 12-month social audit
- We audited 730 posts from twelve months of ISN's social media, to learn which formats and voices reach its audience.
- **H2** The goal: clear, useful communication between ISN Medical and the people it serves.
- **H2** More projects
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social

### Case study: La Taberna Fantástica — `/projects/latabernafantastica/`

*Meta title:* La Taberna Fantástica: Social Media | Pedicel  
*Meta description:* Content, promotions and community management for La Taberna Fantástica, a grill restaurant in Benahavís, Spain.

- **H1** Social media for a country restaurant
- Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H2** The brief
- La Taberna Fantástica asked us to run its social media: show the food and the setting, keep the community active, and promote special menus and events.
- **H2** Goals
- Engagement: build an active online community.
- Showcase: present the dishes and the atmosphere of the restaurant.
- Promotions: highlight special menus, events and offers.
- **H2** About the partner
- La Taberna Fantástica is a restaurant in Benahavís with a relaxed atmosphere. Its menu focuses on fresh, seasonal products and a central grill, with a modern take on market cuisine in a cortijo-style building.
- **H2** We combined appetising content, strong visuals and regular analysis.
- **H2** What we did
- Our work covered three areas:
- **H4** Storytelling
- Posts that tell the story of the dishes and the local food tradition of Benahavís.
- **H4** Community
- We answered comments and messages, and kept conversations going with food lovers.
- **H4** Visual content
- A consistent gallery of the dishes and the setting, to invite people to visit.
- **H2** The aim: a real connection between La Taberna Fantástica and its guests.
- **H2** More projects
- **H1** A brand strategy for a construction group
- **Card** Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social

### Case study: SANA Global Projects — `/projects/sana/`

*Meta title:* SANA Global Projects: Brand Strategy | Pedicel  
*Meta description:* Research, positioning and a brand identity guide for SANA Global Projects, the civil engineering arm of SANA Group.

- **H1** A brand strategy for a construction group
- Research, positioning and a brand guide for SANA Global Projects in West Africa.
- **Label** Brand strategy
- **H2** The brief
- SANA Global Projects asked us for a brand strategy and an identity guide that reflect its mission, its quality standards and its plans for the future.
- **H2** Goals
- Create a brand identity guide
- Develop a brand strategy
- **H2** About the partner
- SANA Global Projects is the civil engineering branch of SANA Group, a construction company in West Africa. International brands such as Kellogg's, Beloxxi and Colgate have trusted it with civil engineering projects in the region.
- **H2** The goal: a brand that is clear, consistent and ready to grow with the company.
- **H2** What we did
- Our work covered three areas:
- **H4** Buyer Persona
- Research and interviews to understand who SANA Global Projects' buyers are and what they need.
- **H4** Competitive Analysis
- A review of competitors to find clear opportunities and sharpen the company's position.
- **H4** Brand strategy
- A brand strategy aligned with the company's target audience, documented in a brand identity guide.
- **H2** The result: a documented brand strategy and identity guide for the years ahead.
- **H2** More projects
- **H1** Social media for a country restaurant
- **Card** Content and community for La Taberna Fantástica in Benahavís, Spain.
- **Label** Content & social
- **H1** Social media for a hostel in Málaga
- **Card** Content, community and review management for COEO Hostels.
- **Label** Content & social

### Impressum — `/impressum/`

*Meta title:* Impressum | Pedicel Marketing  
*Meta description:* Legal notice of Pedicel Marketing OÜ, Tallinn, Estonia.

- **H1** Impressum
- **H2** Company
- Pedicel Marketing OÜ
- Lõõtsa tn 5, 11415 Tallinn, Estonia
- Registry code: 16104440 (Estonian e-Business Register)
- Board member: Sergio Andres Palacio Martinez
- **H2** Contact
- Email:
- **Button** info@pedicelmarketing.com
- Phone:
- **Button** +34 677 196 547

### Privacy policy (Datenschutz) — `/datenschutz/`

*Meta title:* Privacy Policy (Datenschutz) | Pedicel Marketing  
*Meta description:* How Pedicel Marketing OÜ collects and uses personal data on this website, under the GDPR and the Swiss FADP.

- **H1** Privacy policy
- Last updated 6 October 2026
- **H2** 1. Who is responsible
- Pedicel Marketing OÜ, Lõõtsa tn 5, 11415 Tallinn, Estonia (registry code 16104440) is responsible for the processing of personal data on this website.
- Email:
- **Button** info@pedicelmarketing.com
- Phone:
- **Button** +34 677 196 547
- We are established in the European Union, so the EU General Data Protection Regulation (GDPR) applies to our processing. For visitors in Switzerland, the Swiss Federal Act on Data Protection (FADP) also applies.
- **H2** 2. What data we collect
- Forms: when you request an audit or send us a message, we collect what you enter. This can be your name, company, website, role, email address, phone number and message.
- Server logs: our web server records technical data for each visit, such as IP address, date and time, the page requested, browser type and the referring page.
- Analytics and marketing tools: the tools listed in section 5 collect data about your visit, such as pages viewed, device, approximate location and online identifiers. They use cookies or similar technologies.
- Embedded video: when you play a video on this website, it loads from YouTube through the Embedly service. YouTube and Embedly then receive your IP address and browser data.
- **H2** 3. Why we use it, and on what legal basis
- To answer your request and to prepare and send your free audit. Legal basis: steps you ask for before a contract, or a contract (GDPR Art. 6(1)(b)).
- To follow up with you about our services after you contact us. Legal basis: our legitimate interest in finding and serving clients (GDPR Art. 6(1)(f)).
- To run and secure this website. Legal basis: our legitimate interest in a working, secure website (GDPR Art. 6(1)(f)).
- To understand how visitors use the site and to measure our own advertising. Legal basis: your consent where the law requires it (GDPR Art. 6(1)(a)); otherwise our legitimate interest in improving the site and our advertising (GDPR Art. 6(1)(f)).
- To keep records that the law requires. Legal basis: a legal obligation (GDPR Art. 6(1)(c)).
- **H2** 4. How we prepare your audit
- Audit requests are processed with the help of AI model providers and providers of company data. They receive the information needed to prepare the audit, such as your company name and website. A team member reviews the audit before we send it.
- **H2** 5. Service providers
- Supabase: hosts the database in which we store form submissions (our customer database).
- Brevo: sends us an email notification for each form submission.
- AI model providers and company-data providers: help us prepare audits (see section 4).
- Google Analytics and the Google tag (Google): measure visits and how the website is used.
- PostHog: product analytics on how visitors use the website.
- Meta Pixel (Meta Platforms): measures the effect of our advertising on Facebook and Instagram.
- Apollo.io: shows us which companies visit our website, for our sales work.
- YouTube (Google) and Embedly: play the videos embedded on this website.
- These providers process data for us or, in some cases, for their own purposes under their own privacy terms.
- **H2** 6. Transfers abroad
- We are based in Estonia, in the European Union. Switzerland recognises the EU as providing adequate data protection.
- Some of the providers above may process data in other countries, including the United States. Where a country does not offer adequate protection, transfers rely on recognised safeguards, such as the Data Privacy Framework or standard contractual clauses.
- **H2** 7. How long we keep data
- Form data: as long as we need it to handle your request and any business relationship that follows, and after that as long as the law requires.
- Server logs: for a short period, for security purposes.
- Analytics data: according to the retention settings of each tool.
- **H2** 8. Your rights
- Under the GDPR and the FADP, you can ask what data we hold about you, have it corrected or deleted, ask us to restrict its use, receive it in a portable format, and withdraw any consent you have given.
- Where we rely on our legitimate interest, you can object at any time.
- To use these rights, write to info@pedicelmarketing.com.
- You can also complain to a data protection authority. In Estonia this is the Data Protection Inspectorate. In Switzerland it is the Federal Data Protection and Information Commissioner (FDPIC).
- **H2** 9. Cookies
- The analytics and marketing tools in section 5 use cookies. You can block or delete cookies in your browser settings.
- **H2** 10. Changes
- We may update this notice. The date at the top shows the current version.

### 404 — `/404/`

*Meta title:* Page not found | Pedicel Marketing  
*Meta description:* (none)

- **H4** 404
- **H1** This page does not exist
- It may have moved, or the link may be wrong.
- **Button** Back to the homepage

### Shared: navigation

- Home
- About
- Services
- Portfolio
- Contact
- Free AI audit

### Shared: footer (every page)

- How the free AI audit works
- 1
- Tell us about you
- Fill in a short form with your company and website. It takes about a minute.
- 2
- We build your audit
- Our AI system checks how AI assistants and Google present you, what your competitors do in ads and search, and where you can improve. A team member reviews it before we send it.
- 3
- Talk it through
- You get about five concrete fixes and a short motion-graphic video. If you like, we go through it with you in a free call.
- Get a free AI audit
- Book a call
- Call us
- Call us during office hours. We are happy to answer your questions.
- Monday to Friday, 08:00–16:00 (CET)
- Follow us
- Pages
- Home
- About
- Services
- Portfolio
- Contact
- Contact
- info@pedicelmarketing.com
- +34 677 196 547
- Lõõtsa tn 5, 11415 Tallinn, Estonia
- Offices
- West Africa
- — Lagos
- — Abuja
- Europe
- — Estonia
- © 2026 Pedicel Marketing OÜ. All rights reserved.
- Impressum
- Privacy policy
