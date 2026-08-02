#!/usr/bin/env bash
# Produce the publishable build of the padel site from site-v2/.
#
# site-v2/ is the WORKING build: it carries fabricated demo reviews and empty
# partner-logo slots so the design can be evaluated. Neither belongs on a public
# site, so this script derives a separate build/ tree with them removed, and
# refuses to finish if any survived.
#
#   site-v2/  --(copy)-->  build/  --(strip demo)--> --(drop empty slots)--> gates
#
# Idempotent: safe to re-run. Nonzero exit on any gate failure, so publish.sh
# can never run on a build that still contains demo content.
#
# Flags:
#   --keep-reviews   leave the reviews section in place as empty "Pendiente"
#                    slots instead of removing the section entirely
#   --keep-slots     keep the empty partner-logo placeholders
set -euo pipefail

PD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$PD/site-v2"
OUT="$PD/build"

KEEP_REVIEWS=0
KEEP_SLOTS=0
for arg in "$@"; do
  case "$arg" in
    --keep-reviews) KEEP_REVIEWS=1 ;;
    --keep-slots)   KEEP_SLOTS=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

[ -f "$SRC/index.html" ] || { echo "FATAL: $SRC/index.html missing"; exit 1; }

echo "==> staging $SRC -> $OUT"
rm -rf "$OUT"
cp -a "$SRC" "$OUT"

echo "==> reverting fabricated demo reviews"
python3 "$PD/tools/strip_demo_reviews.py" "$(basename "$OUT")"

if [ "$KEEP_REVIEWS" -eq 0 ]; then
  echo "==> removing the now-empty reviews section"
  python3 "$PD/tools/hide_empty_reviews.py" --root "$(basename "$OUT")"
fi

echo "==> rendering partner band"
if [ "$KEEP_SLOTS" -eq 1 ]; then
  python3 "$PD/tools/partner_logos.py" --root "$(basename "$OUT")" --render
else
  python3 "$PD/tools/partner_logos.py" --root "$(basename "$OUT")" --render --no-placeholders
fi

echo
echo "==> gates"

# grep exits 1 when a pattern is absent, which under `set -o pipefail` would abort
# the script on exactly the outcome we want. Absent means zero, not failure.
count() { { grep -rFi "$1" "$OUT" --include='*.html' -c 2>/dev/null || true; } \
            | awk -F: '{s+=$2} END{print s+0}'; }

fail=0
require_absent() {
  local n; n="$(count "$1")"
  if [ "$n" -gt 0 ]; then echo "  FAIL: '$1' present ($n)"; fail=1
  else echo "  ok: no '$1'"; fi
}

# Gate 1 - no fabricated review content survived.
python3 "$PD/tools/strip_demo_reviews.py" --check "$(basename "$OUT")"

# Gate 2 - no placeholder content of any kind reached the public build.
require_absent 'data-demo="true"'
[ "$KEEP_REVIEWS" -eq 1 ] || require_absent 'Pendiente'
if [ "$KEEP_SLOTS" -eq 0 ]; then
  require_absent 'data-placeholder="true"'
  require_absent 'Espacio disponible'
fi

# Gate 3 - none of what the client asked to have removed.
for pattern in 'rikicoach' '600 000 000' 'WIX Harmony' 'tenis' 'tennis'; do
  require_absent "$pattern"
done

# ...and the contact address he asked for, on every page.
n="$(count 'Infopremiumpadelacademy@gmail.com')"
if [ "$n" -ge 4 ]; then echo "  ok: contact email present ($n refs)"
else echo "  FAIL: contact email only $n refs"; fail=1; fi

# Gate 4 - every local asset the markup references exists on disk.
if python3 - "$OUT" <<'PY'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
bad = 0
for page in sorted(root.glob("*.html")):
    html = page.read_text(encoding="utf-8")
    for ref in re.findall(r'(?:src|href)="((?!https?:|mailto:|tel:|#)[^"]+)"', html):
        target = root / ref.split("?")[0].split("#")[0]
        if not target.exists():
            print(f"  FAIL: {page.name} -> {ref} (missing)")
            bad += 1
sys.exit(1 if bad else 0)
PY
then echo "  ok: all local asset references resolve"
else fail=1; fi

echo
if [ "$fail" -ne 0 ]; then
  echo "BUILD FAILED - not fit to publish."
  exit 1
fi
echo "==> build ok"
echo "    files: $(find "$OUT" -type f | wc -l)   size: $(du -sh "$OUT" | cut -f1)"
echo "    next:  bash deploy/publish.sh"
