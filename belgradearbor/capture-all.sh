#!/usr/bin/env bash
set -u
PY=~/.venvs/nt-mirror/bin/python
CAP=~/.claude/skills/nt-site-mirror/scripts/capture_assets.py
declare -A ROUTES=(
  [en]="/en"
  [en-3d]="/en/3d"
  [en-residences]="/en/residences"
  [en-retail-spaces]="/en/retail-spaces"
  [en-business]="/en/business"
  [en-contact]="/en/contact"
  [en-about-the-investor]="/en/about-the-investor"
  [en-privacy-policy]="/en/privacy-policy"
  [en-residences-a-1-01]="/en/residences/a-1-01"
  [en-retail-spaces-b-lk1]="/en/retail-spaces/b-lk1"
)
fail=0
for name in "${!ROUTES[@]}"; do
  url="https://belgradearbor.rs${ROUTES[$name]}"
  echo "=== capturing $name -> $url"
  "$PY" "$CAP" "$url" -o "reports/${name}.asset-graph.json" \
    --scroll-steps 16 --step-wait 800 --settle-max 6000 --timeout 60000 \
    --mobile --probe-metadata
  rc=$?
  echo "--- $name exit=$rc"
  [ $rc -ne 0 ] && fail=1
done
echo "ALL_DONE fail=$fail"
