#!/usr/bin/env bash
# Publish the built mirror to the live web root on spire.
#
# The site is served by nginx from /var/www/pedicelmarketing on this box
# (spire, 62.210.212.199). This script pushes the current built mirror/ there.
#
# Workflow for an update:
#   1. edit / rebuild:  bash deploy/build_mirror.sh   (rebuilds mirror/ from pristine)
#   2. publish:         bash deploy/publish.sh
#
# --delete keeps the web root an exact match for mirror/, minus bookkeeping files.
set -euo pipefail

PD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$PD/mirror/"
DEST="/var/www/pedicelmarketing/"

[ -f "$PD/mirror/_/index.html" ] || { echo "FATAL: mirror/ not built (run build_mirror.sh)"; exit 1; }

echo "==> publishing $SRC -> $DEST"
sudo rsync -a --delete \
  --exclude 'mirror-manifest.json' \
  --exclude 'serve-contract.json' \
  --exclude 'serve-local.py' \
  --exclude '_ntsm/' \
  "$SRC" "$DEST"

# 404 page is fetched/rewritten separately and is not part of mirror/; preserve it.
sudo chown -R www-data:www-data "$DEST"
sudo find "$DEST" -type d -exec chmod 755 {} +
sudo find "$DEST" -type f -exec chmod 644 {} +

echo "==> nginx test + reload"
sudo nginx -t && sudo systemctl reload nginx

echo "==> published. files: $(sudo find "$DEST" -type f | wc -l)"
