#!/bin/bash
# Build one issue end to end:  ./build.sh 2026-08
set -e
cd "$(dirname "$0")"
KEY="${1:-2026-07}"
# Chrome is required for pagination and printing. Honour $CHROME, else look
# in the usual places on macOS and Linux (CI runners have it on PATH).
if [ -z "$CHROME" ]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "/Applications/Chromium.app/Contents/MacOS/Chromium" \
           google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then CHROME="$c"; break; fi
  done
fi
[ -n "$CHROME" ] || { echo "!! no Chrome/Chromium found; set \$CHROME"; exit 1; }
# use a local venv when there is one, otherwise whatever python is on PATH
if [ -x ./.venv/bin/python ]; then PY=./.venv/bin/python; else PY="$(command -v python3 || command -v python)"; fi
[ -n "$PY" ] || { echo "!! no python found"; exit 1; }
OUTNAME=$($PY -c "from issues import resolve; print(resolve('$KEY')['out'])")

# Headless Chrome sometimes tears down before Paged.js finishes, so each read
# is retried across a few virtual-time budgets until it yields a result.
grab () {
  local url="$1" marker="$2" out="$3"
  for b in 120000 300000 600000 200000 400000; do
    "$CHROME" --headless=new --disable-gpu --no-sandbox \
      --allow-file-access-from-files --virtual-time-budget=$b \
      --dump-dom "$url" 2>/dev/null > /tmp/_grab.html || true
    if grep -q "$marker" /tmp/_grab.html; then cp /tmp/_grab.html "$out"; return 0; fi
  done
  echo "!! never saw $marker"; return 1
}

paginate () {
  $PY gen.py "$KEY" "$@" >/dev/null
  grab "file://$PWD/build/issue-$KEY.html" 'PAGEMAP{' /tmp/pg.html
  grep -o 'PAGEMAP{.*}' /tmp/pg.html | head -1 | sed 's/^PAGEMAP//' > "build/pagemap-$KEY.json"
  test -s "build/pagemap-$KEY.json"
}

echo "── $KEY: auto-fit — measuring each tightening level"
rm -f "build/fitstats-$KEY.json"
for LV in none t1 t2 t3; do
  $PY autofit.py set "$KEY" "$LV"
  paginate
  $PY autofit.py record "$KEY" "$LV"
done
$PY autofit.py choose "$KEY"

echo "── contents page numbers + PDF"
paginate --with-toc
$PY gen.py "$KEY" --with-toc >/dev/null
# expected length, so a print that raced the paginator can be detected
WANT=$(KEY="$KEY" $PY -c "
import json, os
pm = json.load(open('build/pagemap-%s.json' % os.environ['KEY']))
print(max(pm['end'].values()))")

printed=0
for b in 120000 300000 60000 600000; do
  "$CHROME" --headless=new --disable-gpu --no-sandbox --allow-file-access-from-files \
    --virtual-time-budget=$b --no-pdf-header-footer \
    --print-to-pdf="build/$OUTNAME.pdf" "file://$PWD/build/issue-$KEY.html" 2>/dev/null || true
  got=$($PY -c "
from pypdf import PdfReader
try: print(len(PdfReader('build/$OUTNAME.pdf').pages))
except Exception: print(0)")
  if [ "$got" -ge "$WANT" ]; then printed=1; echo "   printed $got pages"; break; fi
  echo "   retry: got $got, expected $WANT"
done
[ "$printed" = 1 ] || { echo "!! could not print a complete PDF"; exit 1; }

echo "── editable layout + .pptx"
# The PDF and the web edition are the outputs that matter. If the layout
# extraction misbehaves, warn and carry on rather than losing the whole build.
if ! grab "file://$PWD/build/issue-$KEY.html#extract" 'LAYOUT\[' /tmp/ex.html; then
  echo "!! could not extract the editable layout — skipping the Canva file."
  echo "   The PDF is fine. Re-run if you need the .pptx."
  SKIP_PPTX=1
fi
if [ -z "$SKIP_PPTX" ]; then
KEY="$KEY" $PY -c "
import re, html, json, os
key = os.environ['KEY']
s = open('/tmp/ex.html', encoding='utf-8').read()
d = json.loads(html.unescape(re.search(r'>LAYOUT(\[.*?\])</pre>', s, re.S).group(1)))
json.dump(d, open(f'build/layout-{key}.json', 'w'), ensure_ascii=False)
"
KEY="$KEY" $PY -c "
import json, os
key = os.environ['KEY']
d = json.load(open(f'build/layout-{key}.json'))
bad = [(p['page'], p['missing']) for p in d if p.get('missing')]
if bad:
    print('   !! text on the page that no shape captured:')
    for pg, ws in bad:
        print(f'      p{pg}: {ws}')
else:
    print('   every word on every page was captured')
"
$PY topptx.py "$KEY"
fi
KEY="$KEY" $PY -c "
from pypdf import PdfReader
import json, os
key = os.environ['KEY']
n = len(PdfReader(f'build/$OUTNAME.pdf').pages)
pm = json.load(open(f'build/pagemap-{key}.json'))
print('PDF pages:', n)
print('last-page fill:', {s: round(pm['fill'][str(e)], 2) for s, e in pm['end'].items()})
"
