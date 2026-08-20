# -*- coding: utf-8 -*-
"""Build the mobile reading edition of one issue as a single self-contained
   HTML page.   usage: web.py <issue-key>"""
import base64, html, io, json, os, re, sys
from PIL import Image
from issues import resolve, MASTHEAD, SITE

BASE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(BASE, 'build')
KEY = sys.argv[1] if len(sys.argv) > 1 else '2026-07'
CFG = resolve(KEY)
DATA = CFG.get('data', KEY)
IMGDIR = os.path.join(B, 'images', DATA)

esc = lambda t: html.escape(t, quote=False)
DEV = '०१२३४५६७८९'
dev = lambda n: ''.join(DEV[int(c)] for c in str(n))


# ── images: everything is inlined, so everything gets resized first ──────
def data_uri(path, box, square=False, quality=82):
    im = Image.open(path)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert('RGB')
    if square:
        s = min(im.size)
        l, t = (im.width - s) // 2, (im.height - s) // 2
        im = im.crop((l, t, l + s, t + s))
    im.thumbnail((box, box), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=quality, optimize=True, progressive=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def png_uri(path, box):
    """Keep transparency — used for the line-art marks."""
    im = Image.open(path).convert('RGBA')
    im.thumbnail((box, box), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


ART = os.path.join(B, 'assets')
MARK_PEN = png_uri(os.path.join(ART, 'pen.png'), 120)
MARK_TREE = png_uri(os.path.join(ART, 'p2_X7.png'), 160)
MARK_LEAF = data_uri(os.path.join(ART, 'p3_X24.png'), 260, quality=80)


# ── content ─────────────────────────────────────────────────────────────
def runs_html(runs):
    out = []
    for r in runs:
        t = esc(r['t']).replace('\n', '<br>')
        if r.get('b'):
            t = f'<strong>{t}</strong>'
        if r.get('i'):
            t = f'<em>{t}</em>'
        if r.get('href'):
            t = (f'<a href="{html.escape(r["href"])}" target="_blank" '
                 f'rel="noopener">{t}</a>')
        out.append(t)
    return ''.join(out)


def plain(runs):
    return ''.join(r['t'] for r in runs)


def read_minutes(a):
    words = sum(len(plain(b['runs']).split()) for b in a['body']
                if b['type'] == 'para')
    words += sum(len(plain(p).split()) for b in a['body']
                 if b['type'] == 'quote' for p in b['paras'])
    return max(1, round(words / 180))


def block_html(b):
    t = b['type']
    if t == 'para':
        return f'<p>{runs_html(b["runs"])}</p>'
    if t == 'head':
        return f'<h3>{runs_html(b["runs"])}</h3>'
    if t == 'image':
        src = data_uri(os.path.join(IMGDIR, b['file']), 1100)
        cap = (f'<figcaption>{esc(b["caption"])}</figcaption>'
               if b.get('caption') else '')
        return f'<figure><img src="{src}" alt="" loading="lazy">{cap}</figure>'
    if t == 'quote':
        return ('<blockquote>' +
                ''.join(f'<p>{runs_html(p)}</p>' for p in b['paras']) +
                '</blockquote>')
    if t == 'list':
        tag = 'ol' if b.get('ordered') else 'ul'
        return (f'<{tag}>' + ''.join(f'<li>{runs_html(i)}</li>'
                                     for i in b['items']) + f'</{tag}>')
    return ''


def article_html(a, n, total):
    p = [f'<article id="a{n}" class="art">']
    p.append('<header class="art-head">')
    p.append(f'<div class="art-no">लेख {dev(n)} / {dev(total)}</div>')
    if a['kicker']:
        p.append(f'<p class="eyebrow">{esc(a["kicker"])}</p>')
    p.append(f'<h2>{esc(a["title"])}</h2>')
    if a['byline']:
        names = ' · '.join(esc(x) for x in a['byline'])
        p.append(f'<p class="byline"><img class="nib" src="{MARK_PEN}" alt="">'
                 f'<span>{names}</span></p>')
    p.append(f'<p class="rtime">{dev(read_minutes(a))} मिनिटं वाचन</p>')
    p.append('</header>')

    p.append('<div class="body">')
    lead = False
    for b in a['body']:
        if not lead and b['type'] == 'para':
            lead = True
            p.append(f'<p class="lead">{runs_html(b["runs"])}</p>')
            continue
        p.append(block_html(b))
    for b in a.get('appendix', []):
        if b['type'] == 'para' and plain(b['runs']).strip() == 'संदर्भ:':
            p.append('<h3 class="refs-h">संदर्भ</h3>')
        else:
            p.append(f'<div class="note">{block_html(b)}</div>')
    p.append('</div>')

    if a['tail']:
        tl = a['tail']
        photo = ''
        if tl['photo']:
            src = data_uri(os.path.join(IMGDIR, tl['photo']), 240, square=True)
            photo = f'<img src="{src}" alt="" loading="lazy">'
        role = f'<span class="role">{esc(tl["role"])}</span>' if tl.get('role') else ''
        bio = f'<p>{esc(tl["bio"])}</p>' if tl['bio'] else ''
        mail = (f'<a class="mail" href="mailto:{esc(tl["email"])}">'
                f'{esc(tl["email"])}</a>')
        p.append(f'''<aside class="author">{photo}
    <div><h4>{esc(tl['name'])}{role}</h4>{mail}{bio}</div></aside>''')
    if a['credit']:
        p.append(f'<p class="credit">{esc(a["credit"])}</p>')

    p.append(f'''<div class="art-foot">
    <a class="up" href="#contents">अनुक्रमाकडे परत</a>
    {f'<a class="next" href="#a{n+1}">पुढचा लेख →</a>' if n < total else ''}
  </div>''')
    p.append('</article>')
    if n < total:
        p.append(f'<div class="divider" aria-hidden="true">'
                 f'<img src="{MARK_LEAF}" alt=""></div>')
    return '\n'.join(p)


CSS = """
:root{
  --paper:#F6F8F4; --surface:#EDF1EA; --raise:#FFFFFF;
  --ink:#16211D; --soft:#56685F; --faint:#7C8C84;
  --moss:#1F5A4C; --clay:#BC5D2C; --rule:#DBE3DA;
  --measure:34rem; --tscale:1; --linework:none;
  --serif:'Tiro Devanagari Marathi','Noto Serif Devanagari',Georgia,serif;
  --sans:'Mukta','Noto Sans Devanagari',system-ui,-apple-system,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#101613; --surface:#18211D; --raise:#1D2823;
    --ink:#E6EBE4; --soft:#9DACA3; --faint:#7E8D85;
    --moss:#7CC4AB; --clay:#E4885C; --rule:#25322C;
    --linework:invert(1);
  }
}
:root[data-theme="dark"]{
  --paper:#101613; --surface:#18211D; --raise:#1D2823;
  --ink:#E6EBE4; --soft:#9DACA3; --faint:#7E8D85;
  --moss:#7CC4AB; --clay:#E4885C; --rule:#25322C;
  --linework:invert(1);
}

*{box-sizing:border-box;}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:var(--sans);
  font-size:calc(17px * var(--tscale));
  line-height:1.78; -webkit-text-size-adjust:100%;
}
img{max-width:100%; display:block;}
a{color:var(--moss);}
:focus-visible{outline:2px solid var(--clay); outline-offset:3px; border-radius:2px;}

/* ── chrome ───────────────────────────────────────────────────── */
.progress{position:fixed; inset:0 auto auto 0; height:2px; width:0;
  background:var(--clay); z-index:60;}
.bar{position:sticky; top:0; z-index:50; background:var(--paper);
  border-bottom:1px solid var(--rule);
  display:flex; align-items:center; gap:.7rem;
  padding:.55rem max(1.15rem, env(safe-area-inset-left)) .55rem 1.15rem;}
.bar .tree{width:26px; height:26px; object-fit:contain; flex:none;
  filter:var(--linework);}
.bar .who{font-family:var(--serif); font-size:1.02rem; line-height:1.1;
  color:var(--moss); letter-spacing:.01em;}
.bar .mo{font-size:.74rem; color:var(--faint); line-height:1.1; margin-top:.1rem;}
.bar .spacer{flex:1;}
.thm{background:transparent; border:1px solid var(--rule); border-radius:999px;
  width:2rem; height:2rem; padding:0; cursor:pointer; color:var(--soft);
  display:grid; place-items:center; flex:none; margin-right:.15rem;}
.thm svg{width:15px; height:15px; display:none;}
.thm[data-m="auto"] .i-auto,
.thm[data-m="light"] .i-light,
.thm[data-m="dark"] .i-dark{display:block;}
.thm[data-m="light"],.thm[data-m="dark"]{color:var(--moss); border-color:var(--moss);}
.tsize{display:flex; gap:.28rem;}
.tsize button{
  font-family:var(--sans); background:transparent; color:var(--soft);
  border:1px solid var(--rule); border-radius:999px; cursor:pointer;
  width:2rem; height:2rem; line-height:1; padding:0;
  display:grid; place-items:center;}
.tsize button[aria-pressed="true"]{
  background:var(--moss); border-color:var(--moss); color:var(--paper);}
.tsize button:nth-child(1){font-size:.78rem;}
.tsize button:nth-child(2){font-size:.95rem;}
.tsize button:nth-child(3){font-size:1.12rem;}

main{max-width:var(--measure); margin:0 auto; padding:0 1.15rem 4rem;}

/* ── masthead ─────────────────────────────────────────────────── */
.top{padding:3rem 0 2.2rem; text-align:center;}
.top h1{font-family:var(--serif); font-weight:400;
  font-size:clamp(2.5rem,12vw,3.4rem); line-height:1.05; margin:0;
  color:var(--moss); text-wrap:balance;}
.top .issue{margin:.9rem 0 0; font-size:.9rem; letter-spacing:.16em;
  text-transform:uppercase; color:var(--faint);}
.top .sub{margin:1.4rem auto 0; max-width:26rem; color:var(--soft);
  font-size:.97rem; line-height:1.7;}

/* ── contents ─────────────────────────────────────────────────── */
.contents{scroll-margin-top:4.5rem; padding-top:.5rem;}
.contents h2{font-family:var(--sans); font-size:.8rem; letter-spacing:.18em;
  text-transform:uppercase; color:var(--faint); font-weight:700;
  margin:0 0 .3rem;}
.toc{list-style:none; margin:0; padding:0;}
.toc li{border-top:1px solid var(--rule);}
.toc li:last-child{border-bottom:1px solid var(--rule);}
.toc a{display:grid; grid-template-columns:1.9rem 1fr; gap:.85rem;
  padding:1.05rem .15rem; text-decoration:none; color:inherit;
  align-items:baseline;}
.toc .n{font-family:var(--serif); font-size:1.15rem; color:var(--clay);
  font-variant-numeric:tabular-nums;}
.toc .t{font-family:var(--serif); font-size:1.24rem; line-height:1.35;
  color:var(--ink); text-wrap:balance;}
.toc .m{display:block; margin-top:.3rem; font-size:.85rem; color:var(--soft);}
.toc .m b{font-weight:400; color:var(--faint);}
@media (hover:hover){ .toc a:hover .t{color:var(--moss);} }

/* ── article ──────────────────────────────────────────────────── */
.art{scroll-margin-top:4.2rem; padding-top:2.6rem;}
.art-head{margin-bottom:1.9rem;}
.art-no{font-size:.74rem; letter-spacing:.17em; text-transform:uppercase;
  color:var(--faint); margin-bottom:.9rem;}
.eyebrow{margin:0 0 .45rem; font-size:.83rem; font-weight:700;
  letter-spacing:.11em; text-transform:uppercase; color:var(--clay);}
.art h2{font-family:var(--serif); font-weight:400;
  font-size:clamp(1.85rem,7.4vw,2.5rem); line-height:1.24;
  margin:0 0 1rem; color:var(--ink); text-wrap:balance;}
.byline{display:flex; align-items:center; gap:.55rem; margin:0;
  font-size:.98rem; font-weight:600; color:var(--moss);}
.byline .nib{width:15px; flex:none; opacity:.85; filter:var(--linework);}
.rtime{margin:.35rem 0 0 2.1rem; font-size:.85rem; color:var(--faint);}

.body p{margin:0 0 1.15em;}
.body .lead{font-size:1.1em; line-height:1.7; color:var(--ink);}
.body h3{font-family:var(--serif); font-weight:400; font-size:1.32em;
  line-height:1.35; margin:2em 0 .6em; color:var(--moss);}
.body ul,.body ol{margin:0 0 1.15em; padding-left:1.25em;}
.body li{margin-bottom:.5em;}
.body figure{margin:1.9em 0;}
.body figure img{width:100%; border-radius:3px;}
.body figcaption{margin-top:.55em; font-size:.85rem; color:var(--faint);
  line-height:1.5;}
.body blockquote{margin:1.7em 0; padding:.2em 0 .2em 1.15em;
  border-left:2px solid var(--clay); font-family:var(--serif);
  font-size:1.08em; line-height:1.62; color:var(--ink);}
.body blockquote p{margin:0 0 .7em;}
.body blockquote p:last-child{margin-bottom:0;}
.body a{overflow-wrap:anywhere;}
.refs-h{font-family:var(--sans)!important; font-size:.8rem!important;
  letter-spacing:.18em; text-transform:uppercase; font-weight:700!important;
  color:var(--faint)!important; margin:2.2em 0 .7em!important;}
.note{background:var(--surface); border-radius:4px; padding:1rem 1.1rem;
  margin:0 0 .7rem; font-size:.94em;}
.note p{margin:0 0 .5em;}
.note p:last-child{margin-bottom:0;}

.author{display:flex; gap:1rem; align-items:flex-start; margin:2.6rem 0 0;
  padding:1.15rem; background:var(--surface); border-radius:4px;}
.author img{width:62px; height:62px; border-radius:50%; flex:none;
  object-fit:cover;}
.author h4{margin:0 0 .15rem; font-size:1.02rem; color:var(--ink);}
.author .role{font-weight:400; color:var(--faint); font-size:.85rem;
  margin-left:.4rem;}
.author .mail{font-size:.86rem; word-break:break-all;}
.author p{margin:.45rem 0 0; font-size:.9rem; line-height:1.62;
  color:var(--soft);}
.credit{margin:.9rem 0 0; font-size:.86rem; color:var(--faint);}

.art-foot{display:flex; flex-wrap:wrap; gap:1rem; justify-content:space-between;
  margin-top:2.2rem; padding-top:1rem; border-top:1px solid var(--rule);
  font-size:.9rem;}
.art-foot a{text-decoration:none;}
.art-foot .up{color:var(--soft);}
.art-foot .next{color:var(--moss); font-weight:600;}

.divider{display:flex; justify-content:center; padding:2.8rem 0 .4rem;}
.divider img{width:74px; opacity:.85;}

/* ── colophon ─────────────────────────────────────────────────── */
.colophon{margin-top:4rem; padding-top:1.8rem; border-top:1px solid var(--rule);
  font-size:.88rem; color:var(--soft);}
.colophon h3{font-family:var(--sans); font-size:.78rem; letter-spacing:.18em;
  text-transform:uppercase; color:var(--faint); margin:0 0 .9rem;}
.colophon dl{display:grid; grid-template-columns:auto 1fr; gap:.35rem .9rem;
  margin:0 0 1.4rem;}
.colophon dt{color:var(--faint);}
.colophon dd{margin:0;}
.colophon .site{display:inline-block; margin-top:.4rem; font-weight:600;}

.fab{position:fixed; right:1rem; bottom:calc(1rem + env(safe-area-inset-bottom));
  z-index:55; background:var(--moss); color:var(--paper); border:none;
  border-radius:999px; padding:.7rem 1.1rem; font-family:var(--sans);
  font-size:.87rem; font-weight:600; cursor:pointer;
  box-shadow:0 4px 14px rgba(0,0,0,.18); opacity:0; pointer-events:none;
  transform:translateY(8px); transition:opacity .2s, transform .2s;}
.fab.on{opacity:1; pointer-events:auto; transform:none;}

@media (prefers-reduced-motion:reduce){
  *{scroll-behavior:auto!important; transition:none!important;}
}
@media print{
  .bar,.fab,.progress,.art-foot,.divider{display:none;}
  body{background:#fff; color:#000;}
  .art{page-break-before:always;}
}
"""

JS = """
(function(){
  var root=document.documentElement, bar=document.querySelector('.progress');
  function prog(){
    var h=document.body.scrollHeight-innerHeight;
    bar.style.width=(h>0?(scrollY/h)*100:0)+'%';
  }
  addEventListener('scroll',prog,{passive:true}); prog();

  var fab=document.querySelector('.fab'), toc=document.getElementById('contents');
  addEventListener('scroll',function(){
    fab.classList.toggle('on', scrollY > toc.offsetTop + toc.offsetHeight + 200);
  },{passive:true});

  var steps=[0.92,1,1.14], btns=[].slice.call(document.querySelectorAll('.tsize button'));
  function apply(i){
    root.style.setProperty('--tscale',steps[i]);
    btns.forEach(function(b,j){b.setAttribute('aria-pressed',j===i);});
    try{localStorage.setItem('pn-tsize',i);}catch(e){}
  }
  btns.forEach(function(b,i){b.addEventListener('click',function(){apply(i);});});

  var modes=['auto','light','dark'],
      names={auto:'थीम: आपोआप',light:'थीम: उजळ',dark:'थीम: गडद'},
      tb=document.getElementById('thmBtn'), mi=0;
  function theme(i){
    var m=modes[i]; mi=i;
    if(m==='auto'){
      if(root.__hostTheme) root.setAttribute('data-theme',root.__hostTheme);
      else root.removeAttribute('data-theme');
    } else root.setAttribute('data-theme',m);
    tb.setAttribute('data-m',m);
    tb.setAttribute('aria-label',names[m]);
    tb.setAttribute('title',names[m]);
    try{localStorage.setItem('pn-theme',m);}catch(e){}
  }
  tb.addEventListener('click',function(){theme((mi+1)%3);});
  var tm=0; try{tm=Math.max(0,modes.indexOf(localStorage.getItem('pn-theme')));}catch(e){}
  theme(tm);

  var calm=matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.getElementById('tocBtn').addEventListener('click',function(){
    toc.scrollIntoView(calm?true:{behavior:'smooth'});
  });
  var saved=1; try{var v=localStorage.getItem('pn-tsize'); if(v!==null)saved=+v;}catch(e){}
  apply(saved);
})();
"""


def build():
    arts = json.load(open(os.path.join(BASE, 'data', DATA, 'issue.json')))
    n = len(arts)

    toc = []
    for i, a in enumerate(arts, 1):
        who = ' · '.join(esc(x) for x in a['byline'])
        toc.append(f'''<li><a href="#a{i}">
      <span class="n">{dev(i)}</span>
      <span><span class="t">{esc(a['title'])}</span>
        <span class="m">{who}{' &nbsp;·&nbsp; ' if who else ''}'''
                   f'''<b>{dev(read_minutes(a))} मिनिटं</b></span></span>
    </a></li>''')

    cred = ''.join(f'<dt>{esc(h.rstrip(" :"))}</dt><dd>{esc(" ".join(v))}</dd>'
                   for h, v in MASTHEAD[:3])

    body = '\n'.join(article_html(a, i, n) for i, a in enumerate(arts, 1))

    return f'''<title>पालकनीती · {CFG['month_mr']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700&family=Tiro+Devanagari+Marathi&display=swap">
<style>{CSS}</style>
<script>
/* stamp the saved theme before first paint, so the page never flashes the
   other theme on load. The host may have stamped data-theme itself; remember
   it, because "auto" means defer to the host, not force the OS setting. */
(function(){{
  var r=document.documentElement;
  r.__hostTheme=r.getAttribute('data-theme');
  try{{
    var m=localStorage.getItem('pn-theme');
    if(m==='light'||m==='dark') r.setAttribute('data-theme',m);
  }}catch(e){{}}
}})();
</script>

<div class="progress" aria-hidden="true"></div>

<header class="bar">
  <img class="tree" src="{MARK_TREE}" alt="">
  <div>
    <div class="who">पालकनीती</div>
    <div class="mo">{esc(CFG['month_mr'])}</div>
  </div>
  <div class="spacer"></div>
  <button class="thm" type="button" id="thmBtn" data-m="auto" aria-label="थीम">
    <svg class="i-auto" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.1"
      fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 1.9a6.1 6.1 0 0 0 0 12.2z"
      fill="currentColor"/></svg>
    <svg class="i-light" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3.1"
      fill="currentColor"/><g stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path
      d="M8 1V2.4M8 13.6V15M15 8h-1.4M2.4 8H1M12.9 3.1l-1 1M4.1 11.9l-1 1M12.9 12.9l-1-1M4.1 4.1l-1-1"/></g></svg>
    <svg class="i-dark" viewBox="0 0 16 16" aria-hidden="true"><path
      d="M13.4 9.7A5.8 5.8 0 0 1 6.3 2.6a5.9 5.9 0 1 0 7.1 7.1z" fill="currentColor"/></svg>
  </button>
  <div class="tsize" role="group" aria-label="अक्षरांचा आकार">
    <button type="button" aria-pressed="false" aria-label="लहान अक्षरं">अ</button>
    <button type="button" aria-pressed="true" aria-label="नेहमीचा आकार">अ</button>
    <button type="button" aria-pressed="false" aria-label="मोठी अक्षरं">अ</button>
  </div>
</header>

<main>
  <div class="top">
    <h1>पालकनीती</h1>
    <p class="issue">{esc(CFG['month_mr'])}</p>
    <p class="sub">या अंकातले {dev(n)} लेख — फोनवर वाचण्यासाठी.
       मजकुराचा आकार वरच्या पट्टीतून बदलता येईल.</p>
  </div>

  <nav class="contents" id="contents" aria-label="अनुक्रम">
    <h2>या अंकात</h2>
    <ol class="toc">{''.join(toc)}</ol>
  </nav>

{body}

  <footer class="colophon">
    <h3>अंकाविषयी</h3>
    <dl>{cred}</dl>
    <p>सर्व लेख <a href="https://palakneeti.in" target="_blank" rel="noopener">palakneeti.in</a>
       वर प्रसिद्ध झाले आहेत. जुने अंक आणि लेख तिथे वाचता येतील.</p>
    <a class="site" href="https://palakneeti.in" target="_blank" rel="noopener">{SITE}</a>
  </footer>
</main>

<button class="fab" type="button" id="tocBtn">अनुक्रम</button>

<script>{JS}</script>
'''


out = os.path.join(B, f'web-{KEY}.html')
open(out, 'w', encoding='utf-8').write(build())
print(f'wrote {out}  {os.path.getsize(out)/1024:.0f} KB')
