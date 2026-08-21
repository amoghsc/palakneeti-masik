# -*- coding: utf-8 -*-
"""Shared page furniture: palette, top bar, theme and text-size controls.

Every page on the site — the front page, a month, an author — is built from
this, so they look like one publication and behave the same way.
"""
import base64, io, os

BASE = os.path.dirname(os.path.abspath(__file__))


def _logo():
    from PIL import Image
    p = os.path.join(BASE, 'build', 'assets', 'p2_X7.png')
    im = Image.open(p).convert('RGBA')
    im.thumbnail((120, 120), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


LOGO = _logo()

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Mukta:wght@400;500;600;700&'
         'family=Tiro+Devanagari+Marathi&display=swap">')

# The text-size control scales the root font, so every rem-based size on the
# page follows it — including headings and the contents list. The bar itself
# is sized in px so the furniture stays put while the reading text grows.
TOKENS = """
:root{
  --paper:#F6F8F4; --surface:#EDF1EA; --ink:#16211D; --soft:#56685F;
  --faint:#7C8C84; --moss:#1F5A4C; --clay:#BC5D2C; --rule:#DBE3DA;
  --tscale:1; --linework:none;
  --serif:'Tiro Devanagari Marathi','Noto Serif Devanagari',Georgia,serif;
  --sans:'Mukta','Noto Sans Devanagari',system-ui,-apple-system,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#101613; --surface:#18211D; --ink:#E6EBE4; --soft:#9DACA3;
    --faint:#7E8D85; --moss:#7CC4AB; --clay:#E4885C; --rule:#25322C;
    --linework:invert(1);
  }
}
:root[data-theme="dark"]{
  --paper:#101613; --surface:#18211D; --ink:#E6EBE4; --soft:#9DACA3;
  --faint:#7E8D85; --moss:#7CC4AB; --clay:#E4885C; --rule:#25322C;
  --linework:invert(1);
}
*{box-sizing:border-box}
html{font-size:calc(17px * var(--tscale));}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:1rem;line-height:1.74;-webkit-text-size-adjust:100%}
img{max-width:100%;display:block}
a{color:var(--moss)}
:focus-visible{outline:2px solid var(--clay);outline-offset:3px;border-radius:2px}
main{max-width:34rem;margin:0 auto;padding:0 1.15rem 4rem}
"""

CHROME = """
.progress{position:fixed;inset:0 auto auto 0;height:2px;width:0;
  background:var(--clay);z-index:60}
.bar{position:sticky;top:0;z-index:50;background:var(--paper);
  border-bottom:1px solid var(--rule);display:flex;align-items:center;
  gap:10px;padding:9px max(18px,env(safe-area-inset-left)) 9px 18px}
.bar .home{display:flex;align-items:center;gap:10px;text-decoration:none;
  color:inherit;min-width:0}
.bar .tree{width:26px;height:26px;object-fit:contain;flex:none;
  filter:var(--linework)}
.bar .who{font-family:var(--serif);font-size:17px;line-height:1.1;
  color:var(--moss);letter-spacing:.01em;white-space:nowrap}
.bar .mo{font-size:11.5px;color:var(--faint);line-height:1.1;margin-top:2px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar .spacer{flex:1}
.thm{background:transparent;border:1px solid var(--rule);border-radius:999px;
  width:32px;height:32px;padding:0;cursor:pointer;color:var(--soft);
  display:grid;place-items:center;flex:none;margin-right:2px}
.thm svg{width:15px;height:15px;display:none}
.thm[data-m="auto"] .i-auto,.thm[data-m="light"] .i-light,
.thm[data-m="dark"] .i-dark{display:block}
.thm[data-m="light"],.thm[data-m="dark"]{color:var(--moss);border-color:var(--moss)}
.tsize{display:flex;gap:4px}
.tsize button{font-family:var(--sans);background:transparent;color:var(--soft);
  border:1px solid var(--rule);border-radius:999px;cursor:pointer;
  width:32px;height:32px;line-height:1;padding:0;display:grid;place-items:center}
.tsize button[aria-pressed="true"]{background:var(--moss);
  border-color:var(--moss);color:var(--paper)}
.tsize button:nth-child(1){font-size:12px}
.tsize button:nth-child(2){font-size:15px}
.tsize button:nth-child(3){font-size:18px}
.backlink{display:inline-block;margin:2.4rem 0 0;font-size:.9rem;
  color:var(--soft);text-decoration:none}
.backlink:hover{color:var(--moss)}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;
  transition:none!important}}
@media print{.bar,.progress,.fab,.backlink{display:none}
  body{background:#fff;color:#000}}
"""

