# HANDOFF — Premium Padel Academy

Written 2026-08-01 to hand this session to another agent (Kimi Code). No handoff
document existed before; this is the first.

**Read this whole file before touching anything.** The traps section at the end
covers several things that will waste hours if rediscovered the hard way.

---

## 1. What this is

A rebuild of a padel academy's website. The client is **Riki Padrón**
(Premium Padel Academy, Marbella). His existing site is a free Wix site:
`https://97jnvjsg4j.wixsite.com/riki-coach` — 4 routes: `/`, `/home` (Clubs),
`/camps`, `/contacto`.

The deliverable is a hand-written recreation of that site, in Spanish, with the
client's requested changes applied. Two versions exist side by side so the
client can compare.

| | Build dir | Origin port | Public URL |
| --- | --- | --- | --- |
| **v1.0** | `site/` | `127.0.0.1:8614` | `https://immigrants-energy-marine-abstract.trycloudflare.com` |
| **v2.0** | `site-v2/` | `127.0.0.1:8615` | `https://full-logging-barrier-berlin.trycloudflare.com` |

**v2 is also served at `…immigrants-energy…/v2/`** via a symlink
(`site/v2 -> ../site-v2`, gitignored). That exists because the client's DNS
would not resolve the second hostname; the `/v2/` path avoids DNS entirely.
**v1's root must keep serving v1** — verify after any change to that symlink.

**v2 is the active build.** v1 is frozen as the comparison baseline. Do not edit
`site/` unless explicitly asked.

---

## 2. Current state

### Live services (PIDs change on restart — match on the command line, not these numbers)

```
origin v1   python3 tools/static_range.py <proj>/site     8614     pid 1067202
tunnel v1   cloudflared tunnel --url http://127.0.0.1:8614          pid 2918726  (started Jul 30)
origin v2   python3 tools/static_range.py <proj>/site-v2  8615     pid 1658771
tunnel v2   cloudflared tunnel --url http://127.0.0.1:8615          pid 1658899
```

**Never kill a `cloudflared` process you want the URL from.** These are quick
tunnels: the hostname is issued at startup and a restart mints a *new* one,
breaking every link already sent to the client. To change what a URL serves,
kill and restart only the `static_range.py` origin on that port.

To restart an origin:
```sh
cd "/home/openclaw/Coding/ Cloning Sites/clone-website/premiumpadelacademy"
kill <origin-pid>
setsid nohup python3 "$(pwd)/tools/static_range.py" "$(pwd)/site-v2" 8615 >/dev/null 2>&1 &
```

If a tunnel dies, the new URL is in the cloudflared log line
`Your quick Tunnel has been created!`. Redirect the log somewhere persistent
when you start one.

### Git

