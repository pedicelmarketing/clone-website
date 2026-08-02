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

# Re-assert the two gates that matter most, against the exact tree about to ship.
echo "==> pre-publish gates (on build/, the tree that actually ships)"
python3 "$PD/tools/strip_demo_reviews.py" --check build
for pattern in 'data-demo="true"' 'rikicoach' '600 000 000' 'WIX Harmony'; do
  n="$({ grep -rFi "$pattern" "$PD/build" --include='*.html' -c 2>/dev/null || true; } \
        | awk -F: '{s+=$2} END{print s+0}')"
  [ "$n" -eq 0 ] || { echo "FATAL: '$pattern' present in build/ ($n) — refusing"; exit 1; }
done
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
