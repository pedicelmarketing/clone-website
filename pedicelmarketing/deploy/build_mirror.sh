#!/usr/bin/env bash
# Rebuild the deployable mirror from the pristine capture, deterministically.
#
# mirror-pristine/ is the untouched download (nt-site-mirror output, no rewrites).
# This script applies the two construction-time accommodations on top of it, in the only
# order that works:
#
#   1. asset acquisition must finish FIRST - mirror_assets.py --resume hashes every file
#      and refuses to overwrite one that changed, so any rewrite before the asset set is
#      final locks out later additions
#   2. fix_encoded_filenames.py - rename %XX filenames to their decoded form, because web
#      servers decode the request path before the filesystem lookup
#   3. rewrite_refs.py - point references at local paths, strip now-invalid SRI hashes,
#      restore data-wf-domain, drop the dead CDN preconnect
#
# Idempotent: safe to re-run. Verifies its own gates and exits nonzero on failure.
set -euo pipefail

PD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SK="$HOME/.claude/skills/nt-site-mirror"
AUTH="owner-operated restore of pedicelmarketing.com"

[ -d "$PD/mirror-pristine" ] || { echo "FATAL: mirror-pristine/ missing - re-run capture"; exit 1; }

echo "==> restoring mirror/ from mirror-pristine/"
rm -rf "$PD/mirror"
cp -a "$PD/mirror-pristine" "$PD/mirror"

# Supplementary acquisitions. Routed through --extra-urls per SKILL.md rather than a side
# channel, so the manifest keeps a coherent audit trail.
#   round2/3 - srcset responsive variants, favicons, og:image, CMS rich-text images that a
#              first-load capture never requests (a browser fetches one srcset candidate)
#   round4   - Webflow's first-party analytics script at its hashed path
for round in round2 round3 round4; do
  extra="$PD/reports/extra-urls-$round.jsonl"
  [ -f "$extra" ] || continue
  echo "==> acquiring supplementary assets: $round ($(wc -l < "$extra") urls)"
  python3 "$SK/scripts/mirror_assets.py" "$PD"/reports/graphs/*.asset-graph.json \
    --out "$PD/mirror" --resume \
    --allow-host cdn.prod.website-files.com \
    --allow-host d3e54v103j8qbb.cloudfront.net \
    --extra-urls "$extra" \
    --authorized "$AUTH" \
    > "$PD/reports/mirror-$round.log" 2>&1
  # '|| true' so a no-match grep does not trip 'set -e'; a real acquisition failure has
  # already exited above via mirror_assets.py's nonzero status.
  grep -E 'captured now|reused' "$PD/reports/mirror-$round.log" | tail -1 || true
done

echo "==> reconciling percent-encoded filenames"
python3 "$PD/deploy/fix_encoded_filenames.py" "$PD/mirror"

echo "==> rewriting references to local paths"
python3 "$PD/deploy/rewrite_refs.py" "$PD/mirror"

# Pages built elsewhere and served beside the mirror (e.g. extras/brand/ — the brand
# questionnaire, built by pedicel-ai apps/brand-q/deploy.sh). Copied last, untouched.
if [ -d "$PD/extras" ]; then
  echo "==> adding extras/ ($(ls "$PD/extras" | tr '\n' ' '))"
  cp -a "$PD/extras/." "$PD/mirror/"
fi

echo
echo "==> build complete"
echo "    files: $(find "$PD/mirror" -type f | wc -l)   size: $(du -sh "$PD/mirror" | cut -f1)"
