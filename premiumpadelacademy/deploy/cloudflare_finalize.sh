#!/usr/bin/env bash
# Final leg of the nexumpadel.es cutover: attach the apex + www to the Pages
# project once Cloudflare is authoritative, then prove the result.
#
# Run only after the .es registry delegates to clara/ruben.ns.cloudflare.com.
# Refuses to touch anything if the zone is not active, and fails loudly if the
# mail record set is not intact afterwards.
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="$(cd "$REPO/../.." && pwd)"

ZONE="nexumpadel.es"
PROJECT="nexumpadel"
ACCOUNT_ID="b56751e36842462c119a2063e60935a5"
CF_EMAIL="info@nexumpadel.es"
API="https://api.cloudflare.com/client/v4"

say(){ printf '\n\033[1m== %s\033[0m\n' "$*"; }
die(){ printf '\033[31mFAIL: %s\033[0m\n' "$*" >&2; exit 1; }

if [ -z "${CLOUDFLARE_API_KEY:-}" ]; then
  # shellcheck disable=SC1091
  [ -f "$WORKSPACE/.env" ] && { set -a; . "$WORKSPACE/.env"; set +a; }
fi
[ -n "${CLOUDFLARE_API_KEY:-}" ] || die "CLOUDFLARE_API_KEY unset"
AUTH=(-H "X-Auth-Email: $CF_EMAIL" -H "X-Auth-Key: $CLOUDFLARE_API_KEY" -H "Content-Type: application/json")

jq_(){ python3 -c "import json,sys;d=json.load(sys.stdin);$1"; }

# ---- gate: zone must be active ----------------------------------------------
say "Checking zone status"
ZID=$(curl -s "$API/zones?name=$ZONE" "${AUTH[@]}" | jq_ "print((d.get('result') or [{}])[0].get('id',''))")
[ -n "$ZID" ] || die "zone $ZONE not found"
STATUS=$(curl -s "$API/zones/$ZID" "${AUTH[@]}" | jq_ "print((d.get('result') or {}).get('status',''))")
echo "  zone $ZID status=$STATUS"
[ "$STATUS" = "active" ] || die "zone is '$STATUS', not active — registry delegation has not landed yet"

# ---- attach custom domains ---------------------------------------------------
say "Attaching custom domains to Pages project '$PROJECT'"
for d in "$ZONE" "www.$ZONE"; do
  out=$(curl -s -X POST "$API/accounts/$ACCOUNT_ID/pages/projects/$PROJECT/domains" \
        "${AUTH[@]}" --data "{\"name\":\"$d\"}")
  ok=$(echo "$out" | jq_ "print(d.get('success'))")
  if [ "$ok" = "True" ]; then echo "  added $d"
  else
    # already attached is not an error
    echo "$out" | grep -qi "already\|exists" && echo "  $d already attached" \
      || die "could not attach $d: $(echo "$out" | head -c 300)"
  fi
done

say "Waiting for certificate + domain activation"
for i in $(seq 1 40); do
  st=$(curl -s "$API/accounts/$ACCOUNT_ID/pages/projects/$PROJECT/domains" "${AUTH[@]}" \
       | jq_ "print(' '.join(f\"{x['name']}={x.get('status')}\" for x in (d.get('result') or [])))")
  echo "  [$i] $st"
  echo "$st" | grep -q "active" && ! echo "$st" | grep -qi "pending\|initializing" && break
  sleep 15
done

# ---- verification: the real deliverable --------------------------------------
say "Verifying the live domain"
fail=0
for i in $(seq 1 30); do
  code=$(curl -sL --max-time 25 -o /dev/null -w '%{http_code}' "https://$ZONE/" || echo 000)
  srv=$(curl -sI --max-time 25 "https://$ZONE/" 2>/dev/null | grep -i '^server:' | tr -d '\r' | awk '{print $2}')
  echo "  [$i] https://$ZONE/ -> $code (server: ${srv:-?})"
  [ "$code" = "200" ] && echo "$srv" | grep -qi cloudflare && break
  sleep 15
done
[ "$code" = "200" ] || { echo "  site not 200"; fail=$((fail+1)); }
echo "$srv" | grep -qi cloudflare || { echo "  not served by Cloudflare"; fail=$((fail+1)); }

for p in / /camps.html /clubs.html /contacto.html /privacidad.html \
         /en/ /en/camps.html /en/clubs.html /en/contact.html /en/privacy.html \
         /robots.txt /sitemap.xml; do
  for _ in 1 2 3; do
    c=$(curl -sL --max-time 25 -o /dev/null -w '%{http_code}' "https://$ZONE$p" || echo 000)
    [ "$c" = "200" ] && break; sleep 3
  done
  [ "$c" = "200" ] || { echo "  route $p -> $c"; fail=$((fail+1)); }
done
echo "  routes checked"

curl -s "https://$ZONE/robots.txt" | grep -q "Allow: /" || { echo "  robots.txt not allowing"; fail=$((fail+1)); }
curl -sL "https://$ZONE/" | grep -qi '<meta name="robots"' && { echo "  apex carries robots meta"; fail=$((fail+1)); }

# ---- mail must be untouched ---------------------------------------------------
say "Verifying mail records survived the cutover"
chk(){ # label, name, type, expected-substring
  local got; got=$(dig +short "$2" "$3" @1.1.1.1 2>/dev/null | tr '\n' ' ')
  if echo "$got" | grep -qi "$4"; then printf '  ok   %-30s %s\n' "$1" "$got"
  else printf '  FAIL %-30s %s\n' "$1" "${got:-(empty)}"; fail=$((fail+1)); fi
}
chk "MX"           "$ZONE"                          MX    "mx1.hostinger.com"
chk "SPF"          "$ZONE"                          TXT   "spf1"
chk "DMARC"        "_dmarc.$ZONE"                   TXT   "DMARC1"
chk "DKIM a"       "hostingermail-a._domainkey.$ZONE" CNAME "dkim.mail.hostinger.com"
chk "DKIM b"       "hostingermail-b._domainkey.$ZONE" CNAME "dkim.mail.hostinger.com"
chk "DKIM c"       "hostingermail-c._domainkey.$ZONE" CNAME "dkim.mail.hostinger.com"
chk "autodiscover" "autodiscover.$ZONE"             CNAME "autodiscover.mail.hostinger.com"
chk "autoconfig"   "autoconfig.$ZONE"               CNAME "autoconfig.mail.hostinger.com"
chk "google-verify" "$ZONE"                         TXT   "google-site-verification"

echo
[ "$fail" -eq 0 ] || die "$fail check(s) failed — consider reverting nameservers to byte/pixel.dns-parking.com"
say "CUTOVER COMPLETE — https://$ZONE served by Cloudflare Pages, mail records intact"
echo "Send a real test message both ways through info@$ZONE and confirm dkim=pass / spf=pass."
echo "Keep the Scaleway vhost (62.210.212.199) up for 48h as the rollback target."
