# -*- coding: utf-8 -*-
"""Lay one issue out as an A4 HTML document.  usage: gen.py <issue-key> [--with-toc]"""
import json, os, sys, html
from string import Template
from issues import resolve, PALETTES, MASTHEAD, SITE

BASE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(BASE, 'build')
KEY = sys.argv[1] if len(sys.argv) > 1 else '2026-07'
CFG = resolve(KEY)
STYLE = CFG['style']
C = PALETTES[STYLE]
DATA = CFG.get('data', KEY)
IMG = f'images/{DATA}'

DEV = '०१२३४५६७८९'
dev = lambda n: ''.join(DEV[int(c)] for c in str(n))
esc = lambda t: html.escape(t, quote=False)


def runs_html(runs):
    out = []
    for r in runs:
        t = esc(r['t']).replace('\n', '<br>')
        if r.get('b'): t = f'<strong>{t}</strong>'
        if r.get('i'): t = f'<em>{t}</em>'
        if r.get('href'): t = f'<a href="{html.escape(r["href"])}">{t}</a>'
        out.append(t)
    return ''.join(out)


PEN = '<img class="pen" src="assets/pen.png" alt="">'

# ── shared CSS ──────────────────────────────────────────────────────────
BASE_CSS = Template('''
@font-face { font-family:'Mukta'; src:url('fonts/Mukta-Regular.ttf');  font-weight:400; }
@font-face { font-family:'Mukta'; src:url('fonts/Mukta-Medium.ttf');   font-weight:500; }
@font-face { font-family:'Mukta'; src:url('fonts/Mukta-SemiBold.ttf'); font-weight:600; }
@font-face { font-family:'Mukta'; src:url('fonts/Mukta-Bold.ttf');     font-weight:700; }
@font-face { font-family:'Mukta'; src:url('fonts/Mukta-ExtraBold.ttf');font-weight:800; }

@page { size: A4; margin: 16mm 19mm 19mm 19mm; }
@page cover { margin: 0; }

* { box-sizing: border-box; }
html { font-family:'Mukta', sans-serif; }
body { margin:0; color:$ink; font-size:12.1pt; line-height:1.74;
       text-align:left; hyphens:none; }
/* Paged.js forces text-align-last:justify, which stretches final lines */
.pagedjs_page_content, .pagedjs_page_content * { text-align-last:auto !important; }
a { color:$teal; text-decoration:none; word-break:break-all; }

.pagedjs_page { position:relative; }
.pagedjs_margin-bottom-left, .pagedjs_margin-bottom-right { display:none; }

.cover { page:cover; break-after:page; height:297mm; width:210mm; background:#fff;
         position:relative; overflow:hidden; }

.art p { margin:0 0 3.0mm; orphans:2; widows:2; }
.art h2, .art h3 { font-size:13pt; color:$teal_d; font-weight:700;
                   margin:4mm 0 2mm; text-align:left; }
.art ul, .art ol { margin:0 0 3mm; padding-left:6mm; }
.art li { margin-bottom:1.6mm; }

figure.ph { margin:0 0 3mm; }
figure.ph.right { float:right; width:44%; margin:1mm 0 3mm 5mm; }
figure.ph.left  { float:left;  width:44%; margin:1mm 5mm 3mm 0; }
figure.ph.full  { float:none;  width:100%; margin:3mm 0; }
figure.ph img { width:100%; display:block; }
figure.ph figcaption { font-size:9pt; color:$grey; text-align:center;
                       margin-top:1.2mm; line-height:1.35; }

.sign { text-align:right; font-weight:700; color:$teal_d; }
.credit-line { margin-top:3mm; font-size:10pt; color:$grey; }
.appendix { break-inside:avoid; }

.credits { break-after:page; display:flex; gap:9mm; min-height:245mm; }
.credits .col { flex:1; }
.credits h4 { font-size:12.4pt; color:$teal_d; font-weight:700; margin:0 0 1.5mm; }
.credits .grp { margin-bottom:6.2mm; }
.credits .grp p { margin:0; font-size:11pt; line-height:1.5; }
.credits .side { width:34mm; background:$peach; border-radius:2mm;
                 display:flex; flex-direction:column; align-items:center;
                 padding:7mm 0; }
.credits .side img { width:22mm; }
.credits .side .logo-cap { font-size:8.6pt; font-weight:700; color:$teal_d; margin-top:1mm; }
.credits .side .url { writing-mode:vertical-rl; transform:rotate(180deg);
                      font-size:20pt; font-weight:700; color:$teal_d;
                      letter-spacing:.4pt; margin-top:14mm; }

.toc { break-after:page; position:relative; }
.toc ol { list-style:none; margin:0; padding:0; }

/* text cover */
.cover.text { background:$teal; display:flex; flex-direction:column;
              justify-content:center; align-items:center; }
.cover.text .badge { width:34mm; height:34mm; border-radius:50%; background:#fff;
                     display:flex; align-items:center; justify-content:center;
                     margin-bottom:14mm; }
.cover.text .badge img { width:22mm; }
.cover.text h1 { color:#fff; font-size:58pt; font-weight:800; margin:0;
                 letter-spacing:-1pt; line-height:1; }
.cover.text .crule { width:38mm; height:3mm; background:$orange; margin:8mm 0; }
.cover.text h2 { color:$peach; font-size:20pt; font-weight:500; margin:0;
                 letter-spacing:3pt; }
.cover.text .foot { position:absolute; bottom:18mm; color:$peach; opacity:.75;
                    font-size:11pt; letter-spacing:1.5pt; }

/* auto-fit levels, applied by the build when an article leaves a sparse page */
.art.t1 { line-height:1.66; }
.art.t1 p { margin-bottom:2.5mm; }
.art.t2 { line-height:1.58; font-size:11.6pt; }
.art.t2 p { margin-bottom:2.2mm; }
.art.t3 { line-height:1.52; font-size:11.2pt; }
.art.t3 p { margin-bottom:2mm; }
''')

