#!/usr/bin/env bash
# Deploy nexumpadel.es to Cloudflare Pages from the operator-declared launch zip.
#
# The zip ships in DRAFT state (every page carries noindex + a "Draft:" banner,
# and there is no robots.txt/sitemap.xml). Publishing it raw would de-index the
# site and undo the 2026-08-10 launch. This script therefore re-applies the same
# launch treatment used on 10 Aug before anything is uploaded, then verifies the
# deployed result byte-for-byte.
#
# Self-validating: exits nonzero if the tree is not launch-clean, if any route
# fails, or if any deployed file differs from what was built.
#
#   ./deploy/cloudflare_pages.sh [path/to/launch.zip]
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="$(cd "$REPO/../.." && pwd)"
ZIP="${1:-$WORKSPACE/nexum-padel-web-final (1).zip}"

PROJECT="nexumpadel"
ACCOUNT_ID="b56751e36842462c119a2063e60935a5"     # Info@nexumpadel.es's Account
CF_EMAIL="info@nexumpadel.es"
PAGES_URL="https://${PROJECT}.pages.dev"
LASTMOD="$(date -u +%F)"

say(){ printf '\n\033[1m== %s\033[0m\n' "$*"; }
die(){ printf '\033[31mFAIL: %s\033[0m\n' "$*" >&2; exit 1; }

[ -f "$ZIP" ] || die "launch zip not found: $ZIP"

# ---- credentials -------------------------------------------------------------
# Global API Key lives in the workspace .env; it authenticates as info@nexumpadel.es.
# NOTE: this is a *global* key with full account power. Prefer a scoped token
# (Pages:Edit + Zone:Edit + DNS:Edit) as soon as one exists.
if [ -z "${CLOUDFLARE_API_KEY:-}" ]; then
  # shellcheck disable=SC1091
  [ -f "$WORKSPACE/.env" ] && { set -a; . "$WORKSPACE/.env"; set +a; }
fi
[ -n "${CLOUDFLARE_API_KEY:-}" ] || die "CLOUDFLARE_API_KEY unset (expected in $WORKSPACE/.env)"

export CLOUDFLARE_API_KEY CLOUDFLARE_EMAIL="$CF_EMAIL" CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"

# ---- stage + launch treatment ------------------------------------------------
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
say "Staging $(basename "$ZIP")"
python3 -m zipfile -e "$ZIP" "$STAGE/"

say "Applying launch treatment (noindex off, robots.txt + sitemap.xml)"
python3 "$REPO/tools/draft_noindex.py" --root "$STAGE" --off
python3 "$REPO/tools/seo_files.py" --root "$STAGE" --launch --lastmod "$LASTMOD"

# ---- pre-upload gate ---------------------------------------------------------
say "Pre-upload gate"
if grep -rlq "noindex" "$STAGE" --include=*.html 2>/dev/null; then
  grep -rl "noindex" "$STAGE" --include=*.html >&2
  die "pages still carry noindex — refusing to publish a de-indexing build"
fi
grep -rlq "Draft:" "$STAGE" --include=*.html 2>/dev/null && die "draft banner still present"
[ -f "$STAGE/robots.txt" ]  || die "robots.txt missing"
[ -f "$STAGE/sitemap.xml" ] || die "sitemap.xml missing"
grep -q "Allow: /" "$STAGE/robots.txt" || die "robots.txt does not allow crawling"
if grep -rlq "data-demo" "$STAGE" 2>/dev/null; then
  die "demo review blocks present — those may only ship behind full noindex"
fi
PAGES=$(find "$STAGE" -name '*.html' | wc -l)
FILES=$(find "$STAGE" -type f | wc -l)
echo "  $FILES files, $PAGES pages, zero noindex, robots+sitemap present"
[ "$PAGES" -eq 10 ] || die "expected 10 pages, found $PAGES"

# ---- deploy ------------------------------------------------------------------
say "Deploying to Cloudflare Pages ($PROJECT)"
npx --yes wrangler@latest pages deploy "$STAGE" \
  --project-name="$PROJECT" --branch=main --commit-dirty=true

# ---- post-deploy verification (the real deliverable) -------------------------
# Cloudflare's edge can return transient 522s on a cold deploy, so each fetch
# retries. A file is only accepted when a single 200 response hashes equal to
# the local build — status and body must come from the same request.
say "Verifying live deployment at $PAGES_URL"
sleep 5
fetch_ok(){ # $1 = relative path, $2 = expected md5 ; echoes "code md5"
  local rel="$1" tmp code sum
  for _ in 1 2 3 4; do
    tmp="$(mktemp)"
    code=$(curl -sL --max-time 40 -o "$tmp" -w '%{http_code}' "$PAGES_URL/$rel" || echo 000)
    sum=$(md5sum "$tmp" | cut -d' ' -f1); rm -f "$tmp"
    [ "$code" = "200" ] && [ "$sum" = "$2" ] && { echo "$code $sum"; return 0; }
    sleep 3
  done
  echo "$code $sum"; return 1
}

bad=0
while IFS= read -r f; do
  rel="${f#"$STAGE"/}"
  exp=$(md5sum "$f" | cut -d' ' -f1)
  if ! out=$(fetch_ok "$rel" "$exp"); then
    echo "  BAD  $rel  ($out)"; bad=$((bad+1))
  fi
done < <(find "$STAGE" -type f | sort)

[ "$bad" -eq 0 ] || die "$bad/$FILES deployed files did not match the build"
echo "  all $FILES files verified byte-identical on $PAGES_URL"

# indexability must survive the round trip
for p in "" camps.html en/index.html; do
  if curl -sL --max-time 30 "$PAGES_URL/$p" | grep -qi '<meta name="robots"'; then
    die "live page /$p carries a robots meta tag"
  fi
done
echo "  live pages carry no robots meta ✓"

say "DONE — $PAGES_URL is live and verified"
echo "DNS cutover is a SEPARATE, approval-gated step: see deploy/cloudflare_dns_plan.md"