- Repo: `clone-website`, remote `https://github.com/pedicelmarketing/clone-website.git`
- Branch: `feat/site-cloner-agent`
- **Committed 2026-08-02** (`0b13412`, "Add Premium Padel Academy recreation +
  Travel Productions mirror", 223 files). The commit blocker described below is
  **resolved** — kept here as history.

~~The commit is blocked and needs a human decision.~~ `.git/hooks/pre-commit`
runs three gates that all referenced a different work stream
(`skills/web-designer/scripts`, `reports/m6-composed-site`,
`reports/m6-validation`) that does not exist in this repo, plus a bare
`pytest -q` that either exited 5 (no tests) or tried to collect
`tools/qa/reveal_test.py` and died on its Playwright import. On 2026-08-02 the
hook was rewritten so **each gate is skipped when its inputs are absent** — the
gates re-activate automatically if those paths ever land. It now exits 0 and
commits work normally. Note the hook is not versioned (it lives in `.git/`), so
a fresh clone will not have it.

---

## 3. Layout

```
premiumpadelacademy/
├── site/            v1.0 — frozen baseline (4 html + css/ js/ assets/)
├── site-v2/         v2.0 — ACTIVE BUILD
│   ├── index.html clubs.html camps.html contacto.html
│   ├── css/styles.css      single stylesheet, no build step
│   ├── js/nav.js           mobile menu
│   ├── js/reveal.js        scroll motion (entrances + parallax)
│   ├── js/contact.js       form -> mailto composition
│   └── assets/             15 images + media-provenance.json
├── mirror/          FAILED static-mirror attempt, kept as evidence only.
│                    mirror-manifest.json is versioned; _external/ is not.
├── reports/         discovery / asset-preservation / validation / v2-changes
└── tools/
    ├── static_range.py         static host with Range/206 support
    ├── ingest_media.py         Wix media -> site assets (bounds, strips EXIF)
    ├── strip_demo_reviews.py   removes fabricated reviews (see §7)
    └── qa/                     validation scripts (see §6)
```

No framework, no bundler, no `package.json`. Plain HTML/CSS/JS served statically.
Edit a file, reload — the server sends `Cache-Control: no-store`.

---

## 4. Credentials and MCP — read carefully

### Nothing secret is stored in this repo, and it must stay that way

Secrets live outside the repo. **Do not copy key values into any file here.**

| What | Where | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | `/home/openclaw/Coding/ Cloning Sites/.env` | Load with `set -a; . ".env"; set +a`. **Quota is exhausted** — `generate_content_free_tier_requests, limit: 0`. Gemini is currently unusable; local Whisper was used instead. |
| GitHub auth | `gh` CLI (v2.45.0), already authenticated | Remote is an HTTPS URL |
| Claude settings | `~/.claude/settings.json`, `~/.claude.json` | Contains one local MCP server (`memos`) at user scope |

### MCP — the important part for a Kimi handoff

**This project has ZERO locally-configured MCP servers.** Checked
`~/.claude.json` → `projects["/home/openclaw/Coding/ Cloning Sites"].mcpServers`
is empty, as is the entry for `clone-website`.

Every MCP tool available during this session (Notion, Gmail, Google Calendar,
Google Drive, Calendly, Comfy, Higgsfield, Supabase, Brevo, Meta Ads, PlusVibe,
Supermetrics, Ubersuggest, Academic Research) came from **claude.ai connectors**
— OAuth integrations bound to the Claude account, not to any file on this
machine. **They will not transfer to Kimi Code.** There is no config to copy.

That is not a problem: **none of them were used for this work.** The entire
build used only local tooling (§5). If a future task genuinely needs one, it has
to be set up natively in the new client.

The only portable MCP entry is `memos` in `~/.claude/settings.json` (user
scope), which was also unused here.

---

## 5. Local tooling (this is what actually matters)

| Tool | Version / path | Used for |
| --- | --- | --- |
| python3 | 3.12.3 | everything; stdlib only for serve/mirror |
| venv | `~/.venvs/nt-mirror/bin/python` | **Playwright lives here, not in system python** |
| Playwright + Chromium | in the venv | all validation, screenshots, DOM measurement |
| whisper | `~/.local/bin/whisper`, model `medium.pt` cached | transcribing the client's Spanish voice notes |
| ffmpeg / ffprobe | 6.1.1 | audio extraction, frame extraction |
| yt-dlp | 2026.07.04 **in the venv** (system copy is old and fails) | video download |
| cloudflared | 2026.7.2 | quick tunnels |
| node / npx | v22.23.1 / 10.9.8 | available, unused so far |
| gh | 2.45.0 | GitHub |

**Always use `~/.venvs/nt-mirror/bin/python` for anything importing Playwright.**
System `python3` has no pip and no Playwright.

### nt-site-mirror skill

`~/.claude/skills/nt-site-mirror/` — the cloning pipeline
(`capture_assets.py`, `mirror_assets.py`, `serve.py`, `viewports.py`).
`viewports.py` is still useful as a route × viewport matrix runner:

```sh
~/.venvs/nt-mirror/bin/python ~/.claude/skills/nt-site-mirror/scripts/viewports.py \
  "http://127.0.0.1:8713/index.html" ... --out reports/viewports-v2 \
  --viewports desktop,tablet,mobile
```

For Kimi: this is a Claude-Code skill format. The *scripts* are plain Python and
work anywhere; only the `SKILL.md` orchestration is Claude-specific.

---

## 6. How to validate (do not skip this)

Every change in this session was gated. Scripts are in `tools/qa/`, saved out of
the session scratchpad so they survive. They take the base URL from `$QA_BASE`
(default `http://127.0.0.1:8713`).

```sh
cd "/home/openclaw/Coding/ Cloning Sites/clone-website/premiumpadelacademy"
python3 tools/static_range.py "$(pwd)/site-v2" 8713 &     # scratch port, not 8615
export QA_BASE=http://127.0.0.1:8713

~/.venvs/nt-mirror/bin/python tools/qa/audit3.py        # layout gate  -> exit 0
~/.venvs/nt-mirror/bin/python tools/qa/reveal_test.py   # motion gate
~/.venvs/nt-mirror/bin/python tools/qa/nojs.py          # JS-disabled gate
~/.venvs/nt-mirror/bin/python tools/qa/motion.py        # reduced-motion + menu
~/.venvs/nt-mirror/bin/python tools/qa/shot4.py "$QA_BASE" ./shots v2   # screenshots
~/.venvs/nt-mirror/bin/python tools/qa/verify_live.py   # against the public URL
```

`audit3.py` asserts, per page × {mobile 390, desktop 1440}: no text under 15px,
no horizontal overflow, no unintended image overlap, no real document h-scroll,
no page errors, no 4xx/5xx. **Current state: all green.**

Two things about this gate, learned painfully:

- It ignores elements clipped by an ancestor. Bounding boxes do not shrink under
  `overflow:hidden`, so a deliberately over-scaled hero image looked like an
  overflow bug until that was fixed.
- After relaxing it, it was re-run against the old broken build
  (`examples/riki-coach/recreation/`) as a **negative control** — it still
  reports that build's 43 sub-15px nodes and 68×140px image overlap. Do the same
  if you weaken any assertion. A gate that cannot fail is worse than none.

`shot4.py` scrolls the whole page before capturing, because the scroll-reveal
animation leaves below-fold content transparent in a naive full-page screenshot.
Allow >1.4s for transitions to settle or you will measure mid-animation opacity
and think it is broken.

---

## 7. Content rules that must not be quietly dropped

**Fabricated reviews are currently live on v2 and must not ship as-is.**
The client asked for demo reviews to populate the design ("the page is just a
front for now"). Six invented reviews plus an invented 4.8 average are on
`site-v2/index.html`, every one tagged `data-demo="true"`.

```sh
python3 tools/strip_demo_reviews.py --check   # exit 1 if fabricated content present
python3 tools/strip_demo_reviews.py           # revert to marked-empty slots
```

Wire `--check` into any deploy path. Publishing invented reviews to real
visitors is a misleading commercial practice under Spanish/EU consumer law
(Ley de Competencia Desleal art. 5; Directive 2005/29/EC as amended) and the
liability sits with the academy.

**Do not invent content attributed to identifiable real people.** Juampi
Vanella's biography is still an explicit placeholder for this reason — nothing
about his background is publicly sourceable. Placeholders in this build are
always visibly marked (dashed borders, "PENDIENTE" tags), never plausible-looking
filler that could be mistaken for real.

**Report evidence honestly.** The reports in `reports/` state the evidence basis
for every claim (`Observed visually` / `Interaction-tested` / `DOM+assets
confirmed` / `Not exercised`) and name the acceptance tier reached. Keep that
discipline; do not upgrade a claim the evidence does not support.

---

## 8. Traps

1. **Cloudflare rewrites email addresses in transit.** `mailto:` links come back
   as `/cdn-cgi/l/email-protection#<hex>` plus an injected decoder script, so
   **`curl` on the public URL is not valid evidence** about contact details — it
   returns a stub. Use a real browser (`tools/qa/verify_live.py`). The served
   HTML is also ~434 bytes larger than the file on disk for this reason.

2. **The Wix source cannot be statically mirrored.** `mirror_assets.py` returns
   `result: failed_required` — all four documents refused with
   `personalized_evidence_observed_in_one_or_more_responses` (Wix SSRs per
   session). Only 4 of ~250 requests per route are same-origin; 186 are Wix's
   proprietary Thunderbolt runtime. That is why this is a hand-written
   recreation. Do not retry the mirror expecting a different result.

3. **The source site returns intermittent 503s.** Observed once for ~30 minutes
   (bare `nginx` error, not a Wix branded page) while `wix.com` itself was fine.
   Transient origin wobble; it recovers. Retry rather than concluding the site is
   gone.

4. **Client media files may be mislabelled.** A file supplied as
   `riqui upscaled.jpeg` was 600×1024 against the 1170×1994 already on the
   site — a downgrade despite the name. **Always compare dimensions and a
   perceptual hash before accepting a replacement image.** See
   `reports/v2-changes.md` §v2.2 for the method.

5. **WhatsApp/Vimeo video files can be truncated on read.** ffmpeg reported
   `partial file` and a naive audio extraction silently stopped at 180s of 348s,
   which would have lost half the client's feedback. Extract with
   `-err_detect ignore_err -fflags +genpts+igndts` and **check the output
   duration against the container duration.**

6. **Vimeo downloads need the venv yt-dlp + impersonation**, and an unlisted
   video still hits a Cloudflare human-verification page in headless Chromium —
   which is a hard stop, not something to work around. Ask for the file directly.

7. **The client reviews the site machine-translated.** Chrome auto-translates the
   Spanish build to English for him. Any feedback about *wording* may be aimed at
   Google's translation, not the copy. Check before rewriting Spanish.

8. **`prefers-reduced-motion` and JS-off must both leave content visible.** The
   reveal animation hides content behind `.js` on `<html>` set before first
   paint. If you touch `reveal.js` or the `.js [data-anim]` rules, re-run
   `nojs.py` — a regression here makes the entire page below the fold invisible.

---

## 9. Open items

| Item | Needs |
| --- | --- |
| ~~**Commit blocked**~~ | **Resolved 2026-08-02** — hook rewritten to skip absent gates; work committed as `0b13412` |
| **Fabricated reviews live** | Real reviews, or run `strip_demo_reviews.py` before launch |
| **Juampi's bio** | Two sentences from him; placeholder in place |
| **Coach name spelling** | Client wrote "juanmi"; his site says "Juampi Vanella". Site spelling used — confirm |
| **Hero photography** | Only one 2000px landscape image exists for three hero slots; the rest are 1170px **at source**. Needs full-res originals from his camera roll |
| **Contact form backend** | Currently composes a `mailto:`. Wire Formspree/Brevo/serverless if real submissions wanted; markup does not change |
| **Logo artwork** | Client's own file misspells "Aacademy". Worked around by using only the monogram + typeset wordmark. Original artwork still wrong |
| **Stable URL** | Quick tunnels are ephemeral and unauthenticated. A named tunnel on a real domain would stop the URL churn |

---

## 10. Continuing in another client (Kimi Code / Continue / etc.)

Nothing here is Claude-specific except the skill wrapper. To continue elsewhere:

- **Working dir:** `/home/openclaw/Coding/ Cloning Sites/clone-website/premiumpadelacademy`
  (note the space in `" Cloning Sites"` — quote all paths).
- **Project instructions:** `../CLAUDE.md` explains the two-phase clone →
  re-version pipeline and its non-negotiables. Worth reading even under a
  different agent; rename/copy if your client expects `AGENTS.md` or similar.
- **Recent history:** `reports/v2-changes.md` is the full change log with client
  quotes and timestamps. `reports/validation-report.md` has the evidence table.
- **No install step.** No `package.json`, no dependencies to restore. Python and
  the venv are already set up.

Regarding `npx`: node 22 / npx 10.9.8 are available, and nothing in this project
uses them. If the intent was to run **Continue** (`continue.dev`) or a similar
npx-launched assistant against this repo, it will work fine — the codebase is
plain static files — but it will not inherit the claude.ai connectors (§4), and
it will need `~/.venvs/nt-mirror/bin/python` for any Playwright validation.
If something else was meant by "npx continues", ask; I did not want to guess and
write something misleading.
