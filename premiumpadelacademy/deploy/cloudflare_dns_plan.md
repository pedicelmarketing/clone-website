# nexumpadel.es — DNS cutover to Cloudflare

**Status as of 2026-08-10: staged and gate-passed, BLOCKED at the nameserver switch.**

| Step | State |
|------|-------|
| Pages project + 87-file deploy, all files verified byte-identical | ✅ done |
| Zone `nexumpadel.es` added (`6798c68fbe30691255b78e03c735bf46`) | ✅ done |
| All 12 records replicated, verified present and grey-cloud | ✅ done |
| Pre-cutover gate: Cloudflare answers == Hostinger answers, 10/10 | ✅ **passed** |
| Switch nameservers at Hostinger → `clara`/`ruben.ns.cloudflare.com` | ⛔ **blocked** — the harness permission classifier denied the `PUT .../nameservers` call |
| Attach Pages custom domains | ⏸ waiting on the switch |

Nothing user-visible has changed: the apex still resolves to `62.210.212.199`, the site still
returns 200 from nginx, and MX still points at Hostinger. The Cloudflare zone sits `pending`
with a record set proven identical to what Hostinger serves, so the switch is a no-op for
visitors and mail — the flip to Pages happens later, when the custom domain is attached.

To unblock, either run the PUT below manually or allow the call and I will continue:

```sh
set -a && . ~/.config/secrets.env && set +a
curl -X PUT "https://developers.hostinger.com/api/domains/v1/portfolio/nexumpadel.es/nameservers" \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN_NEXUMPADEL_ES" \
  -H "Content-Type: application/json" \
  --data '{"ns1":"clara.ns.cloudflare.com","ns2":"ruben.ns.cloudflare.com"}'
```

## Why the nameservers must move

Cloudflare Pages needs the apex on Cloudflare DNS (CNAME flattening). Hostinger has no
apex ALIAS/ANAME, so `nexumpadel.es` cannot point at Pages while DNS stays at Hostinger.
Moving nameservers means **every existing record must be recreated in Cloudflare first**,
or live mail dies at the moment of the switch.

## The complete record set to replicate

Pulled from the Hostinger DNS API on 2026-08-10 — not from `dig`, which would have missed
the three DKIM selectors entirely.

| Type  | Name                         | Content                                             | TTL   | Proxy        |
|-------|------------------------------|-----------------------------------------------------|-------|--------------|
| A     | `@`                          | `62.210.212.199` → **replaced by Pages**             | 3600  | Proxied      |
| CNAME | `www`                        | `nexumpadel.es.` → **replaced by Pages**             | 300   | Proxied      |
| MX    | `@`                          | `5 mx1.hostinger.com.`                               | 14400 | **DNS only** |
| MX    | `@`                          | `10 mx2.hostinger.com.`                              | 14400 | **DNS only** |
| TXT   | `@`                          | `"v=spf1 include:_spf.mail.hostinger.com ~all"`      | 3600  | —            |
| TXT   | `@`                          | `"google-site-verification=0POClK7cnf10yhr5fTBEXG1SekH6yjwEtJ_dGRUBaH8"` | 3600 | — |
| TXT   | `_dmarc`                     | `"v=DMARC1; p=none"`                                 | 3600  | —            |
| CNAME | `hostingermail-a._domainkey` | `hostingermail-a.dkim.mail.hostinger.com.`           | 300   | **DNS only** |
| CNAME | `hostingermail-b._domainkey` | `hostingermail-b.dkim.mail.hostinger.com.`           | 300   | **DNS only** |
| CNAME | `hostingermail-c._domainkey` | `hostingermail-c.dkim.mail.hostinger.com.`           | 300   | **DNS only** |
| CNAME | `autodiscover`               | `autodiscover.mail.hostinger.com.`                   | 300   | **DNS only** |
| CNAME | `autoconfig`                 | `autoconfig.mail.hostinger.com.`                     | 300   | **DNS only** |

> **Every mail record must be grey-cloud (DNS only).** If a DKIM or autodiscover CNAME is
> proxied, Cloudflare answers with its own anycast IPs, DKIM signatures fail to verify and
> mail clients stop autoconfiguring. Cloudflare's zone-import wizard proxies CNAMEs by
> default — this is the single most likely way to break mail here.

## Order of operations

Scaleway keeps serving the live site through every step, so there is no content downtime.

1. **Add the zone** `nexumpadel.es` to account `b56751e36842462c119a2063e60935a5`.
   Let the scan import what it can.
2. **Reconcile against the table above.** Add anything missed; set every mail record to
   DNS only. Do this *before* touching nameservers.
3. **Verify against Cloudflare's own nameservers while the domain is still live on
   Hostinger** — this is the whole safety margin, use it:
   ```sh
   NS=<assigned>.ns.cloudflare.com
   dig +short @$NS nexumpadel.es MX
   dig +short @$NS nexumpadel.es TXT
   dig +short @$NS _dmarc.nexumpadel.es TXT
   for s in a b c; do dig +short @$NS hostingermail-$s._domainkey.nexumpadel.es CNAME; done
   dig +short @$NS autodiscover.nexumpadel.es CNAME
   ```
   Each answer must equal the table. **If any differ, stop — do not change nameservers.**
4. **Switch nameservers at Hostinger** to the assigned Cloudflare pair. Wait for the zone
   to report `active`.
5. **Attach custom domains** `nexumpadel.es` and `www.nexumpadel.es` to the `nexumpadel`
   Pages project; Cloudflare replaces the apex A and www CNAME automatically.
6. **Post-cutover verification:**
   ```sh
   curl -sI https://nexumpadel.es | grep -i 'server\|cf-ray'   # expect cloudflare
   dig +short nexumpadel.es MX                                  # expect mx1/mx2.hostinger
   curl -s https://nexumpadel.es/robots.txt                     # expect Allow: /
   ```
   Then send a real test message **both ways** through `info@nexumpadel.es` and confirm the
   received headers show `dkim=pass` and `spf=pass`.

## Rollback

Revert the nameservers at Hostinger to `byte.dns-parking.com` / `pixel.dns-parking.com`.
The Hostinger zone is left intact by this procedure, so reverting restores the previous
state wholesale.

**Do not decommission the Scaleway vhost** (`/var/www/premiumpadelacademy`, nginx
`premiumpadel.conf` on `62.210.212.199`) until mail and site have been verified on
Cloudflare for at least 48h. It is the rollback target.

## Credential note

The cutover currently depends on the **Global API Key** in the workspace `.env`
(authenticates as `info@nexumpadel.es`). That key can do anything to the account and cannot
be scoped. Replace it with a token limited to `Pages:Edit`, `Zone:Edit`, `DNS:Edit` and
rotate the global key once the migration is done.

The unrelated `CLOUDFLARE_API_KEY` value previously in `.env` under the
`#Cloudfare_nexumpadel` heading is **invalid as a bearer token** — it only authenticates as
a global key, and only when paired with `X-Auth-Email: info@nexumpadel.es`.