# ── style: classic (as printed in May / used for July) ──────────────────
CLASSIC_CSS = Template('''
.pagedjs_page::after { content:''; position:absolute; left:19mm; right:19mm;
  bottom:11mm; height:2.6pt; background:$teal; border-radius:2pt; }
.folio { position:absolute; right:19mm; bottom:7.2mm; z-index:5;
  width:8.4mm; height:8.4mm; border-radius:50%; background:$orange; color:#fff;
  font-weight:700; font-size:10pt; display:flex; align-items:center;
  justify-content:center; line-height:1; }
.folio-tab { position:absolute; left:19mm; bottom:11mm; z-index:5;
  width:26mm; height:2.6pt; background:$orange; border-radius:2pt; }
.runfoot { display:none; }

.credits { flex-direction:row; }
.toc .leaf  { position:absolute; top:-19mm; right:-10mm; width:36mm; opacity:.95; }
.toc .leaf2 { position:absolute; bottom:6mm; left:-8mm; width:26mm; opacity:.9;
              transform:rotate(150deg); }
.toc h2 { font-size:27pt; color:$teal; font-weight:800; margin:26mm 0 8mm; }
.toc li { display:flex; gap:5mm; align-items:baseline; padding:3.4mm 0;
          border-top:.6pt solid #CBD8D5; }
.toc li:last-child { border-bottom:.6pt solid #CBD8D5; }
.toc .no { color:$orange; font-weight:700; font-size:13pt; width:7mm; flex:none; }
.toc .t { flex:1; }
.toc .t b { display:block; font-size:14.2pt; color:$teal; font-weight:700; line-height:1.3; }
.toc .t .toc-by { display:block; font-size:10pt; color:$grey; }
.toc .pg { color:$teal; font-weight:700; font-size:12pt; flex:none; }
.toc .foot { margin-top:12mm; text-align:center; }
.toc .foot p { margin:0 0 2mm; font-size:11.4pt; }
.toc .foot .site { margin:0; }
.toc .foot a { font-size:19pt; font-weight:800; color:$teal; text-decoration:underline; }

.art { break-before:page; }
.art .kicker { text-align:center; color:$orange; font-weight:700; font-size:10.4pt;
               letter-spacing:.8pt; margin:0 0 1.5mm; }
.art h1 { text-align:center; color:$teal; font-weight:800; font-size:27pt;
          line-height:1.22; margin:0 0 3mm; }
.art .by { display:flex; align-items:center; justify-content:center; gap:2.5mm;
           margin:0 0 6mm; }
.art .by .pen { width:7mm; flex:none; }
.art .by .names p { margin:0; font-size:11pt; font-weight:600; }
.art .by .names p + p { font-weight:400; font-size:10.2pt; color:$grey; }
.art .lead { background:$mint; border-radius:2mm; padding:4mm 5mm; margin:0 0 4mm; }
.art .lead p:last-child { margin-bottom:0; }
figure.ph img { border-radius:2mm; }
blockquote { background:$peach; border-left:3pt solid $orange;
             border-radius:0 2mm 2mm 0; padding:4mm 5mm; margin:4mm 0; }
blockquote p { margin:0 0 2.2mm; }
blockquote p:last-child { margin-bottom:0; }
.tail { break-inside:avoid; background:$mint; border-radius:2mm; padding:4mm 5mm;
        margin:6mm 0 0; display:flex; gap:4mm; align-items:flex-start; }
.tail img { width:24mm; height:24mm; object-fit:cover; border-radius:1.5mm;
            border:1.6pt solid $teal; flex:none; }
.tail .who b { display:block; font-size:12pt; color:$teal_d; }
.tail .who .role { font-size:9.6pt; color:$grey; }
.tail .who .mail { font-size:10pt; color:$teal; margin-bottom:1.2mm; }
.tail .who .bio { font-size:9.8pt; line-height:1.5; margin:0; }
.art.t1 .tail { margin-top:4.5mm; padding:3.4mm 4.2mm; }
.art.t2 .tail { margin-top:3.5mm; padding:3mm 4mm; }
.art.t2 .tail img { width:21mm; height:21mm; }
.art.t3 .tail { margin-top:3mm; padding:2.8mm 3.6mm; }
.art.t3 .tail img { width:20mm; height:20mm; }
''')

