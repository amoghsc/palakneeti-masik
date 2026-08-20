# -*- coding: utf-8 -*-
"""Record one built issue in the published site and regenerate the index.

Each build drops its files into docs/<key>/ and leaves a meta.json behind, so
the site accumulates months instead of replacing them and the index can be
rebuilt from what is actually on disk.

    mksite.py <issue-key> <repo-root>
"""
import html, json, os, sys, datetime
from issues import resolve

KEY = sys.argv[1]
ROOT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else '..')
PIPE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, 'docs')
esc = lambda t: html.escape(str(t), quote=False)


def record():
    cfg = resolve(KEY)
    dest = os.path.join(DOCS, KEY)
    os.makedirs(dest, exist_ok=True)
    arts = json.load(open(os.path.join(PIPE, 'data', cfg.get('data', KEY),
                                       'issue.json')))
    meta = {
        'key': KEY,
        'month_mr': cfg['month_mr'],
        'month_en': cfg['month_en'],
        'articles': len(arts),
        'titles': [a['title'] for a in arts],
        'built': datetime.date.today().isoformat(),
        'pdf': f'{cfg["out"]}.pdf' if os.path.exists(
            os.path.join(dest, f'{cfg["out"]}.pdf')) else None,
    }
    json.dump(meta, open(os.path.join(dest, 'meta.json'), 'w'),
              ensure_ascii=False, indent=1)
    return meta


def all_issues():
    out = []
    if not os.path.isdir(DOCS):
        return out
    for name in sorted(os.listdir(DOCS), reverse=True):
        m = os.path.join(DOCS, name, 'meta.json')
        if os.path.exists(m):
            out.append(json.load(open(m)))
    return out


INDEX_CSS = """
:root{--paper:#F6F8F4;--surface:#EDF1EA;--ink:#16211D;--soft:#56685F;
 --faint:#7C8C84;--moss:#1F5A4C;--clay:#BC5D2C;--rule:#DBE3DA;
 --serif:'Tiro Devanagari Marathi','Noto Serif Devanagari',Georgia,serif;
 --sans:'Mukta','Noto Sans Devanagari',system-ui,sans-serif;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#101613;--surface:#18211D;--ink:#E6EBE4;--soft:#9DACA3;
 --faint:#7E8D85;--moss:#7CC4AB;--clay:#E4885C;--rule:#25322C;}}
:root[data-theme="dark"]{--paper:#101613;--surface:#18211D;--ink:#E6EBE4;
 --soft:#9DACA3;--faint:#7E8D85;--moss:#7CC4AB;--clay:#E4885C;--rule:#25322C;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
 font-size:17px;line-height:1.7;-webkit-text-size-adjust:100%}
main{max-width:34rem;margin:0 auto;padding:3rem 1.15rem 4rem}
h1{font-family:var(--serif);font-weight:400;font-size:clamp(2.4rem,11vw,3.2rem);
 margin:0;color:var(--moss);line-height:1.05;text-align:center}
.tag{margin:.8rem 0 2.6rem;text-align:center;color:var(--faint);font-size:.9rem;
 letter-spacing:.15em;text-transform:uppercase}
.issue{border-top:1px solid var(--rule);padding:1.3rem 0}
.issue:last-of-type{border-bottom:1px solid var(--rule)}
.issue h2{font-family:var(--serif);font-weight:400;font-size:1.5rem;margin:0;
 color:var(--ink)}
.issue .meta{color:var(--faint);font-size:.87rem;margin:.2rem 0 .8rem}
.issue .links{display:flex;gap:.6rem;flex-wrap:wrap}
.issue a{display:inline-block;text-decoration:none;font-size:.9rem;
 font-weight:600;padding:.42rem .9rem;border-radius:999px}
.read{background:var(--moss);color:var(--paper)}
.pdf{border:1px solid var(--rule);color:var(--soft)}
.titles{margin:.7rem 0 0;padding-left:1.1rem;color:var(--soft);font-size:.88rem}
.titles li{margin:.15rem 0}
footer{margin-top:3rem;text-align:center;color:var(--faint);font-size:.85rem}
footer a{color:var(--moss)}
.empty{color:var(--soft);text-align:center;padding:2rem 0}
"""


def index(issues):
    rows = []
    for m in issues:
        pdf = (f'<a class="pdf" href="{esc(m["key"])}/{esc(m["pdf"])}">PDF</a>'
               if m.get('pdf') else '')
        titles = ''.join(f'<li>{esc(t)}</li>' for t in m.get('titles', [])[:8])
        rows.append(f'''<section class="issue">
  <h2>{esc(m['month_mr'])}</h2>
  <p class="meta">{esc(m['articles'])} लेख · {esc(m['month_en'])}</p>
  <div class="links">
    <a class="read" href="{esc(m['key'])}/">वाचा</a>{pdf}
  </div>
  <ul class="titles">{titles}</ul>
</section>''')
    body = '\n'.join(rows) or '<p class="empty">अजून एकही अंक तयार झालेला नाही.</p>'
    return f'''<!doctype html>
<html lang="mr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>पालकनीती मासिक</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;600;700&family=Tiro+Devanagari+Marathi&display=swap">
<style>{INDEX_CSS}</style></head>
<body><main>
  <h1>पालकनीती</h1>
  <p class="tag">मासिक अंक</p>
  {body}
  <footer><p>सर्व लेख <a href="https://palakneeti.in">palakneeti.in</a> वर प्रसिद्ध झाले आहेत.</p></footer>
</main></body></html>
'''


if __name__ == '__main__':
    m = record()
    issues = all_issues()
    os.makedirs(DOCS, exist_ok=True)
    open(os.path.join(DOCS, 'index.html'), 'w', encoding='utf-8').write(index(issues))
    print(f'recorded {KEY}: {m["articles"]} articles; '
          f'index now lists {len(issues)} issue(s)')
