#!/usr/bin/env bash
set -u
PY=~/.venvs/nt-mirror/bin/python
VP=~/.claude/skills/nt-site-mirror/scripts/viewports.py
ROUTES="/en /en/3d /en/residences /en/retail-spaces /en/business /en/contact /en/about-the-investor /en/privacy-policy /en/residences/a-1-01 /en/retail-spaces/b-lk1"
for r in $ROUTES; do
  name=$(echo "$r" | sed 's#^/##; s#/#-#g')
  echo "=== paired validate $r"
  "$PY" "$VP" "https://belgradearbor.rs$r" "http://127.0.0.1:8100$r" \
    --source-url "https://belgradearbor.rs$r" \
    --out "reports/paired/$name" --viewports desktop,tablet,mobile \
    --timeout 90000 --settle-ms 5000 --scroll-steps 8 --step-wait 500
  echo "--- $name exit=$?"
done
echo "PAIRED_DONE"