# ── style: editorial (August) ───────────────────────────────────────────
EDITORIAL_CSS = Template('''
.pagedjs_page::after { content:''; position:absolute; left:19mm; right:19mm;
  bottom:12.4mm; height:.7pt; background:#C8D2CC; }
.folio { position:absolute; right:19mm; bottom:7.6mm; z-index:5;
  color:$orange; font-weight:800; font-size:12pt; line-height:1; }
.folio-tab { display:none; }
.runfoot { position:absolute; left:19mm; bottom:7.9mm; z-index:5;
  font-size:8.6pt; letter-spacing:.5pt; color:$grey; text-transform:none; }

/* masthead: tinted column on the left instead of the right */
.credits { flex-direction:row-reverse; }
.credits .side { background:$peach; border-radius:0; width:38mm; }
.credits .side .url { color:$teal_d; font-size:18pt; }

.toc .leaf  { position:absolute; top:-14mm; right:-12mm; width:30mm; opacity:.5; }
.toc .leaf2 { display:none; }
.toc h2 { font-size:30pt; color:$teal; font-weight:800; margin:22mm 0 2mm;
          letter-spacing:-.3pt; }
.toc .rule { width:22mm; height:2.4mm; background:$orange; margin:0 0 9mm; }
.toc li { display:flex; gap:6mm; align-items:flex-start; padding:0 0 7mm; }
.toc .no { color:$orange; font-weight:800; font-size:22pt; width:11mm;
           flex:none; line-height:1; opacity:.85; }
.toc .t { flex:1; padding-right:5mm; }
.toc .t b { display:block; font-size:15pt; color:$teal_d; font-weight:700;
            line-height:1.28; }
.toc .t .toc-by { display:block; font-size:10pt; color:$grey; }
.toc .pg { color:$orange; font-weight:700; font-size:12pt; flex:none;
           padding-top:2mm; min-width:8mm; text-align:right; }
.toc .foot { margin-top:6mm; padding-top:5mm; border-top:.7pt solid #C8D2CC; }
.toc .foot p { margin:0 0 1.5mm; font-size:10.6pt; color:$grey; }
.toc .foot .site { margin:0; }
.toc .foot a { font-size:16pt; font-weight:800; color:$teal; }

.art { break-before:page; }
.art .bar { background:$teal; color:#fff; font-weight:700; font-size:9.6pt;
            letter-spacing:1.1pt; padding:1.5mm 4mm; display:inline-block;
            margin:0 0 3.5mm; }
.art .rule-top { height:2.6mm; background:$orange; width:26mm; margin:0 0 4mm; }
.art h1 { text-align:left; color:$teal_d; font-weight:800; font-size:25pt;
          line-height:1.2; margin:0 0 3.5mm; letter-spacing:-.2pt; }
.art .by { display:flex; align-items:center; gap:2.5mm; margin:0 0 6mm;
           padding-bottom:3mm; border-bottom:.7pt solid #C8D2CC; }
.art .by .pen { width:6mm; flex:none; }
.art .by .names p { margin:0; font-size:11pt; font-weight:600; color:$teal_d; }
.art .by .names p + p { font-weight:400; font-size:10.2pt; color:$grey; }
/* an accent lead-in replaces the tinted intro panel */
.lead-in { color:$orange; font-weight:800; }
figure.ph img { border-radius:0; }
figure.ph { position:relative; }
figure.ph.right { border-left:2.2mm solid $peach; padding-left:3mm; }
figure.ph.left  { border-right:2.2mm solid $peach; padding-right:3mm; }
blockquote { background:$peach; padding:5mm 6mm; margin:4.5mm 0; border:none;
             position:relative; }
blockquote p { margin:0 0 2.2mm; font-size:11.6pt; }
blockquote p:last-child { margin-bottom:0; }
.tail { break-inside:avoid; background:#fff; border:.7pt solid #C8D2CC;
        border-left:2.6mm solid $orange; padding:4mm 5mm; margin:7mm 0 0;
        display:flex; gap:4.5mm; align-items:flex-start; }
.tail img { width:23mm; height:23mm; object-fit:cover; border-radius:50%; flex:none; }
.tail .who b { display:block; font-size:12pt; color:$teal_d; }
.tail .who .role { font-size:9.6pt; color:$grey; }
.tail .who .mail { font-size:10pt; color:$orange; margin-bottom:1.2mm; }
.tail .who .bio { font-size:9.8pt; line-height:1.5; margin:0; }
.art.t1 .tail { margin-top:5mm; padding:3.4mm 4.2mm; }
.art.t2 .tail { margin-top:4mm; padding:3mm 4mm; }
.art.t2 .tail img { width:20mm; height:20mm; }
.art.t3 .tail { margin-top:3.5mm; padding:2.8mm 3.6mm; }
.art.t3 .tail img { width:19mm; height:19mm; }

''')


