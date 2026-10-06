# Deploying Premium Padel Academy

The site runs as static files on **spire** (Scaleway, `62.210.212.199`) behind the
nginx already on that box — the same arrangement as `pedicelmarketing.com`.

## Two trees, deliberately

| Tree | What it is | Contains |
|---|---|---|
| `site-v2/` | the **working** build — edit this | fabricated demo reviews, empty logo slots |
| `build/` | the **publishable** build — generated, never edited | neither |

`build/` is derived from `site-v2/` by `build_public.sh`, which strips the demo
content and then *refuses to exit 0* if any of it survived. That is what stops
invented reviews reaching a real audience: `publish.sh` re-asserts the same gates
against the exact tree it is about to copy, so rsyncing `site-v2/` by hand cannot
route around them.

## Update cycle

```sh
# 1. edit site-v2/ …then:
bash deploy/build_public.sh      # derive build/, run the gates
bash deploy/publish.sh           # rsync build/ -> /var/www/premiumpadelacademy
```

`build_public.sh` flags, if you want the placeholders visible on the live site:

* `--keep-reviews` — keep the reviews section as empty "Pendiente" cards
* `--keep-slots` — keep the "Espacio disponible" partner-logo slots

## Going live on a domain

**Done on 2026-08-02 — the site is live at https://nexumpadel.es.** The commands,
for reference and for the next domain:

```sh
python3 deploy/dns_cutover.py <domain>            # dry run, prints the exact request body
python3 deploy/dns_cutover.py <domain> --apply    # writes ONLY the @ and www A records
python3 deploy/dns_cutover.py <domain> --verify   # propagation check
bash    deploy/install_vhost.sh <domain>          # nginx vhost + certbot TLS
```

`dns_cutover.py` is mail-safe by construction: the request body contains nothing
but the two A records, it sends `overwrite=false` so Hostinger merges rather than
replaces, it snapshots the whole zone to `dns/` first, and afterwards it re-reads
the zone and aborts loudly if any MX / TXT / DKIM / DMARC record changed by a
single byte. Verified read-only against `pedicelmarketing.com` (45 record sets,
43 of them correctly classified as protected).

`install_vhost.sh` checks that the domain already resolves here before touching
nginx, and asserts the `pedicelmarketing` vhost still exists in the merged config
afterwards. The vhost file installs as `premiumpadel.conf`, which sorts *after*
`pedicelmarketing.conf`, so pedicelmarketing stays the default server for the
address exactly as it is today.

## Domain — live

`nexumpadel.es`, in the client's own Hostinger account (token stored as
`HOSTINGER_API_TOKEN_NEXUMPADEL_ES` in `~/.config/secrets.env`, never in this repo).

`nexumpadel.com` was the original request but is **not the client's**: RDAP shows it
registered 2025-06-13 to a third party via Namefinger.com LLC, parked on
`ns1/ns2.afternic.com` (listed for sale), expired 2026-06-13 and in redemption.
Hostinger's availability API returns `is_available: false`.

Two things the cutover had to handle, both now automatic:

* **`www` is a CNAME to the apex**, so it is left alone — a name cannot hold both a
  CNAME and an A record. It follows the apex for free.
* **Hostinger's `overwrite=false` appends rather than replaces.** The first write left
  the apex holding both `2.57.91.91` (the old parking address) and the new one, which
  would have alternated traffic between hosts. `--repair-apex` fixes it by deleting the
  apex A *set* by filter — a type-scoped operation that cannot touch MX or TXT — then
  re-adding the single record. `overwrite=true` is deliberately never used: if it means
  "replace the zone" rather than "replace this record set", a body containing only an A
  record would take the mail configuration with it.

Mail was verified untouched at every step: all 9 non-web record sets (Hostinger MX,
SPF, DMARC, 3 DKIM CNAMEs, autoconfig/autodiscover) byte-identical before and after.

## Draft state — read this before launch

The site is live but **marked `noindex` on every page**, because it is not yet client-
approved and the reviews on it are examples rather than real ones. The two are coupled
on purpose:

* `build_public.sh --keep-demo` forces the draft marker on
* `--keep-demo` together with `--allow-index` is refused outright
* `publish.sh` independently refuses any tree containing demo blocks unless every page
  carries `noindex`

At launch, once real reviews replace the examples:

```sh
bash deploy/build_public.sh --keep-slots --allow-index
bash deploy/publish.sh
```

## Current state

**Live at https://nexumpadel.es** since 2026-08-02.

* TLS via Let's Encrypt, expires 2026-10-31, `snap.certbot.renew.timer` handles renewal
* `www` and plain `http` both 301 to `https://nexumpadel.es` in a single hop
* clean URLs work (`/clubs`, `/camps`, `/contacto`)
* `pedicelmarketing.com` verified unaffected — still 200, still the default server for
  the address (`premiumpadel.conf` sorts after `pedicelmarketing.conf`)
* layout audit run against the live public site, not just the web root