EARLY = """
<script>
/* Stamp the saved theme before first paint so the page never flashes the
   other theme. "auto" defers to whatever the host or the phone says. */
(function(){var r=document.documentElement;r.__hostTheme=r.getAttribute('data-theme');
try{var m=localStorage.getItem('pn-theme');if(m==='light'||m==='dark')
r.setAttribute('data-theme',m);var t=localStorage.getItem('pn-tsize');
if(t!==null)r.style.setProperty('--tscale',[0.92,1,1.14][+t]||1);}catch(e){}})();
</script>"""

SCRIPT = """
<script>
(function(){
  var root=document.documentElement;
  var bar=document.querySelector('.progress');
  if(bar){
    var prog=function(){var h=document.body.scrollHeight-innerHeight;
      bar.style.width=(h>0?(scrollY/h)*100:0)+'%';};
    addEventListener('scroll',prog,{passive:true});prog();
  }
  var modes=['auto','light','dark'],
      names={auto:'थीम: आपोआप',light:'थीम: उजळ',dark:'थीम: गडद'},
      tb=document.getElementById('thmBtn'),mi=0;
  function theme(i){var m=modes[i];mi=i;
    if(m==='auto'){ if(root.__hostTheme) root.setAttribute('data-theme',root.__hostTheme);
      else root.removeAttribute('data-theme'); }
    else root.setAttribute('data-theme',m);
    tb.setAttribute('data-m',m);tb.setAttribute('aria-label',names[m]);
    tb.setAttribute('title',names[m]);
    try{localStorage.setItem('pn-theme',m);}catch(e){}}
  if(tb){ tb.addEventListener('click',function(){theme((mi+1)%3);});
    var tm=0;try{tm=Math.max(0,modes.indexOf(localStorage.getItem('pn-theme')));}catch(e){}
    theme(tm); }

  var steps=[0.92,1,1.14],btns=[].slice.call(document.querySelectorAll('.tsize button'));
  function size(i){root.style.setProperty('--tscale',steps[i]);
    btns.forEach(function(b,j){b.setAttribute('aria-pressed',j===i);});
    try{localStorage.setItem('pn-tsize',i);}catch(e){}}
  btns.forEach(function(b,i){b.addEventListener('click',function(){size(i);});});
  var sv=1;try{var v=localStorage.getItem('pn-tsize');if(v!==null)sv=+v;}catch(e){}
  if(btns.length)size(sv);
})();
</script>"""

_ICONS = '''<svg class="i-auto" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.1"
 fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 1.9a6.1 6.1 0 0 0 0 12.2z"
 fill="currentColor"/></svg>
<svg class="i-light" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3.1"
 fill="currentColor"/><g stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path
 d="M8 1V2.4M8 13.6V15M15 8h-1.4M2.4 8H1M12.9 3.1l-1 1M4.1 11.9l-1 1M12.9 12.9l-1-1M4.1 4.1l-1-1"/></g></svg>
<svg class="i-dark" viewBox="0 0 16 16" aria-hidden="true"><path
 d="M13.4 9.7A5.8 5.8 0 0 1 6.3 2.6a5.9 5.9 0 1 0 7.1 7.1z" fill="currentColor"/></svg>'''


def bar(home, label, progress=True):
    """Top bar. The logo and name always lead back to the front page."""
    pg = '<div class="progress" aria-hidden="true"></div>' if progress else ''
    sub = f'<div class="mo">{label}</div>' if label else ''
    return f'''{pg}
<header class="bar">
  <a class="home" href="{home}" title="पालकनीती मासिक">
    <img class="tree" src="{LOGO}" alt="">
    <span><span class="who">पालकनीती</span>{sub}</span>
  </a>
  <div class="spacer"></div>
  <button class="thm" type="button" id="thmBtn" data-m="auto" aria-label="थीम">{_ICONS}</button>
  <div class="tsize" role="group" aria-label="अक्षरांचा आकार">
    <button type="button" aria-pressed="false" aria-label="लहान अक्षरं">अ</button>
    <button type="button" aria-pressed="true" aria-label="नेहमीचा आकार">अ</button>
    <button type="button" aria-pressed="false" aria-label="मोठी अक्षरं">अ</button>
  </div>
</header>'''


def page(title, css, body, home='./', label='', progress=True, extra_head=''):
    """A complete, standalone HTML document — doctype, viewport and all."""
    return f'''<!doctype html>
<html lang="mr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
{FONTS}
<style>{TOKENS}{CHROME}{css}</style>{extra_head}
{EARLY}
</head>
<body>
{bar(home, label, progress)}
{body}
{SCRIPT}
</body></html>
'''