TWOCOL_CSS = Template("""
/* a narrower measure wants smaller type and tighter leading */
body { font-size:10.6pt; line-height:1.62; }

.art { column-count:2; column-gap:8mm; }
/* the opener, intro panel and author card run across both columns */
.art .kicker, .art h1, .art .by, .art .lead,
.art .tail, .art .credit-line, .art .appendix { column-span:all; }
.art h1 { font-size:23pt; margin-bottom:2.5mm; }
.art .by { margin-bottom:5mm; }
.art .lead { margin-bottom:5mm; }
.art p { margin:0 0 2.4mm; }
.art h2, .art h3 { font-size:11.6pt; margin:3mm 0 1.6mm; }

/* in a narrow column a floated image is not worth the ragged wrap:
   images take the full column instead */
figure.ph.right, figure.ph.left, figure.ph.full {
  float:none; width:100%; margin:2mm 0 3.5mm; }
figure.ph figcaption { font-size:8.4pt; }

blockquote { padding:3.5mm 4mm; margin:3mm 0; }
blockquote p { margin:0 0 1.8mm; }
.tail { padding:3.5mm 4.5mm; margin-top:5mm; }
.tail .who .bio { font-size:9.4pt; }
.toc, .credits { column-count:1; }
""")


def css():
    s = BASE_CSS.substitute(**C)
    if STYLE == 'editorial':
        s += EDITORIAL_CSS.substitute(**C)
    else:
        s += CLASSIC_CSS.substitute(**C)          # twocol builds on classic
        if STYLE == 'twocol':
            s += TWOCOL_CSS.substitute(**C)
    return s


# ── page builders ───────────────────────────────────────────────────────
def cover():
    cv = CFG['cover']
    if cv['mode'] == 'blank':
        return '<section class="cover"></section>\n'
    return f'''<section class="cover text">
  <div class="badge"><img src="assets/p2_X7.png" alt=""></div>
  <h1>{esc(cv['title'])}</h1>
  <div class="crule"></div>
  <h2>{esc(cv['subtitle'])}</h2>
  <div class="foot">{SITE}</div>
</section>
'''


def credits():
    grps = ''.join(
        f'<div class="grp"><h4>{esc(h)}</h4>' +
        ''.join(f'<p>{esc(l)}</p>' for l in ls) + '</div>'
        for h, ls in MASTHEAD)
    return f'''<section class="credits">
  <div class="col">{grps}</div>
  <div class="side">
    <img src="assets/p2_X7.png" alt="">
    <div class="logo-cap">पालकनीती परिवार</div>
    <div class="url">{SITE}</div>
  </div>
</section>
'''


