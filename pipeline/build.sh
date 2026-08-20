#!/bin/bash
# Build one issue end to end:  ./build.sh 2026-08
set -e
cd "$(dirname "$0")"
KEY="${1:-2026-07}"

# use a local venv when there is one, otherwise whatever python is on PATH
if [ -x ./.venv/bin/python ]; then PY=./.venv/bin/python; else PY="$(command -v python3 || command -v python)"; fi
[ -n "$PY" ] || { echo "!! no python found"; exit 1; }
OUTNAME=$($PY -c "from issues import resolve; print(resolve('$KEY')['out'])")

# Pagination and printing go through Playwright (see render.py): it waits for
# the page to actually finish rather than guessing with a time budget.
paginate () {
  $PY gen.py "$KEY" "$@" >/dev/null
  $PY render.py dom "file://$PWD/build/issue-$KEY.html" > /tmp/pg.html
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
$PY render.py pdf "file://$PWD/build/issue-$KEY.html" "build/$OUTNAME.pdf"
GOT=$($PY -c "
from pypdf import PdfReader
print(len(PdfReader('build/$OUTNAME.pdf').pages))")
WANT=$(KEY="$KEY" $PY -c "
import json, os
pm = json.load(open('build/pagemap-%s.json' % os.environ['KEY']))
print(max(pm['end'].values()))")
[ "$GOT" -ge "$WANT" ] || { echo "!! printed $GOT pages, expected $WANT"; exit 1; }
echo "   printed $GOT pages"

echo "── editable layout + .pptx"
# The PDF and the web edition are the outputs that matter. If the layout
# extraction misbehaves, warn and carry on rather than losing the whole build.
if ! $PY render.py dom "file://$PWD/build/issue-$KEY.html#extract" > /tmp/ex.html \
     || ! grep -q 'LAYOUT\[' /tmp/ex.html; then
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
