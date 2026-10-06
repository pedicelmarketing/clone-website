#!/usr/bin/env bash
set -euo pipefail
M="${MIRROR:-/home/openclaw/Coding/ Cloning Sites/clone-website/pedicelmarketing/mirror}"
P="$(cd "$(dirname "$0")" && pwd)/pages"
cp_page() { mkdir -p "$P/$2"; cp "$M/$1/index.html" "$P/$2/index.html"; }
cp_page _ .
cp_page services services
cp_page service-lead-generation outbound
cp_page service-brand-presence ai-content-video
cp_page service-web-development web-tracking
cp_page service-social-media paid-ads
cp_page service-lead-generation seo-ai-visibility
cp_page service-brand-presence hub
cp_page audit audit
cp_page about-our-marketing-agency about
cp_page contact-us contact
cp_page our-marketing-portfolio portfolio
for p in coeo isnmedical latabernafantastica sana; do cp_page "projects/$p" "projects/$p"; done
cp_page contact-us impressum
cp_page contact-us datenschutz
mkdir -p "$P/404"; cp "$M/404.html" "$P/404/index.html"
echo "imported $(find "$P" -name index.html | wc -l) pages"