def toc(arts, pages):
    lis = []
    for i, a in enumerate(arts, 1):
        pg = pages.get(a['slug'])
        who = ' &nbsp;·&nbsp; '.join(esc(x) for x in a['byline'])
        lis.append(f'<li><span class="no">{dev(i)}</span>'
                   f'<span class="t"><b>{esc(a["title"])}</b>'
                   f'{f"<span class=\'toc-by\'>{who}</span>" if who else ""}</span>'
                   f'<span class="pg">{dev(pg) if pg else "&nbsp;"}</span></li>')
    rule = '<div class="rule"></div>' if STYLE == 'editorial' else ''
    leaf2 = '<img class="leaf2" src="assets/p3_X24.png" alt="">' if STYLE == 'classic' else ''
    return f'''<section class="toc">
  <img class="leaf" src="assets/p3_X24.png" alt="">{leaf2}
  <h2>या अंकात…</h2>{rule}
  <ol>{''.join(lis)}</ol>
  <div class="foot">
    <p>जुने लेख / अंक वाचण्यासाठी पालकनीतीच्या वेबसाईटला अवश्य भेट द्या</p>
    <p class="site"><a href="https://palakneeti.in">{SITE}</a></p>
  </div>
</section>
'''


def block_html(b, side):
    t = b['type']
    if t == 'para':
        txt = runs_html(b['runs'])
        p = ''.join(r['t'] for r in b['runs']).strip()
        cls = ' class="sign"' if p.startswith(('–', '-', '—')) and len(p) < 60 else ''
        return f'<p{cls}>{txt}</p>'
    if t == 'head':
        lv = 2 if b['level'] <= 3 else 3
        return f'<h{lv}>{runs_html(b["runs"])}</h{lv}>'
    if t == 'image':
        if not b.get('file'):        # nothing was downloaded for this one
            return ''
        cap = f'<figcaption>{esc(b["caption"])}</figcaption>' if b.get('caption') else ''
        return f'<figure class="ph {side}"><img src="{IMG}/{b["file"]}" alt="">{cap}</figure>'
    if t == 'quote':
        return '<blockquote>' + ''.join(f'<p>{runs_html(p)}</p>' for p in b['paras']) + '</blockquote>'
    if t == 'list':
        tag = 'ol' if b.get('ordered') else 'ul'
        return f'<{tag}>' + ''.join(f'<li>{runs_html(i)}</li>' for i in b['items']) + f'</{tag}>'
    return ''


def lead_in(runs, want=30):
    """Wrap the opening words in an accent span (safe for Devanagari, unlike
       a ::first-letter drop cap, which would strip combining marks)."""
    out, used, done = [], 0, False
    for r in runs:
        if done or used >= want:
            out.append(r); continue
        t = r['t']
        if used + len(t) <= want:
            out.append({**r, 'lead': True}); used += len(t); continue
        cut = t.find(' ', want - used)
        cut = len(t) if cut == -1 else cut
        out.append({**r, 't': t[:cut], 'lead': True})
        if t[cut:]:
            out.append({**r, 't': t[cut:]})
        done = True
    html_parts = []
    for r in out:
        seg = runs_html([r])
        html_parts.append(f'<span class="lead-in">{seg}</span>' if r.get('lead') else seg)
    return '<p>' + ''.join(html_parts) + '</p>'


def article(a, tight=None):
    cls = 'art' + (f' {tight}' if tight else '')
    p = [f'<section class="{cls}" id="art-{a["slug"]}" data-a="{a["slug"]}">']

    if STYLE == 'editorial':
        if a['kicker']:
            p.append(f'<div class="bar">{esc(a["kicker"])}</div>')
        else:
            p.append('<div class="rule-top"></div>')
    elif a['kicker']:
        p.append(f'<p class="kicker">{esc(a["kicker"])}</p>')

    p.append(f'<h1>{esc(a["title"])}</h1>')
    if a['byline']:
        names = ''.join(f'<p>{esc(x)}</p>' for x in a['byline'])
        p.append(f'<div class="by">{PEN}<div class="names">{names}</div></div>')

    sides, si, lead_done = ['right', 'left'], 0, False
    for i, b in enumerate(a['body']):
        if not lead_done and b['type'] == 'para':
            n = len(''.join(r['t'] for r in b['runs']))
            if STYLE == 'editorial':
                lead_done = True
                p.append(lead_in(b['runs'])); continue
            if i == 0 and 140 < n < 700:
                lead_done = True
                p.append(f'<div class="lead">{block_html(b, "")}</div>'); continue
            lead_done = True
        if b['type'] == 'image':
            p.append(block_html(b, 'full' if b.get('lead') else sides[si % 2]))
            si += 0 if b.get('lead') else 1
        else:
            p.append(block_html(b, ''))

    for b in a.get('appendix', []):
        p.append(f'<div class="appendix">{block_html(b, "")}</div>')
    if a['tail']:
        tl = a['tail']
        img = f'<img src="{IMG}/{tl["photo"]}" alt="">' if tl['photo'] else ''
        role = f'<div class="role">{esc(tl["role"])}</div>' if tl.get('role') else ''
        bio = f'<p class="bio">{esc(tl["bio"])}</p>' if tl['bio'] else ''
        p.append(f'<div class="tail">{img}<div class="who"><b>{esc(tl["name"])}</b>{role}'
                 f'<div class="mail">{esc(tl["email"])}</div>{bio}</div></div>')
    if a['credit']:
        p.append(f'<p class="credit-line">{esc(a["credit"])}</p>')
    p.append('</section>')
    return '\n'.join(p)


