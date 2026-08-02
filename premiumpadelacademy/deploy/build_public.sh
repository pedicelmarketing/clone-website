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
KEEP_DEMO=0
NOINDEX=1          # default on: the site is live before the client has approved it
for arg in "$@"; do
  case "$arg" in
    --keep-reviews) KEEP_REVIEWS=1 ;;
    --keep-slots)   KEEP_SLOTS=1 ;;
    --keep-demo)    KEEP_DEMO=1; KEEP_REVIEWS=1 ;;   # ship the example reviews as-is
    --allow-index)  NOINDEX=0 ;;                     # launch: let search engines in
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

[ -f "$SRC/index.html" ] || { echo "FATAL: $SRC/index.html missing"; exit 1; }

echo "==> staging $SRC -> $OUT"
rm -rf "$OUT"
cp -a "$SRC" "$OUT"

if [ "$KEEP_DEMO" -eq 1 ]; then
  echo "==> KEEPING the example reviews (--keep-demo), at the client's direction"
else
  echo "==> reverting fabricated demo reviews"
  python3 "$PD/tools/strip_demo_reviews.py" "$(basename "$OUT")"

  if [ "$KEEP_REVIEWS" -eq 0 ]; then
    echo "==> removing the now-empty reviews section"
    python3 "$PD/tools/hide_empty_reviews.py" --root "$(basename "$OUT")"
  fi
fi

if [ "$NOINDEX" -eq 1 ]; then
  echo "==> marking as an unapproved draft (noindex)"
  python3 "$PD/tools/draft_noindex.py" --root "$(basename "$OUT")" --on
else
  echo "==> LAUNCH build — search engines allowed"
  python3 "$PD/tools/draft_noindex.py" --root "$(basename "$OUT")" --off
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
if [ "$KEEP_DEMO" -eq 1 ]; then
  n_demo="$(count 'data-demo="true"')"
  echo "  SKIPPED: example reviews retained on purpose ($n_demo block(s))."
  echo "           They are invented, not real customer reviews. Publishing"
  echo "           invented reviews as genuine is prohibited under EU/ES"
  echo "           consumer law once the site is presented as live and approved."
  echo "           Held back from search engines by the noindex gate below."
  [ "$NOINDEX" -eq 1 ] || { echo "  FAIL: --keep-demo with --allow-index is not permitted"; fail=1; }
else
  python3 "$PD/tools/strip_demo_reviews.py" --check "$(basename "$OUT")"
  require_absent 'data-demo="true"'
fi

# Gate 2 - no placeholder content of any kind reached the public build.
{ [ "$KEEP_REVIEWS" -eq 1 ] || [ "$KEEP_DEMO" -eq 1 ]; } || require_absent 'Pendiente'
if [ "$KEEP_SLOTS" -eq 0 ]; then
  require_absent 'data-placeholder="true"'
  require_absent 'Espacio disponible'
fi

# Gate 3 - none of what the client asked to have removed.
for pattern in 'rikicoach' '600 000 000' 'WIX Harmony' 'tenis' 'tennis'; do
  require_absent "$pattern"
done

# ...and exactly one contact address, present on every page. Asserting the count
# rather than a literal address means the gate survives a change of address, but
# still catches a half-finished swap where the visible text and the mailto:
# disagree, or a page that lost its footer address entirely.
mapfile -t addrs < <(grep -rhoE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' \
                       "$OUT" --include='*.html' --include='*.js' | sort -uf)
if [ "${#addrs[@]}" -ne 1 ]; then
  echo "  FAIL: expected one contact address, found ${#addrs[@]}: ${addrs[*]}"
  fail=1
else
  pages_with="$(grep -rlF "${addrs[0]}" "$OUT" --include='*.html' | wc -l)"
  n_html="$(find "$OUT" -maxdepth 1 -name '*.html' | wc -l)"
  if [ "$pages_with" -eq "$n_html" ]; then
    echo "  ok: ${addrs[0]} on all $n_html page(s)"
  else
    echo "  FAIL: ${addrs[0]} on only $pages_with/$n_html page(s)"; fail=1
  fi
fi

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

# Gate 5 - the draft/launch indexing state is what was actually asked for.
n_noindex="$(count 'name="robots"')"
n_pages="$(find "$OUT" -maxdepth 1 -name '*.html' | wc -l)"
if [ "$NOINDEX" -eq 1 ]; then
  [ "$n_noindex" -eq "$n_pages" ] \
    && echo "  ok: noindex on all $n_pages page(s) (unapproved draft)" \
    || { echo "  FAIL: noindex on $n_noindex/$n_pages page(s)"; fail=1; }
else
  [ "$n_noindex" -eq 0 ] \
    && echo "  ok: no noindex — indexable launch build" \
    || { echo "  FAIL: $n_noindex page(s) still carry noindex"; fail=1; }
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "BUILD FAILED - not fit to publish."
  exit 1
fi
echo "==> build ok"
echo "    files: $(find "$OUT" -type f | wc -l)   size: $(du -sh "$OUT" | cut -f1)"
echo "    next:  bash deploy/publish.sh"
