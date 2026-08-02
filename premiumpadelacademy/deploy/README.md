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

**Both steps are still pending — see "Domain" below.**

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

## Domain — blocked

`nexumpadel.com` **cannot be connected.** Established 2026-08-02:

| Fact | Evidence |
|---|---|
| Not in this Hostinger account | portfolio API returns only `pedicelmarketing.com`, `pedicelfinance.com` |
| Owned by a third party | RDAP: registered 2025-06-13, registrar Namefinger.com LLC |
| Listed for sale | nameservers `ns1/ns2.afternic.com` |
| Expired, in **redemption period** | RDAP status; expired 2026-06-13 |
| Unregisterable right now | Hostinger availability API: `is_available: false` |

`nexumpadel.es` **is** registered, parked on Hostinger's own nameservers
(`byte/pixel.dns-parking.com` → `2.57.91.91`), with Hostinger mail live (MX +
SPF). But it sits in a **different Hostinger account**: this token gets
`403 [DNS:4002] Customer does not own nexumpadel.es`. An API token generated in
*that* account makes `dns_cutover.py` work unchanged.

Available to register in this account right now: `nexumpadel.net`,
`nexumpadel.academy`, `nexumpadel.club`, and `premiumpadelacademy.com`
(unregistered — no DNS at all).

## Current state

Files are published to `/var/www/premiumpadelacademy` (23 files) and pass the full
layout audit **served from that web root**, not just from source. No vhost is
installed and no DNS has been touched, so nothing is publicly reachable yet — the
site goes live the moment a domain is settled and the two commands above run.