def main():
    arts = json.load(open(os.path.join(BASE, 'data', DATA, 'issue.json')))
    pmap, tight = {}, {}
    pm = os.path.join(B, f'pagemap-{KEY}.json')
    if os.path.exists(pm) and '--with-toc' in sys.argv:
        pmap = json.load(open(pm))
    tp = os.path.join(B, f'tighten-{KEY}.json')
    if os.path.exists(tp):
        tight = json.load(open(tp))

    body = (cover() + credits() + toc(arts, pmap.get('start', {})) +
            '\n'.join(article(a, tight.get(a['slug'])) for a in arts))

    runfoot = f"पालकनीती · {CFG['month_mr']}"
    doc = f'''<!doctype html>
<html lang="mr"><head><meta charset="utf-8">
<title>पालकनीती — {CFG['month_mr']}</title>
<style>{css()}</style></head>
<body>
{body}
<script>
window.PagedConfig = {{ auto: true, after: () => {{
  document.querySelectorAll('.pagedjs_page').forEach((pg, i) => {{
    if (i === 0) return;
    const n = i + 1;
    const f = document.createElement('div');
    f.className = 'folio';
    f.textContent = String(n).split('').map(d => '{DEV}'[+d]).join('');
    const t = document.createElement('div'); t.className = 'folio-tab';
    const rf = document.createElement('div'); rf.className = 'runfoot';
    rf.textContent = {json.dumps(runfoot, ensure_ascii=False)};
    pg.appendChild(f); pg.appendChild(t); pg.appendChild(rf);
  }});
  const map = {{}}, endp = {{}}, fill = {{}};
  document.querySelectorAll('.pagedjs_page').forEach((pg, i) => {{
    const n = i + 1;
    pg.querySelectorAll('[data-a]').forEach(a => {{
      const slug = a.getAttribute('data-a');
      if (!(slug in map)) map[slug] = n;
      endp[slug] = n;
    }});
    const area = pg.querySelector('.pagedjs_page_content');
    if (area) {{
      const ab = area.getBoundingClientRect();
      let maxB = ab.top;
      area.querySelectorAll('p,h1,h2,h3,h4,li,img,figcaption,blockquote,.tail,.lead').forEach(el => {{
        if (!el.getClientRects().length) return;
        const r = el.getBoundingClientRect();
        if (r.height > 0 && r.bottom > maxB && r.bottom <= ab.bottom + 4) maxB = r.bottom;
      }});
      fill[n] = ab.height ? (maxB - ab.top) / ab.height : 0;
    }}
  }});
  const out = document.createElement('pre');
  out.id = 'PAGEMAP'; out.style.display = 'none';
  out.textContent = 'PAGEMAP' + JSON.stringify({{start: map, end: endp, fill: fill}});
  document.body.appendChild(out);
  if (location.hash === '#extract' && window.__extractLayout) {{
    window.__extractLayout();
  }} else {{
    document.title = 'RENDER_DONE';
  }}
}} }};
</script>
<script src="paged.polyfill.js"></script>
<script src="extract.js"></script>
</body></html>'''
    open(os.path.join(B, f'issue-{KEY}.html'), 'w', encoding='utf-8').write(doc)
    print(f'wrote build/issue-{KEY}.html  [{STYLE}]  toc={"yes" if pmap else "pass1"}'
          f'  tight={tight or "{}"}')


main()
