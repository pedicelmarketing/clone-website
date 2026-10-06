#!/usr/bin/env bash
# Build, check and publish pedicelmarketing.ch to the live web root on spire.
#
#   bash deploy/publish.sh
#
# Refuses to run until hosting exists (nginx config enabled) and refuses to
# publish a build that fails build.py or checks.py.
#
# --delete keeps the web root an exact match for dist/. dist/_external is a
# local-preview symlink and is excluded (anchored to the top level): nginx serves /_external/ from the
# .com web root (/var/www/pedicelmarketing/_external/) by alias.
set -euo pipefail

PD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PD"
DEST="/var/www/pedicelmarketing-ch/"

# Guard: hosting must exist first (see deploy/nginx-pedicelmarketing-ch.conf header).
if ! ls /etc/nginx/sites-enabled/ 2>/dev/null | grep -q 'pedicelmarketing-ch'; then
  echo "FATAL: no pedicelmarketing-ch config in /etc/nginx/sites-enabled/." >&2
  echo "       Install deploy/nginx-pedicelmarketing-ch.conf first (see its header)." >&2
  exit 1
fi

echo "==> build + checks"
python3 build.py && python3 checks.py dist || { echo "FATAL: build or checks failed, not publishing" >&2; exit 1; }
[ -f dist/index.html ] || { echo "FATAL: dist/index.html missing" >&2; exit 1; }

echo "==> nginx config test (before touching files)"
sudo nginx -t || { echo "FATAL: nginx -t failed, not publishing" >&2; exit 1; }

echo "==> publishing dist/ -> $DEST"
sudo mkdir -p "$DEST"
sudo rsync -a --delete --exclude /_external dist/ "$DEST"

sudo chown -R www-data:www-data "$DEST"
sudo find "$DEST" -type d -exec chmod 755 {} +
sudo find "$DEST" -type f -exec chmod 644 {} +

echo "==> nginx test + reload"
sudo nginx -t || { echo "FATAL: nginx -t failed after publish" >&2; exit 1; }
sudo systemctl reload nginx || { echo "FATAL: nginx reload failed" >&2; exit 1; }

echo "==> published. files: $(sudo find "$DEST" -type f | wc -l)"
