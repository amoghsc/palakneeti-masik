# -*- coding: utf-8 -*-
"""Build the mobile reading edition of one issue as a single self-contained
   HTML page.   usage: web.py <issue-key>"""
import base64, html, io, json, os, re, sys
import chrome
from PIL import Image
from issues import resolve, MASTHEAD, SITE

BASE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(BASE, 'build')
KEY = sys.argv[1] if len(sys.argv) > 1 else '2026-07'
CFG = resolve(KEY)
DATA = CFG.get('data', KEY)
IMGDIR = os.path.join(B, 'images', DATA)

esc = lambda t: html.escape(t, quote=False)

# Built by authors.py. When present, bylines become links to the author's page.
ROOT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, '..'))
try:
    AUTHORS = json.load(open(os.path.join(ROOT, 'docs', 'authors', 'map.json')))
except Exception:
    AUTHORS = {}
_akey = lambda n: re.sub(r'\s+', '', n or '').lower()
AUTHOR_BY_KEY = {_akey(k): v for k, v in AUTHORS.items()}


def author_rec(name):
    m = ROLE_SPLIT.match((name or '').strip())
    person = m.group(2) if m else (name or '')
    rec = AUTHOR_BY_KEY.get(_akey(person.strip(' .,')))
    return rec if isinstance(rec, dict) else None


def avatar_html(name, cls='av'):
    """The author's face, or their initial when the site has no photo."""
    rec = author_rec(name)
    if rec and rec.get('img'):
        return f'<img class="{cls}" src="{rec["img"]}" alt="" loading="lazy">'
    m = ROLE_SPLIT.match((name or '').strip())
    person = (m.group(2) if m else (name or '')).strip(' .,')
    return f'<span class="{cls} none">{esc(person[:1])}</span>' if person else ''
ROLE_SPLIT = re.compile(r'^(अनुवाद|शब्दांकन|छायाचित्र[े]?|संकलन)\s*[:：]\s*(.+)$')


def author_slug(name):
    rec = author_rec(name)
    return rec and rec.get('slug')


def author_html(name):
    """Link a byline to its author page, keeping any 'अनुवाद :' prefix outside
       the link so only the person's name is clickable."""
    m = ROLE_SPLIT.match(name.strip())
    prefix, person = (m.group(1) + ' : ', m.group(2)) if m else ('', name)
    rec = author_rec(name)
    slug = rec and rec.get('slug')
    if not slug:
        return esc(name)
    return (f'{esc(prefix)}<a class="who-link" href="../authors/{slug}/">'
            f'{esc(person)}</a>')
DEV = '०१२३४५६७८९'
dev = lambda n: ''.join(DEV[int(c)] for c in str(n))


# ── images: everything is inlined, so everything gets resized first ──────
def data_uri(path, box, square=False, quality=72):
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
    # WebP is roughly a third smaller than JPEG at the same quality here, and
    # every phone browser in use supports it — these pages travel over mobile
    # data, so the saving is worth more than the compatibility tail.
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=quality, method=5)
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()


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
        if not b.get('file'):        # nothing was downloaded for this one
            return ''
        src = data_uri(os.path.join(IMGDIR, b['file']), 900)
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
        names = ' · '.join(author_html(x) for x in a['byline'])
        face = avatar_html(a['byline'][0], 'av md')
        p.append(f'<p class="byline">{face or f"<img class=\"nib\" src=\"{MARK_PEN}\" alt=\"\">"}'
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
        rec = author_rec(tl['name'])
        slug = rec and rec.get('slug')
        cnt = ''
        if rec and rec.get('n'):
            cnt = (f'<p class="count">{rec["span"]} मध्ये '
                   f'{dev(rec["n"])} लेख</p>')
        more = (f'<a class="more" href="../authors/{slug}/">'
                f'या लेखकाचे सगळे लेख →</a>') if slug else ''
        p.append(f'''<aside class="author">{photo}
    <div><h4>{author_html(tl['name'])}{role}</h4>{mail}{bio}{cnt}{more}</div></aside>''')
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
.av{border-radius:50%;object-fit:cover;flex:none;background:var(--surface)}
.av.none{display:inline-grid;place-items:center;font-family:var(--serif);
  color:var(--faint);line-height:1}
.av.sm{width:1.3rem;height:1.3rem;font-size:.72rem;
  display:inline-block;vertical-align:-.3rem;margin-right:.4rem}
span.av.sm.none{display:inline-grid;vertical-align:-.3rem}
.av.md{width:1.7rem;height:1.7rem;font-size:.9rem}
.author .count{margin:.55rem 0 0;font-size:.85rem;color:var(--faint)}
/* the page furniture — palette, bar, controls — lives in chrome.py */
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
.byline .who-link{color:inherit;text-decoration:underline;
  text-decoration-color:var(--rule);text-underline-offset:3px}
.author h4 .who-link{color:inherit;text-decoration:underline;
  text-decoration-color:var(--rule);text-underline-offset:3px}
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
.author .more{display:inline-block;margin-top:.7rem;font-size:.87rem;
  font-weight:600;color:var(--moss);text-decoration:none;
  border:1px solid var(--rule);border-radius:999px;padding:.32rem .85rem;}
@media (hover:hover){.author .more:hover{border-color:var(--moss)}}
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

"""

JS = """
(function(){
  var fab=document.querySelector('.fab'), toc=document.getElementById('contents');
  if(!fab||!toc) return;
  addEventListener('scroll',function(){
    fab.classList.toggle('on', scrollY > toc.offsetTop + toc.offsetHeight + 200);
  },{passive:true});
  var calm=matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.getElementById('tocBtn').addEventListener('click',function(){
    toc.scrollIntoView(calm?true:{behavior:'smooth'});
  });
})();
"""


def build():
    arts = json.load(open(os.path.join(BASE, 'data', DATA, 'issue.json')))
    n = len(arts)

    toc = []
    for i, a in enumerate(arts, 1):
        who = ' · '.join(esc(x) for x in a['byline'])
        face = avatar_html(a['byline'][0], 'av sm') if a['byline'] else ''
        toc.append(f'''<li><a href="#a{i}">
      <span class="n">{dev(i)}</span>
      <span><span class="t">{esc(a['title'])}</span>
        <span class="m">{face}{who}{' &nbsp;·&nbsp; ' if who else ''}'''
                   f'''<b>{dev(read_minutes(a))} मिनिटं</b></span></span>
    </a></li>''')

    cred = ''.join(f'<dt>{esc(h.rstrip(" :"))}</dt><dd>{esc(" ".join(v))}</dd>'
                   for h, v in MASTHEAD[:3])

    body = '\n'.join(article_html(a, i, n) for i, a in enumerate(arts, 1))

    body = f"""<main>
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
    <p><a class="backlink" href="../">← सगळे अंक</a></p>
  </footer>
</main>
<button class="fab" type="button" id="tocBtn">अनुक्रम</button>
<script>{JS}</script>"""
    return chrome.page(f"पालकनीती · {CFG['month_mr']}", CSS, body,
                       home='../', label=CFG['month_mr'])


out = os.path.join(B, f'web-{KEY}.html')
open(out, 'w', encoding='utf-8').write(build())
print(f'wrote {out}  {os.path.getsize(out)/1024:.0f} KB')
