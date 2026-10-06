#!/usr/bin/env python3
"""Add a TXT record to the zone without disturbing anything else.

Written for the Google Search Console domain-property verification token, but
it will add any apex TXT value.

Why this is not a one-line curl: the apex TXT record SET already holds the SPF
record. SPF is what stops nexumpadel.es mail being treated as forged, and losing
it breaks outbound email in a way nobody notices until deliverability collapses
days later. A write that replaces the apex TXT set instead of appending to it
would do exactly that.

So, mirroring deploy/dns_cutover.py:

  * the full zone is snapshotted to dns/ before anything is sent
  * the request uses overwrite=false, which Hostinger merges into the existing
    set rather than replacing it
  * afterwards the zone is re-read and checked three ways: the new value is
    present, the SPF record is still present, and every other record set in the
    zone (MX, DKIM, DMARC, autoconfig, A, CNAME) is byte-identical
  * any mismatch aborts loudly, pointing at the snapshot

    python3 deploy/dns_txt_add.py nexumpadel.es "google-site-verification=..."
    python3 deploy/dns_txt_add.py nexumpadel.es "..." --apply

Stdlib only. Needs HOSTINGER_API_TOKEN[_DOMAIN] in ~/.config/secrets.env.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dns_cutover import call, show                      # noqa: E402  (shared client)

PROJECT = Path(__file__).resolve().parent.parent


def fingerprint(zone: list, exclude: tuple[str, str]) -> dict:
    """Every record set except the one being changed, in a comparable form."""
    return {
        f"{rec.get('name')}|{rec.get('type')}": sorted(
            r.get("content", "") for r in rec.get("records", []))
        for rec in zone
        if (rec.get("name"), rec.get("type")) != exclude
    }


def apex_txt(zone: list) -> list[str]:
    return sorted(
        r.get("content", "").strip('"')
        for rec in zone if rec.get("name") == "@" and rec.get("type") == "TXT"
        for r in rec.get("records", []))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain")
    ap.add_argument("value", help='TXT content, e.g. "google-site-verification=..."')
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ttl", type=int, default=3600)
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dns_dir = PROJECT / "dns"
    dns_dir.mkdir(exist_ok=True)

    status, zone = call("GET", args.domain)
    if status != 200 or not isinstance(zone, list):
        sys.exit(f"FATAL: could not read the zone (HTTP {status}).")

    before = dns_dir / f"{args.domain}-zone-before-txt-{stamp}.json"
    before.write_text(json.dumps(zone, indent=2) + "\n")
    print(f"==> snapshot written: {before.relative_to(PROJECT)}\n")
    show(zone)

    txt_before = apex_txt(zone)
    spf = [t for t in txt_before if t.lower().startswith("v=spf1")]
    print(f"\n==> apex TXT currently holds {len(txt_before)} record(s):")
    for t in txt_before:
        print(f"    {t}")
    if not spf:
        sys.exit("\nFATAL: no SPF record found in the apex TXT set. Refusing to "
                 "write — this zone is not in the state this tool expects.")
    print(f"    SPF present: {spf[0]}")

    if args.value.strip('"') in txt_before:
        print(f"\n==> already present, nothing to do: {args.value}")
        return 0

    payload = {"overwrite": False,
               "zone": [{"name": "@", "type": "TXT", "ttl": args.ttl,
                         "records": [{"content": args.value}]}]}
    print("\n==> planned write (this is the ENTIRE request body):")
    print(json.dumps(payload, indent=2))
    print("\n    overwrite=false -> merged into the existing apex TXT set,")
    print("    so the SPF record above is retained alongside the new value.")

    if not args.apply:
        print("\nDRY RUN — nothing sent. Re-run with --apply to perform it.")
        return 0

    print("\n==> applying")
    status, resp = call("PUT", args.domain, payload)
    print(f"    HTTP {status}")
    if status not in (200, 201, 204):
        print(json.dumps(resp, indent=2)[:1500])
        sys.exit("FATAL: write rejected — zone unchanged.")

    status, after = call("GET", args.domain)
    if status != 200 or not isinstance(after, list):
        sys.exit("FATAL: could not re-read the zone to verify. CHECK MAIL MANUALLY "
                 f"and compare against {before}.")
    (dns_dir / f"{args.domain}-zone-after-txt-{stamp}.json").write_text(
        json.dumps(after, indent=2) + "\n")

    print("\n==> verifying")
    problems = 0

    txt_after = apex_txt(after)
    if args.value.strip('"') not in txt_after:
        print("  FAIL: the new TXT value is not in the zone after the write")
        problems += 1
    else:
        print("  ok: new TXT value present")

    spf_after = [t for t in txt_after if t.lower().startswith("v=spf1")]
    if spf_after != spf:
        print(f"  FAIL: SPF CHANGED. before={spf} after={spf_after}")
        problems += 1
    else:
        print(f"  ok: SPF unchanged ({spf[0]})")

    fb, fa = fingerprint(zone, ("@", "TXT")), fingerprint(after, ("@", "TXT"))
    if fb != fa:
        print("  FAIL: other record sets changed:")
        for key in sorted(set(fb) | set(fa)):
            if fb.get(key) != fa.get(key):
                print(f"      {key}: {fb.get(key)} -> {fa.get(key)}")
        problems += 1
    else:
        print(f"  ok: all {len(fb)} other record set(s) byte-identical "
              "(MX, DKIM, DMARC, autoconfig, A, CNAME)")

    if problems:
        print(f"\n!!! {problems} problem(s) — restore from {before} immediately !!!")
        return 1
    print("\n==> done. DNS propagation is typically minutes; verify with:")
    print(f"    dig +short TXT {args.domain}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
