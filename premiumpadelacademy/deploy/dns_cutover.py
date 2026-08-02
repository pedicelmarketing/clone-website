#!/usr/bin/env python3
"""Point a Hostinger-hosted domain at spire (62.210.212.199) without touching mail.

The danger with a zone API is collateral damage: a full-zone write wipes MX, SPF,
DKIM and DMARC, and the domain silently stops receiving mail. So this script is
mail-safe by construction:

  * it only ever SENDS A records for the apex and www — no other name or type is
    included in the request body
  * it sends overwrite=false, so Hostinger merges rather than replacing the zone
  * it snapshots the full zone to dns/ before the write
  * it re-reads the zone afterwards and diffs EVERY non-web record, aborting loud
    if a single MX/TXT/CNAME byte changed

    python3 deploy/dns_cutover.py nexumpadel.es              # dry run, shows the plan
    python3 deploy/dns_cutover.py nexumpadel.es --apply
    python3 deploy/dns_cutover.py nexumpadel.es --verify     # propagation check only

Needs HOSTINGER_API_TOKEN, read from ~/.config/secrets.env (mode 600). The token
is never written to disk by this script and never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SECRETS = Path.home() / ".config" / "secrets.env"
API = "https://developers.hostinger.com/api/dns/v1/zones"
TARGET_IP = "62.210.212.199"

# Names whose records this script is allowed to write. Everything else in the
# zone is read-only as far as this tool is concerned.
WEB_NAMES = {"@", "www"}


def token(domain: str) -> str:
    """Domain-specific token first, falling back to the generic one.

    Domains here live in more than one Hostinger account, and a token only ever
    sees its own account's zones. So nexumpadel.es reads
    HOSTINGER_API_TOKEN_NEXUMPADEL_ES before HOSTINGER_API_TOKEN.
    """
    names = [f"HOSTINGER_API_TOKEN_{re.sub(r'[^A-Z0-9]', '_', domain.upper())}",
             "HOSTINGER_API_TOKEN"]
    text = SECRETS.read_text() if SECRETS.exists() else ""

    # Each name is resolved fully — environment, then file — before falling back
    # to the next. Checking the whole environment first would let a generic
    # HOSTINGER_API_TOKEN exported by the shell profile silently outrank the
    # domain-specific token sitting in secrets.env, and the request would go out
    # authenticated as the wrong account.
    for name in names:
        if os.environ.get(name):
            return os.environ[name]
        m = re.search(rf"^(?:export\s+)?{name}=(.*)$", text, re.M)
        if m:
            return m.group(1).strip().strip('"').strip("'")

    sys.exit(f"FATAL: none of {names} found in env or {SECRETS}")


def call(method: str, domain: str, body: dict | None = None) -> tuple[int, object]:
    req = urllib.request.Request(
        f"{API}/{domain}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token(domain)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            # developers.hostinger.com sits behind Cloudflare, which rejects the
            # default "Python-urllib/3.x" agent outright (error 1010) before the
            # request ever reaches the API.
            "User-Agent": "premiumpadelacademy-deploy/1.0",
        })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def mail_fingerprint(zone: list) -> dict:
    """Everything this script must not change, in a comparable form."""
    return {
        f"{rec.get('name')}|{rec.get('type')}": sorted(
            r.get("content", "") for r in rec.get("records", []))
        for rec in zone
        if rec.get("name") not in WEB_NAMES or rec.get("type") not in ("A", "AAAA")
    }


def show(zone: list) -> None:
    for rec in sorted(zone, key=lambda r: (r.get("type", ""), r.get("name", ""))):
        contents = ", ".join(r.get("content", "") for r in rec.get("records", []))
        flag = "  <-- web" if rec.get("name") in WEB_NAMES and rec.get("type") in ("A", "AAAA", "CNAME") else ""
        print(f"    {rec.get('type'):6} {rec.get('name'):28} {contents[:70]}{flag}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain")
    ap.add_argument("--apply", action="store_true", help="perform the write")
    ap.add_argument("--verify", action="store_true", help="propagation check only")
    ap.add_argument("--ip", default=TARGET_IP)
    args = ap.parse_args()

    if args.verify:
        return verify(args.domain, args.ip)

    print(f"==> reading zone for {args.domain}")
    status, zone = call("GET", args.domain)
    if status != 200:
        print(json.dumps(zone, indent=2) if not isinstance(zone, str) else zone[:800])
        hint = ""
        if isinstance(zone, dict):
            if zone.get("cloudflare_error"):
                hint = ("\nHINT: blocked by Cloudflare before reaching Hostinger — this is a "
                        "transport problem (User-Agent / IP reputation), not a permissions one.")
            elif "does not own" in str(zone.get("message", "")):
                hint = ("\nHINT: the API token belongs to a different Hostinger account than "
                        "the one holding this domain. Generate a token in the account that "
                        "owns it (hPanel -> API -> Manage API tokens).")
        sys.exit(f"FATAL: HTTP {status} reading the zone.{hint}")
    if not isinstance(zone, list) or not zone:
        sys.exit(f"FATAL: zone for {args.domain} is empty — is the domain in this account?")

    print(f"    {len(zone)} record set(s)")
    show(zone)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dns_dir = PROJECT / "dns"
    dns_dir.mkdir(exist_ok=True)
    before = dns_dir / f"{args.domain}-zone-before-{stamp}.json"
    before.write_text(json.dumps(zone, indent=2) + "\n")
    print(f"==> snapshot written: {before.relative_to(PROJECT)}")

    mail_before = mail_fingerprint(zone)
    print(f"==> {len(mail_before)} non-web record set(s) that must not change "
          f"(MX/TXT/DKIM/etc.)")

    # www is usually already a CNAME to the apex, in which case it follows the
    # apex automatically and must be left alone: a name cannot hold both a CNAME
    # and an A record, and writing one would either be rejected or produce a
    # conflicting set.
    www_cname = next((rec for rec in zone
                      if rec.get("name") == "www" and rec.get("type") == "CNAME"), None)
    www_targets = {r.get("content", "").rstrip(".").lower()
                   for r in (www_cname or {}).get("records", [])}
    www_follows_apex = bool(www_targets & {args.domain.lower(), "@"})

    records = [{"name": "@", "type": "A", "ttl": 3600,
                "records": [{"content": args.ip}]}]
    if www_follows_apex:
        print(f"\n==> www is a CNAME to the apex — leaving it untouched, it will follow")
    else:
        records.append({"name": "www", "type": "A", "ttl": 3600,
                        "records": [{"content": args.ip}]})

    payload = {"overwrite": False, "zone": records}   # merge; never replace the zone

    print("\n==> planned write (this is the ENTIRE request body):")
    print(json.dumps(payload, indent=2))

    if not args.apply:
        print("\nDRY RUN — nothing sent. Re-run with --apply to perform it.")
        return 0

    print("\n==> applying")
    status, resp = call("PUT", args.domain, payload)
    print(f"    HTTP {status}")
    if status not in (200, 201, 204):
        print(json.dumps(resp, indent=2)[:1500])
        sys.exit("FATAL: write rejected — zone unchanged.")

    print("==> re-reading zone to confirm nothing else moved")
    status, after_zone = call("GET", args.domain)
    if status != 200 or not isinstance(after_zone, list):
        sys.exit("FATAL: could not re-read the zone to verify. CHECK MAIL MANUALLY.")

    (dns_dir / f"{args.domain}-zone-after-{stamp}.json").write_text(
        json.dumps(after_zone, indent=2) + "\n")

    mail_after = mail_fingerprint(after_zone)
    if mail_after != mail_before:
        print("\n!!! NON-WEB RECORDS CHANGED — restore from the snapshot immediately !!!")
        for key in sorted(set(mail_before) | set(mail_after)):
            if mail_before.get(key) != mail_after.get(key):
                print(f"    {key}\n      before: {mail_before.get(key)}"
                      f"\n      after:  {mail_after.get(key)}")
        sys.exit(1)

    print(f"    ok — all {len(mail_after)} non-web record sets byte-identical")
    show([r for r in after_zone if r.get("name") in WEB_NAMES])

    # "merge" must not have left the old parking IP alongside the new one, or the
    # domain would round-robin between this server and the old host.
    apex_a = {r.get("content") for rec in after_zone
              if rec.get("name") == "@" and rec.get("type") == "A"
              for r in rec.get("records", [])}
    if apex_a != {args.ip}:
        print(f"\n!!! apex A is {sorted(apex_a)}, expected exactly ['{args.ip}']")
        print("    The merge kept the previous address; traffic would alternate hosts.")
        print("    Fix: remove the stale A record in hPanel -> DNS Zone Editor, or re-run")
        print("    this with --apply once more, then re-verify.")
        return 1
    print(f"    ok — apex A is exactly {args.ip}")

    print("\n==> DNS updated. Propagation typically 5-60 min at TTL 3600.")
    print(f"    then: bash deploy/install_vhost.sh {args.domain}")
    return 0


def verify(domain: str, ip: str) -> int:
    print(f"==> resolving {domain} (expecting {ip})")
    ok = True
    for host in (domain, f"www.{domain}"):
        for resolver in ("1.1.1.1", "8.8.8.8"):
            out = subprocess.run(["dig", "+short", host, "A", f"@{resolver}"],
                                 capture_output=True, text=True, timeout=20).stdout.split()
            hit = ip in out
            ok &= hit
            print(f"    {host:30} via {resolver:8} {out or ['<none>']}  "
                  f"{'OK' if hit else 'not yet'}")
    print("\nPROPAGATION:", "COMPLETE" if ok else "PENDING")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
