# -*- coding: utf-8 -*-
"""Choose a per-article tightening level.

Every article begins on a fresh page, so articles paginate independently of one
another.  That lets the build measure *all* articles at each tightening level in
a single pagination pass, then keep, for each article, the lightest level that
actually reduces its page count.  A greedy "tighten until the last page looks
full" loop can overshoot and leave an emptier page than it started with.

  autofit.py set    <key> <level>   write the trial tighten file
  autofit.py record <key> <level>   append this level's measurements
  autofit.py choose <key>           write the final tighten file
"""
import json, os, sys
from issues import resolve

BASE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(BASE, 'build')
LEVELS = ['none', 't1', 't2', 't3']

cmd, key = sys.argv[1], sys.argv[2]
DATA = resolve(key).get('data', key)
tight_p = os.path.join(B, f'tighten-{key}.json')
stats_p = os.path.join(B, f'fitstats-{key}.json')
slugs = [a['slug'] for a in json.load(
    open(os.path.join(BASE, 'data', DATA, 'issue.json')))]

if cmd == 'set':
    lv = sys.argv[3]
    json.dump({} if lv == 'none' else {s: lv for s in slugs},
              open(tight_p, 'w'))

elif cmd == 'record':
    lv = sys.argv[3]
    pm = json.load(open(os.path.join(B, f'pagemap-{key}.json')))
    stats = json.load(open(stats_p)) if os.path.exists(stats_p) else {}
    for s in slugs:
        start, end = pm['start'].get(s), pm['end'].get(s)
        if start is None:
            continue
        stats.setdefault(s, {})[lv] = {
            'pages': end - start + 1,
            'fill': pm['fill'].get(str(end), 1.0),
        }
    json.dump(stats, open(stats_p, 'w'))

elif cmd == 'choose':
    stats = json.load(open(stats_p))
    chosen, notes = {}, []
    for s in slugs:
        st = stats.get(s, {})
        if not st:
            continue
        have = [lv for lv in LEVELS if lv in st]
        fewest = min(st[lv]['pages'] for lv in have)
        # never spend an extra page; among the levels that use the fewest,
        # take the one that leaves the fullest last page
        cands = [lv for lv in have if st[lv]['pages'] == fewest]
        best = max(cands, key=lambda lv: st[lv]['fill'])
        base = st.get('none', {})
        # leaving it alone is preferable unless tightening clearly helps
        if ('none' in cands
                and st['none']['fill'] >= st[best]['fill'] - 0.05):
            best = 'none'
        if best != 'none':
            chosen[s] = best
            notes.append(
                f"    {s}: {base.get('pages','?')}pp/"
                f"{int(base.get('fill', 0) * 100)}% -> {st[best]['pages']}pp/"
                f"{int(st[best]['fill'] * 100)}%  [{best}]")
        elif base:
            notes.append(f"    {s}: {base['pages']}pp, last page "
                         f"{int(base['fill'] * 100)}% full  [no change]")
    json.dump(chosen, open(tight_p, 'w'))
    print('\n'.join(notes))
