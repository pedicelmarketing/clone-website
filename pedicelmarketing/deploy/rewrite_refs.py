#!/usr/bin/env python3
"""Phase A5 - rewrite captured references to local, root-relative paths.

Construction-time accommodation (nt-site-mirror SKILL.md 'Static Mirror Workflow' step 5):
local path/origin resolution only. No copy, branding, layout, media-selection, or behaviour
change. Every rewrite is driven by mirror-manifest.json#source_url_map, which is the
machine-authoritative record of what was actually downloaded and where it landed - the path
scheme is never guessed.

Root-relative (/_external/host/...) is used because both the local validation server and the
production nginx serve from the mirror root, so one form works in both.

Run with --check to report without writing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from urllib.parse import quote, unquote

STAGING_HOSTS = ("new-pedicel-website.webflow.io",)
CANONICAL_DOMAIN = "www.pedicelmarketing.com"
REWRITABLE_SUFFIXES = (".html", ".css", ".js")

# Tracking/telemetry hosts are deliberately NOT localised: they are live beacons and
# replaying them locally would be both wrong and a fidelity lie. See SKILL.md
# 'Conditional Rule Activation > Analytics/tracking'.
KEEP_EXTERNAL = (
    "us-assets.i.posthog.com", "us.i.posthog.com", "www.googletagmanager.com",
    "analytics.google.com", "region1.analytics.google.com", "stats.g.doubleclick.net",
    "assets.apollo.io", "aplo-evnt.com", "connect.facebook.net", "www.google.com",
    "www.google.co.in", "www.google.fr", "calendly.com",
)


def load_map(mirror_dir: str) -> dict[str, str]:
    manifest_path = os.path.join(mirror_dir, "mirror-manifest.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    url_map: dict[str, str] = {}
    for url, info in (manifest.get("source_url_map") or {}).items():
        local = info.get("local_path") if isinstance(info, dict) else info
        if not local:
            continue
        # local_path is a filesystem path and, after fix_encoded_filenames.py, holds the
        # DECODED name (real spaces). A URL in markup must be encoded, so quote it back.
        # This round-trips correctly in both directions:
        #   disk "Careers Image.webp"    -> href ".../Careers%20Image.webp"
        #   disk "strategy%20(1).webp"   -> href ".../strategy%2520(1).webp"
        # In each case the server decodes exactly once and lands on the real file.
        url_map[url] = "/" + quote(local.lstrip("/"), safe="/")
    return url_map


def iter_files(mirror_dir: str):
    for root, dirs, files in os.walk(mirror_dir):
        dirs[:] = [d for d in dirs if d != "_ntsm"]
        for name in files:
            if name.endswith(REWRITABLE_SUFFIXES):
                yield os.path.join(root, name)


def rewrite_text(text: str, url_map: dict[str, str], stats: Counter) -> str:
    # Longest-first so a URL that is a prefix of another never steals its replacement.
    for url in sorted(url_map, key=len, reverse=True):
        local = url_map[url]
        for variant in (url, url.replace("&", "&amp;")):
            if variant in text:
                stats["asset_refs"] += text.count(variant)
                text = text.replace(variant, local)

    # Staging-absolute internal links -> root-relative.
    for host in STAGING_HOSTS:
        for scheme in ("https://", "http://", "//"):
            token = f"{scheme}{host}"
            if token in text:
                stats["internal_links"] += text.count(token)
                text = text.replace(token, "")

    # Webflow stamps the publishing host on <html>; restore the real domain.
    for host in STAGING_HOSTS:
        if f'data-wf-domain="{host}"' in text:
            stats["wf_domain"] += 1
            text = text.replace(f'data-wf-domain="{host}"', f'data-wf-domain="{CANONICAL_DOMAIN}"')

    # SRI hashes are computed over the CDN bytes. Served from our own origin the hash no
    # longer applies, and any byte-level difference makes the browser refuse the file
    # outright - an unstyled page. Drop integrity/crossorigin on now-local subresources.
    def drop_sri(match: re.Match) -> str:
        tag = match.group(0)
        if 'href="/' not in tag and 'src="/' not in tag:
            return tag  # still external - leave its SRI intact
        new = re.sub(r'\s+integrity="[^"]*"', "", tag)
        new = re.sub(r'\s+crossorigin="[^"]*"', "", new)
        if new != tag:
            stats["sri_stripped"] += 1
        return new

    text = re.sub(r"<(?:link|script)\b[^>]*>", drop_sri, text)

    # Once every asset is local, a preconnect/dns-prefetch to the Webflow CDN just opens a
    # TLS connection to a host the page never uses again. Drop it so the deployed site has
    # no live dependency on Webflow.
    def drop_preconnect(match: re.Match) -> str:
        tag = match.group(0)
        if re.search(r'rel="(?:preconnect|dns-prefetch)"', tag) and re.search(
            r'href="https://(?:cdn\.prod\.website-files\.com|d3e54v103j8qbb\.cloudfront\.net)"', tag
        ):
            stats["preconnect_dropped"] += 1
            return ""
        return tag

    text = re.sub(r"<link\b[^>]*>", drop_preconnect, text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mirror", help="mirror output directory")
    parser.add_argument("--check", action="store_true", help="report only, do not write")
    args = parser.parse_args()

    mirror = os.path.abspath(args.mirror)
    url_map = load_map(mirror)
    print(f"source_url_map entries: {len(url_map)}")

    stats: Counter = Counter()
    changed = 0
    files = list(iter_files(mirror))
    for path in files:
        with open(path, encoding="utf-8", errors="surrogateescape") as handle:
            original = handle.read()
        updated = rewrite_text(original, url_map, stats)
        if updated != original:
            changed += 1
            if not args.check:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as handle:
                    handle.write(updated)

    print(f"files scanned : {len(files)}")
    print(f"files changed : {changed}{' (dry run)' if args.check else ''}")
    for key in ("asset_refs", "internal_links", "wf_domain", "sri_stripped", "preconnect_dropped"):
        print(f"  {key:<19} {stats[key]}")

    # Post-conditions. These are gates, not commentary: a surviving CDN reference means the
    # deployed site would hotlink Webflow, and a surviving noindex would destroy SEO silently.
    # A *true* external reference has a scheme. The bare hostname also occurs inside the
    # local path (/_external/cdn.prod.website-files.com/...), which is exactly what we want
    # and must not be counted as a failure.
    external_re = re.compile(
        r'https?://(?:cdn\.prod\.website-files\.com|d3e54v103j8qbb\.cloudfront\.net)'
    )
    residual: Counter = Counter()
    noindex: list[str] = []
    local_refs: set[str] = set()
    for path in files:
        with open(path, encoding="utf-8", errors="surrogateescape") as handle:
            body = handle.read()
        for hit in external_re.findall(body):
            residual[hit] += 1
        # Webflow filenames contain literal parentheses (e.g. project-LTF(2).jpg) and the
        # markup HTML-escapes surrounding quotes, so allow '(' / ')' then trim entities and
        # rebalance - otherwise the check truncates valid refs and reports false dangles.
        for ref in re.findall(r'/_external/[^\s"\'<>]+', body):
            ref = ref.split("&quot")[0].split("&#")[0].split("?")[0].rstrip('\\",\';')
            while ref.endswith(")") and ref.count(")") > ref.count("("):
                ref = ref[:-1]
            if ref:
                local_refs.add(ref.rstrip('\\",\';'))
        if path.endswith(".html") and re.search(r'name=["\']robots["\'][^>]*noindex', body, re.I):
            noindex.append(os.path.relpath(path, mirror))

    # Every local reference must resolve to a real file, or the deployed site 404s on it.
    from urllib.parse import unquote
    dangling = sorted(
        ref for ref in local_refs
        if not os.path.exists(os.path.join(mirror, unquote(ref).lstrip("/")))
        and not os.path.exists(os.path.join(mirror, ref.lstrip("/")))
    )
    fonts = [r for r in local_refs if r.lower().endswith((".otf", ".ttf", ".woff", ".woff2"))]

    print("\n-- gates --")
    if residual:
        print("  FAIL residual absolute CDN URLs:")
        for host, count in residual.items():
            print(f"        {host}: {count}")
    else:
        print("  PASS no absolute Webflow CDN URLs remain")

    print(f"  {'FAIL' if noindex else 'PASS'} noindex directives: {len(noindex)}"
          + (f" {noindex[:5]}" if noindex else ""))
    print(f"  {'FAIL' if dangling else 'PASS'} local refs resolve on disk "
          f"({len(local_refs) - len(dangling)}/{len(local_refs)})")
    for ref in dangling[:8]:
        print(f"        dangling: {ref}")
    print(f"  INFO distinct local font references: {len(fonts)}")

    failed = bool(residual or noindex or dangling)
    return 1 if failed and not args.check else 0


if __name__ == "__main__":
    sys.exit(main())
