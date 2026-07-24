# USER.md — Site Cloner (operator notes)

**Profile:** `site-cloner`
**Model:** MiniMax-M3 (`provider: minimax`, `https://api.minimax.io/anthropic`)
**Mode:** CLI / manual, **mirror-only** (produces faithful baselines; no re-versioning yet)

## What it does

Give it a URL; it runs the `nt-site-mirror` pipeline and returns a validated local baseline plus an
honest evidence/gaps report. Baselines land in `workspace/<site-slug>/` (mirror in `mirror/`,
evidence in `reports/`).

## How to drive it (no messaging gateway installed)

```bash
HP=~/.hermes/hermes-agent/venv/bin/python

# one-shot
$HP -m hermes_cli.main -p site-cloner chat "Clone https://example.com as a reference baseline."

# interactive
$HP -m hermes_cli.main -p site-cloner chat
```

## Prerequisites (already set up on this host)

- Adapted skill: `skills/nt-site-mirror/` (profile-local).
- Playwright + Chromium venv: `~/.venvs/nt-mirror/bin/python` — used for `capture_assets.py` and
  `viewports.py`. The stdlib-only `mirror_assets.py` / `serve.py` run under plain `python3`.
- `MINIMAX_API_KEY` is set in `.env`.

## Deliberately NOT configured

- **No messaging gateway** (no Telegram/Discord). Run `hermes -p site-cloner gateway install && ... start`
  only if you later want to DM it a URL.
- **No cron jobs** — it is manual/on-demand.
- **Memory disabled** — the agent is stateless per clone (isolated from other profiles' memory cubes).
- **Re-versioning (phase 2)** is out of scope until the SOUL.md scope is explicitly widened.

## To expand scope later

1. Edit `SOUL.md` → add a phase-2 "re-version" section (rebrand/copy/media/layout on top of a
   validated baseline, kept separate from the mirror step).
2. Preserve a pristine copy of each baseline before editing so derived versions can be diffed.
