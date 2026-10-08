#!/usr/bin/env python3
"""Reconcile the Cloudflare DNS zone for nexumpadel.es against the authoritative
record set captured from Hostinger.

Deliberately conservative:

* Mail records (MX, SPF/DMARC TXT, DKIM CNAMEs, autodiscover/autoconfig) are ALWAYS
  created grey-cloud. Cloudflare's import wizard proxies CNAMEs by default, which
  silently breaks DKIM verification and mail-client autoconfig.
* The apex A and www CNAME are seeded pointing at the *existing* Scaleway origin,
  grey-cloud, so switching nameservers is a no-op for visitors. Cloudflare Pages
  rewrites them later when the custom domain is attached.
* Extra records the zone scan invented are reported and removed only with --prune.

Run with --check to diff without writing anything.
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.request, urllib.error

ZONE_NAME = "nexumpadel.es"
API = "https://api.cloudflare.com/client/v4"
SCALEWAY_ORIGIN = "62.210.212.199"

# The authoritative set, pulled from the Hostinger DNS API on 2026-08-10.
# (type, name, content, ttl, priority)
DESIRED = [
    ("A",     "@",                          SCALEWAY_ORIGIN,                             3600,  None),
    ("CNAME", "www",                        ZONE_NAME,                                    300,  None),
    ("MX",    "@",                          "mx1.hostinger.com",                        14400,     5),
    ("MX",    "@",                          "mx2.hostinger.com",                        14400,    10),
    ("TXT",   "@",                          "v=spf1 include:_spf.mail.hostinger.com ~all", 3600, None),
    ("TXT",   "@",                          "google-site-verification=0POClK7cnf10yhr5fTBEXG1SekH6yjwEtJ_dGRUBaH8", 3600, None),
    ("TXT",   "_dmarc",                     "v=DMARC1; p=none",                          3600,  None),
    ("CNAME", "hostingermail-a._domainkey", "hostingermail-a.dkim.mail.hostinger.com",    300,  None),
    ("CNAME", "hostingermail-b._domainkey", "hostingermail-b.dkim.mail.hostinger.com",    300,  None),
    ("CNAME", "hostingermail-c._domainkey", "hostingermail-c.dkim.mail.hostinger.com",    300,  None),
    ("CNAME", "autodiscover",               "autodiscover.mail.hostinger.com",            300,  None),
    ("CNAME", "autoconfig",                 "autoconfig.mail.hostinger.com",              300,  None),
]

# Nothing in this zone should ever be proxied until Pages attaches its own records.
PROXIED = False


def creds():
    key, email = os.environ.get("CLOUDFLARE_API_KEY"), os.environ.get("CLOUDFLARE_EMAIL")
    if not key:
        env = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        if os.path.exists(env):
            for line in open(env, encoding="utf-8"):
                line = line.strip()
                if line.startswith("CLOUDFLARE_API_KEY="):
                    key = line.split("=", 1)[1]
    if not key:
        sys.exit("CLOUDFLARE_API_KEY not found (env or workspace .env)")
    return key, email or "info@nexumpadel.es"


KEY, EMAIL = creds()
HDR = {"X-Auth-Email": EMAIL, "X-Auth-Key": KEY, "Content-Type": "application/json"}


def call(method: str, path: str, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def fqdn(name: str) -> str:
    return ZONE_NAME if name == "@" else f"{name}.{ZONE_NAME}"


def norm(rtype: str, content: str) -> str:
    c = content.strip().rstrip(".")
    if rtype == "TXT":
        c = c.strip('"')
    return c.lower()


def zone_id() -> str:
    d = call("GET", f"/zones?name={ZONE_NAME}")
    res = d.get("result") or []
    if not res:
        sys.exit(f"zone {ZONE_NAME} not found in this account")
    return res[0]["id"]


def records(zid: str):
    out, page = [], 1
    while True:
        d = call("GET", f"/zones/{zid}/dns_records?per_page=100&page={page}")
        out += d.get("result") or []
        info = (d.get("result_info") or {})
        if page >= (info.get("total_pages") or 1):
            return out
        page += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="diff only, write nothing")
    ap.add_argument("--prune", action="store_true", help="delete records not in the desired set")
    args = ap.parse_args()

    zid = zone_id()
    print(f"zone {ZONE_NAME} = {zid}\n")

    have = records(zid)
    have_key = {}
    for r in have:
        have_key.setdefault((r["type"], r["name"].lower(), norm(r["type"], r["content"])), []).append(r)

    created = updated = deleted = 0
    matched_ids = set()

    for rtype, name, content, ttl, prio in DESIRED:
        key = (rtype, fqdn(name).lower(), norm(rtype, content))
        existing = have_key.get(key)
        label = f"{rtype:5} {fqdn(name):34} -> {content}"
        if existing:
            r = existing[0]
            matched_ids.add(r["id"])
            need = {}
            if r.get("proxied") is True and PROXIED is False:
                need["proxied"] = False
            if r.get("ttl") != ttl:
                need["ttl"] = ttl
            if prio is not None and r.get("priority") != prio:
                need["priority"] = prio
            if need:
                print(f"  UPDATE {label}   {need}")
                if not args.check:
                    body = {"type": rtype, "name": fqdn(name), "content": content, "ttl": ttl}
                    if prio is not None:
                        body["priority"] = prio
                    if rtype in ("A", "CNAME"):
                        body["proxied"] = PROXIED
                    d = call("PATCH", f"/zones/{zid}/dns_records/{r['id']}", body)
                    if not d.get("success"):
                        sys.exit(f"  update failed: {d.get('errors')}")
                updated += 1
            else:
                print(f"  ok     {label}")
        else:
            print(f"  CREATE {label}")
            if not args.check:
                body = {"type": rtype, "name": fqdn(name), "content": content, "ttl": ttl}
                if prio is not None:
                    body["priority"] = prio
                if rtype in ("A", "CNAME"):
                    body["proxied"] = PROXIED
                d = call("POST", f"/zones/{zid}/dns_records", body)
                if not d.get("success"):
                    sys.exit(f"  create failed: {d.get('errors')}")
                matched_ids.add(d["result"]["id"])
            created += 1

    extras = [r for r in have if r["id"] not in matched_ids]
    if extras:
        print("\n  records NOT in the desired set:")
        for r in extras:
            print(f"    {'DELETE' if args.prune else 'EXTRA '} {r['type']:5} {r['name']:34} -> {r['content']}")
            if args.prune and not args.check:
                call("DELETE", f"/zones/{zid}/dns_records/{r['id']}")
                deleted += 1

    print(f"\ncreated={created} updated={updated} deleted={deleted} extra={len(extras)}")

    # self-check: re-read and assert the desired set is present and grey-cloud
    if not args.check:
        final = records(zid)
        fkey = {(r["type"], r["name"].lower(), norm(r["type"], r["content"])): r for r in final}
        missing, proxied_bad = [], []
        for rtype, name, content, ttl, prio in DESIRED:
            k = (rtype, fqdn(name).lower(), norm(rtype, content))
            r = fkey.get(k)
            if not r:
                missing.append(k)
            elif r.get("proxied") is True:
                proxied_bad.append(k)
        if missing:
            sys.exit(f"VERIFY FAILED — missing after sync: {missing}")
        if proxied_bad:
            sys.exit(f"VERIFY FAILED — proxied (must be grey-cloud): {proxied_bad}")
        print(f"verified: all {len(DESIRED)} desired records present, none proxied")


if __name__ == "__main__":
    main()
