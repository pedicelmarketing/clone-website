# pedicelmarketing.ch

Static multilingual site for Pedicel's Swiss market: German at `/`, French at `/fr/`, English at `/en/`. Built from English templates plus translation files; hosted on spire next to the .com site. Copy decisions and removed claims are in `COPY.md`.

```
pages/<route>/index.html   English templates (source of truth for text and layout)
strings/de.json, fr.json   {english string: translation}
assets/                    images (img/ + img/PROMPTS.md), form-shim-ch.js, lang-switch.css
dist/                      build output (git-ignored); dist/_external = local-preview symlink
deploy/                    nginx-pedicelmarketing-ch.conf, publish.sh
```

## Edit text

1. Change English in `pages/…/index.html`.
2. `python3 extract.py` lists untranslated strings in `strings/todo-de.json` and `todo-fr.json`.
3. Put the translations into `strings/de.json` and `strings/fr.json`.
4. `python3 build.py` (all languages; `--lang de|fr|en` for one). It exits 1 and lists any string still untranslated.
5. `python3 checks.py dist` (forbidden claims, broken links, meta lengths, blog links). Must print `checks: all clear`.
6. `python3 -m unittest -v`

## Preview

```bash
python3 -m http.server 8090 --bind 127.0.0.1 -d dist
python3 qa_shots.py --base http://127.0.0.1:8090   # screenshots to shots/, layout + 404 + hero assertions
```

## Images

Scene images are AI-generated (Z-Image Turbo, Comfy Cloud). Prompts, seeds and slots: `assets/img/PROMPTS.md`. People shown are not real and are never named or used as testimonials.

## Forms

The two forms post to `/api/forms/ch-audit` and `/api/forms/ch-contact` (`assets/form-shim-ch.js`, which also sends the page language as `lang`). nginx proxies them to `form_handler.py` on 127.0.0.1:8081, which creates Hub CRM leads labelled "(CH-DE)", "(CH-FR)" or "(CH-EN)" (plain "(CH)" if the language is missing) and queues the audit pitch in that language. Both forms carry the hidden `website_url_hp` honeypot. The handler lives in `pedicelmarketing/deploy/` and is shared with the .com.

`/assets/*` is cached for a year as immutable; `build.py` adds `?v=<content hash>` to every reference, so an edited file gets a new URL. 404s answer in the URL's language (`/fr/…` → `/fr/404/`), and the 404 pages are `noindex`.

**After merging, restart the `pedicel-forms` service** so the handler picks up the CH endpoints.

## Go live (operator steps, in order)

0. **Blocking — decide trackers vs consent:** remove Meta Pixel / PostHog / Apollo / GA from the .ch pages, or add a consent banner. Do not publish until this is decided (operator decision pending; see Open decisions).
1. Buy `pedicelmarketing.ch` (ask first).
2. DNS: A records `@` and `www` to `62.210.212.199`. Wait for `dig +short pedicelmarketing.ch`.
3. Install nginx: copy `deploy/nginx-pedicelmarketing-ch.conf` to `sites-available`, symlink into `sites-enabled` (commands in the file header), `sudo nginx -t && sudo systemctl reload nginx`. The .com vhost must stay enabled (this file reuses its `pedicel_forms` zone and `$pedicel_cache` map).
4. `sudo certbot --nginx -d pedicelmarketing.ch -d www.pedicelmarketing.ch`
5. Restart `pedicel-forms`.
6. `bash deploy/publish.sh` (builds, runs checks, rsyncs `dist/` to `/var/www/pedicelmarketing-ch/`, reloads nginx). It refuses to run before step 3.
7. Live checks: `curl -sI` returns 200 for `https://pedicelmarketing.ch/`, `/fr/`, `/en/hub/`, and 404 (in the right language) for `/nope`, `/fr/nope`, `/en/nope`. Then 6 test submits — each form in each language: contact on `/contact/`, `/fr/contact/`, `/en/contact/` and audit on `/audit/`, `/fr/audit/`, `/en/audit/` (name `TEST CH <lang>`, audit website `example.ch`). Confirm 6 leads in the Hub CRM labelled "Contact form (CH-DE)", "(CH-FR)", "(CH-EN)" and "Website Audit request (CH-DE)", "(CH-FR)", "(CH-EN)", the 3 audit pitches queued in de/fr/en, and the owner emails saying "on pedicelmarketing.ch". Delete all 6 leads and their pitches after.
8. spire-config repo: `./sync.sh --commit` to store the new nginx file.

## Open decisions (details in `COPY.md`)

- **Trackers and consent:** the pages load Google tag, PostHog, Meta Pixel and the Apollo tracker with no cookie banner. Remove them for .ch or add a consent banner. The privacy text is drafted for counsel and needs a lawyer's check.
- **Phone calls in outbound:** removed until Swiss rules on sales calls are checked.
- **Offices and phone:** footer offices (Lagos, Abuja, Estonia) and the +34 phone with "08:00-16:00 CET" hours are carried over from the .com. Confirm they are right for a Swiss site, and that German/French callers get an answer.
- **Client logos:** the "Brands we have worked with" logos (including Pfizer) and the About-page founding story: confirm they are true and cleared for use on a Swiss site.
