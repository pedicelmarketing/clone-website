#!/usr/bin/env bash
# Publish the built site to the live web root on spire (62.210.212.199).
#
# Workflow for an update:
#   1. edit site-v2/
#   2. build:    bash deploy/build_public.sh    (derives build/, runs the gates)
#   3. publish:  bash deploy/publish.sh
#
# This script refuses to publish a tree that build_public.sh did not bless, so
# demo reviews and placeholder slots cannot reach the public site by way of
# someone rsyncing site-v2/ directly.
set -euo pipefail

PD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$PD/build/"
DEST="/var/www/premiumpadelacademy/"

[ -f "$PD/build/index.html" ] || {
  echo "FATAL: build/ not built — run: bash deploy/build_public.sh"; exit 1; }

# Re-assert the gates against the exact tree about to ship, so rsyncing site-v2/
# by hand cannot route around build_public.sh.
echo "==> pre-publish gates (on build/, the tree that actually ships)"
count() { { grep -rFi "$1" "$PD/build" --include='*.html' -c 2>/dev/null || true; } \
            | awk -F: '{s+=$2} END{print s+0}'; }

for pattern in 'rikicoach' '600 000 000' 'WIX Harmony'; do
  n="$(count "$pattern")"
  [ "$n" -eq 0 ] || { echo "FATAL: '$pattern' present in build/ ($n) — refusing"; exit 1; }
done

# The example reviews may ship — the client's call — but only while the site is
# held back from search engines. Indexed invented reviews on a live commercial
# site are a different thing from an unapproved draft, so the two move together.
n_demo="$(count 'data-demo="true"')"
n_pages="$(find "$PD/build" -maxdepth 1 -name '*.html' | wc -l)"
n_noindex="$(count 'name="robots"')"
if [ "$n_demo" -gt 0 ]; then
  if [ "$n_noindex" -ne "$n_pages" ]; then
    echo "FATAL: $n_demo example review block(s) present but only $n_noindex/$n_pages"
    echo "       page(s) carry noindex. Rebuild with --keep-demo (which forces noindex),"
    echo "       or replace the examples with real reviews before allowing indexing."
    exit 1
  fi
  echo "    $n_demo example review block(s) shipping, noindex on all $n_pages page(s)"
fi
echo "    ok"

echo "==> publishing $SRC -> $DEST"
sudo mkdir -p "$DEST"
sudo rsync -a --delete \
  --exclude 'assets/partners.json' \
  --exclude 'assets/media-provenance.json' \
  "$SRC" "$DEST"

sudo chown -R www-data:www-data "$DEST"
sudo find "$DEST" -type d -exec chmod 755 {} +
sudo find "$DEST" -type f -exec chmod 644 {} +

if [ -f /etc/nginx/sites-enabled/premiumpadel.conf ]; then
  echo "==> nginx test + reload"
  sudo nginx -t && sudo systemctl reload nginx
else
  echo "==> note: no vhost installed yet (deploy/install_vhost.sh <domain>)"
  echo "    files are in place; the site goes live when the vhost + DNS land."
fi

echo "==> published. files: $(sudo find "$DEST" -type f | wc -l)"
