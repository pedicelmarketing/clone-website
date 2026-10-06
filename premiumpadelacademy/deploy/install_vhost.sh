#!/usr/bin/env bash
# Install the nginx vhost for the padel site and issue TLS.
#
#   bash deploy/install_vhost.sh nexumpadel.es
#
# Run this only AFTER the domain's A records point at 62.210.212.199 — certbot's
# HTTP-01 challenge resolves the name from the public internet, so it fails if
# DNS has not propagated yet. deploy/dns_cutover.py does the DNS half.
set -euo pipefail

PD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="${1:-}"
[ -n "$DOMAIN" ] || { echo "usage: $0 <domain>   e.g. $0 nexumpadel.es"; exit 2; }

TEMPLATE="$PD/deploy/nginx-premiumpadel.conf.template"
RENDERED="$PD/deploy/nginx-premiumpadel.conf.rendered"
TARGET="/etc/nginx/sites-available/premiumpadel.conf"

echo "==> checking DNS points here before touching nginx"
IP="$(curl -s --max-time 10 https://ifconfig.me/ip || echo "")"
RESOLVED="$(dig +short "$DOMAIN" A @1.1.1.1 | tail -1)"
echo "    this host : ${IP:-unknown}"
echo "    $DOMAIN -> ${RESOLVED:-<unresolved>}"
if [ "$RESOLVED" != "$IP" ]; then
  echo "    WARNING: $DOMAIN does not resolve to this server yet."
  echo "    nginx will install, but certbot will fail until DNS propagates."
  read -r -p "    continue anyway? [y/N] " reply
  [ "$reply" = "y" ] || { echo "aborted"; exit 1; }
fi

echo "==> rendering vhost for $DOMAIN"
sed "s/__DOMAIN__/$DOMAIN/g" "$TEMPLATE" > "$RENDERED"
grep -q "__DOMAIN__" "$RENDERED" && { echo "FATAL: unsubstituted __DOMAIN__"; exit 1; }

[ -d /var/www/premiumpadelacademy ] || {
  echo "FATAL: /var/www/premiumpadelacademy missing — run deploy/publish.sh first"; exit 1; }

echo "==> installing $TARGET"
sudo cp "$RENDERED" "$TARGET"
sudo ln -sfn "$TARGET" /etc/nginx/sites-enabled/premiumpadel.conf

echo "==> nginx config test"
sudo nginx -t

# Guard the neighbours: pedicelmarketing must remain the default server for this
# address, and must still be a valid vhost after our file lands.
echo "==> verifying pedicelmarketing is unaffected"
sudo nginx -T 2>/dev/null | grep -q "pedicelmarketing.com" \
  || { echo "FATAL: pedicelmarketing vhost vanished from the merged config"; exit 1; }
echo "    ok"

sudo systemctl reload nginx

echo "==> requesting TLS certificate"
sudo certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
  --non-interactive --agree-tos --redirect \
  -m pedicelsocial@gmail.com

echo "==> live check"
for host in "$DOMAIN" "www.$DOMAIN"; do
  printf '    https://%-28s %s\n' "$host" \
    "$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "https://$host/" || echo FAIL)"
done
echo "==> done"
